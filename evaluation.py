"""
RAG 评估模块（最小可用版）

目标：
1) 读取评测集（JSON）
2) 调用现有问答链路批量评估
3) 输出可复用的结构化报告（JSON）
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Callable

from pipeline import answer_with_store, build_runtime


def _normalize_text(text: str) -> str:
    return " ".join(re.findall(r"\w+", text.lower()))


def token_f1(prediction: str, reference: str) -> float:
    pred_tokens = _normalize_text(prediction).split()
    ref_tokens = _normalize_text(reference).split()
    if not pred_tokens or not ref_tokens:
        return 0.0

    ref_count: dict[str, int] = {}
    for token in ref_tokens:
        ref_count[token] = ref_count.get(token, 0) + 1

    overlap = 0
    for token in pred_tokens:
        left = ref_count.get(token, 0)
        if left > 0:
            overlap += 1
            ref_count[token] = left - 1
    if overlap == 0:
        return 0.0

    precision = overlap / len(pred_tokens)
    recall = overlap / len(ref_tokens)
    return 2 * precision * recall / (precision + recall)


def keyword_recall(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0
    normalized_answer = _normalize_text(answer)
    hit = 0
    for kw in keywords:
        needle = _normalize_text(kw)
        if needle and needle in normalized_answer:
            hit += 1
    return hit / len(keywords)


def source_metrics(
    predicted_sources: list[dict[str, Any]],
    expected_sources: list[dict[str, Any]],
) -> tuple[float, bool]:
    if not expected_sources:
        return 0.0, False

    expected = {
        (item.get("source"), item.get("page"))
        for item in expected_sources
    }
    predicted = {
        (item.get("source"), item.get("page"))
        for item in predicted_sources
    }
    matched = expected & predicted
    recall = len(matched) / len(expected) if expected else 0.0
    hit = len(matched) > 0
    return recall, hit


def load_eval_cases(path: str) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"评测集不存在: {path}")
    payload = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("评测集 JSON 根结构必须是 list")
    return payload


def evaluate_cases(
    cases: list[dict[str, Any]],
    answer_fn: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    per_case: list[dict[str, Any]] = []

    exact_scores: list[float] = []
    f1_scores: list[float] = []
    kw_scores: list[float] = []
    src_recall_scores: list[float] = []
    src_hit_scores: list[float] = []

    for i, case in enumerate(cases, start=1):
        query = str(case.get("query", "")).strip()
        if not query:
            raise ValueError(f"第 {i} 条评测样本缺少 query")

        response = answer_fn(case)
        answer = str(response.get("answer", "")).strip()
        sources = response.get("sources", [])
        if not isinstance(sources, list):
            sources = []

        row: dict[str, Any] = {
            "id": case.get("id", f"case_{i}"),
            "query": query,
            "answer": answer,
            "sources": sources,
            "metrics": {},
        }

        expected_answer = str(case.get("expected_answer", "")).strip()
        if expected_answer:
            em = 1.0 if _normalize_text(answer) == _normalize_text(expected_answer) else 0.0
            f1 = token_f1(answer, expected_answer)
            row["metrics"]["answer_exact_match"] = em
            row["metrics"]["answer_token_f1"] = f1
            exact_scores.append(em)
            f1_scores.append(f1)

        expected_keywords = case.get("expected_keywords", [])
        if isinstance(expected_keywords, list) and expected_keywords:
            kw = keyword_recall(answer, [str(x) for x in expected_keywords])
            row["metrics"]["keyword_recall"] = kw
            kw_scores.append(kw)

        expected_sources = case.get("expected_sources", [])
        if isinstance(expected_sources, list) and expected_sources:
            src_recall, src_hit = source_metrics(sources, expected_sources)
            row["metrics"]["source_recall"] = src_recall
            row["metrics"]["source_hit"] = src_hit
            src_recall_scores.append(src_recall)
            src_hit_scores.append(1.0 if src_hit else 0.0)

        per_case.append(row)

    def _avg(values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)

    summary = {
        "total_cases": len(cases),
        "answer_exact_match_avg": _avg(exact_scores),
        "answer_token_f1_avg": _avg(f1_scores),
        "keyword_recall_avg": _avg(kw_scores),
        "source_recall_avg": _avg(src_recall_scores),
        "source_hit_rate": _avg(src_hit_scores),
    }
    return {"summary": summary, "cases": per_case}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="RAG-Demo 评估脚本")
    parser.add_argument("--eval-set", type=str, default="eval/eval_set.example.json", help="评测集 JSON 路径")
    parser.add_argument("--output", type=str, default="artifacts/eval/latest_report.json", help="评估报告输出路径")
    parser.add_argument("--top-k", type=int, default=3, help="默认检索 top_k")
    parser.add_argument("--force-rebuild", action="store_true", help="忽略缓存并重建向量/索引")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--embed-dim", type=int, default=256)
    parser.add_argument(
        "--llm-provider",
        type=str,
        default="local",
        choices=["local", "openai", "openai_compatible"],
    )
    parser.add_argument("--llm-model", type=str, default="gpt-4o-mini")
    parser.add_argument("--llm-base-url", type=str, default="")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--llm-timeout", type=float, default=120.0)
    parser.add_argument("--llm-max-retries", type=int, default=1)
    parser.add_argument(
        "--min-relevance-score",
        type=float,
        default=0.0,
        help="检索最小相关度阈值（0 表示关闭；低于阈值的上下文将被丢弃）",
    )
    parser.add_argument("--no-llm-fallback-local", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_eval_cases(args.eval_set)
    vector_store, faiss_index = build_runtime(
        force_rebuild=args.force_rebuild,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        embed_dim=args.embed_dim,
    )

    def _answer_fn(case: dict[str, Any]) -> dict[str, Any]:
        case_top_k = int(case.get("top_k", args.top_k))
        return answer_with_store(
            query=str(case["query"]),
            vector_store=vector_store,
            faiss_index=faiss_index,
            top_k=case_top_k,
            llm_provider=args.llm_provider,
            llm_model=args.llm_model,
            llm_base_url=args.llm_base_url,
            temperature=args.temperature,
            llm_timeout=args.llm_timeout,
            llm_max_retries=args.llm_max_retries,
            llm_fallback_local=not args.no_llm_fallback_local,
            min_relevance_score=None
            if args.min_relevance_score <= 0
            else float(args.min_relevance_score),
        )

    report = evaluate_cases(cases, _answer_fn)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("[EVAL] 评估完成")
    print(f"[EVAL] 样本数: {report['summary']['total_cases']}")
    print(f"[EVAL] answer_exact_match_avg: {report['summary']['answer_exact_match_avg']}")
    print(f"[EVAL] answer_token_f1_avg: {report['summary']['answer_token_f1_avg']}")
    print(f"[EVAL] keyword_recall_avg: {report['summary']['keyword_recall_avg']}")
    print(f"[EVAL] source_recall_avg: {report['summary']['source_recall_avg']}")
    print(f"[EVAL] source_hit_rate: {report['summary']['source_hit_rate']}")
    print(f"[EVAL] 报告路径: {output_path}")


if __name__ == "__main__":
    main()
