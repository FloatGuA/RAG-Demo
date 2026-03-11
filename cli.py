"""
RAG-Demo 统一命令行入口（基于 typer）

用法:
    python cli.py build                           # 离线构建
    python cli.py query "What is A/B testing?"    # 单次问答
    python cli.py chat                            # 交互式 REPL
    python cli.py eval --eval-set eval/xxx.json   # 批量评估
    python cli.py web                             # 启动 Streamlit Web UI
"""

from __future__ import annotations

import subprocess
import sys
from typing import Optional

import typer

from config.defaults import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBED_BACKEND,
    DEFAULT_EMBED_DIM,
    DEFAULT_LLM_MAX_RETRIES,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_OVERLAP,
    DEFAULT_PREVIEW,
    DEFAULT_RERANK_INITIAL_K,
    DEFAULT_RERANK_MODEL,
    DEFAULT_TOP_K,
    DEFAULT_TEMPERATURE,
    DEFAULT_USE_HYBRID,
    DEFAULT_USE_RERANK,
)
from config.env import get_llm_default, load_env_defaults
from config.llm_presets import (
    get_default_base_url,
    get_default_model,
    load_llm_presets,
)
from config.paths import CHUNKS_PATH, FAISS_INDEX_PATH, VECTORS_PATH

app = typer.Typer(help="RAG-Demo 统一命令行入口", add_completion=False)

_env = load_env_defaults()
_presets = load_llm_presets()


# ── 共享参数默认值（Provider 来自 .env，base_url/model 来自 llm_presets.json）───

def _provider_default() -> str:
    return get_llm_default("LLM_PROVIDER", DEFAULT_LLM_PROVIDER, env_defaults=_env)


def _model_default() -> str:
    provider = _provider_default()
    return get_default_model(_presets, provider)


def _base_url_default() -> str:
    provider = _provider_default()
    return get_default_base_url(_presets, provider)


# ── build ──────────────────────────────────────────

@app.command()
def build(
    force_rebuild: bool = typer.Option(False, "--force-rebuild", help="忽略缓存，强制重建"),
    chunk_size: int = typer.Option(DEFAULT_CHUNK_SIZE, help="chunk 最大字符数"),
    overlap: int = typer.Option(DEFAULT_OVERLAP, help="chunk 重叠字符数"),
    embed_dim: int = typer.Option(DEFAULT_EMBED_DIM, help="向量维度"),
    embed_backend: str = typer.Option(DEFAULT_EMBED_BACKEND, help="embedding 后端（auto/sentence_transformers/hash）"),
    preview: int = typer.Option(DEFAULT_PREVIEW, help="预览前 N 个 chunk"),
) -> None:
    """离线构建 chunks / vectors / FAISS index。"""
    from pipeline.build import build_or_load_chunks, build_or_load_faiss_index, build_or_load_vectors

    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    chunks, src, new_chunks = build_or_load_chunks(force_rebuild=force_rebuild, chunk_size=chunk_size, overlap=overlap)
    extra = f", {len(new_chunks)} new" if src == "incremental" else ""
    typer.echo(f"[BUILD] chunks: {len(chunks)} ({src}{extra})")

    incremental_new = new_chunks if src == "incremental" else None
    vs, vs_src = build_or_load_vectors(chunks, force_rebuild=force_rebuild, dim=embed_dim, backend=embed_backend, new_chunks=incremental_new)
    typer.echo(f"[BUILD] vectors: dim={vs.dim}, count={len(vs.vectors)} ({vs_src})")

    faiss_force = force_rebuild or src == "incremental"
    fi, fi_src = build_or_load_faiss_index(vs, force_rebuild=faiss_force)
    typer.echo(f"[BUILD] FAISS: {fi_src}")

    stdout_enc = sys.stdout.encoding or "utf-8"
    for c in chunks[: max(preview, 0)]:
        text = c.text[:80].encode(stdout_enc, errors="replace").decode(stdout_enc, errors="replace")
        typer.echo(f"  - [{c.source} p.{c.page}] {text}...")


# ── query ──────────────────────────────────────────

@app.command()
def query(
    question: str = typer.Argument(..., help="要提问的问题"),
    top_k: int = typer.Option(DEFAULT_TOP_K, help="检索 top_k"),
    hybrid: bool = typer.Option(DEFAULT_USE_HYBRID, "--hybrid/--no-hybrid", help="启用 BM25 + Dense 混合检索"),
    rerank: bool = typer.Option(DEFAULT_USE_RERANK, "--rerank/--no-rerank", help="启用 Cross-Encoder 重排"),
    rerank_initial_k: int = typer.Option(DEFAULT_RERANK_INITIAL_K, help="Rerank 前粗召回数量"),
    llm_provider: str = typer.Option(_provider_default(), help="LLM provider"),
    llm_model: str = typer.Option(_model_default(), help="模型名"),
    llm_base_url: str = typer.Option(_base_url_default(), help="Base URL"),
    temperature: float = typer.Option(DEFAULT_TEMPERATURE, help="采样温度"),
    llm_timeout: float = typer.Option(DEFAULT_LLM_TIMEOUT, help="超时（秒）"),
    llm_max_retries: int = typer.Option(DEFAULT_LLM_MAX_RETRIES, help="重试次数"),
    min_relevance_score: float = typer.Option(0.0, help="最小相关度阈值"),
    no_fallback: bool = typer.Option(False, "--no-fallback", help="失败时不回退本地"),
    debug: bool = typer.Option(False, "--debug", help="输出调试信息"),
    force_rebuild: bool = typer.Option(False, "--force-rebuild", help="忽略缓存"),
    chunk_size: int = typer.Option(DEFAULT_CHUNK_SIZE, help="chunk size"),
    overlap: int = typer.Option(DEFAULT_OVERLAP, help="overlap"),
    embed_dim: int = typer.Option(DEFAULT_EMBED_DIM, help="向量维度"),
    embed_backend: str = typer.Option(DEFAULT_EMBED_BACKEND, help="embedding 后端（auto/sentence_transformers/hash）"),
) -> None:
    """单次问答：给定问题，返回答案与来源。"""
    from pipeline import answer_with_store, build_runtime, render_response

    vs, fi = build_runtime(force_rebuild=force_rebuild, chunk_size=chunk_size, overlap=overlap, embed_dim=embed_dim, embed_backend=embed_backend)
    response = answer_with_store(
        question,
        vs,
        faiss_index=fi,
        top_k=top_k,
        use_hybrid=hybrid,
        use_rerank=rerank,
        rerank_initial_k=rerank_initial_k,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        temperature=temperature,
        llm_timeout=llm_timeout,
        llm_max_retries=llm_max_retries,
        llm_fallback_local=not no_fallback,
        min_relevance_score=None if min_relevance_score <= 0 else min_relevance_score,
    )
    typer.echo(render_response(response, include_debug=debug))


# ── chat ───────────────────────────────────────────

@app.command()
def chat(
    top_k: int = typer.Option(DEFAULT_TOP_K, help="检索 top_k"),
    hybrid: bool = typer.Option(DEFAULT_USE_HYBRID, "--hybrid/--no-hybrid", help="启用 BM25 + Dense 混合检索"),
    rerank: bool = typer.Option(DEFAULT_USE_RERANK, "--rerank/--no-rerank", help="启用 Cross-Encoder 重排"),
    rerank_initial_k: int = typer.Option(DEFAULT_RERANK_INITIAL_K, help="Rerank 前粗召回数量"),
    llm_provider: str = typer.Option(_provider_default(), help="LLM provider"),
    llm_model: str = typer.Option(_model_default(), help="模型名"),
    llm_base_url: str = typer.Option(_base_url_default(), help="Base URL"),
    temperature: float = typer.Option(DEFAULT_TEMPERATURE, help="采样温度"),
    llm_timeout: float = typer.Option(DEFAULT_LLM_TIMEOUT, help="超时（秒）"),
    llm_max_retries: int = typer.Option(DEFAULT_LLM_MAX_RETRIES, help="重试次数"),
    min_relevance_score: float = typer.Option(0.0, help="最小相关度阈值"),
    no_fallback: bool = typer.Option(False, "--no-fallback", help="失败时不回退本地"),
    debug: bool = typer.Option(False, "--debug", help="输出调试信息"),
    force_rebuild: bool = typer.Option(False, "--force-rebuild", help="忽略缓存"),
    chunk_size: int = typer.Option(DEFAULT_CHUNK_SIZE, help="chunk size"),
    overlap: int = typer.Option(DEFAULT_OVERLAP, help="overlap"),
    embed_dim: int = typer.Option(DEFAULT_EMBED_DIM, help="向量维度"),
    embed_backend: str = typer.Option(DEFAULT_EMBED_BACKEND, help="embedding 后端（auto/sentence_transformers/hash）"),
) -> None:
    """交互式 REPL：输入问题回车，输入 exit/quit 退出。"""
    from pipeline import answer_with_store, build_runtime, render_response

    vs, fi = build_runtime(force_rebuild=force_rebuild, chunk_size=chunk_size, overlap=overlap, embed_dim=embed_dim, embed_backend=embed_backend)
    typer.echo("RAG CLI 已启动。输入问题后回车；输入 exit/quit 退出。")
    while True:
        q = input("\nQuestion> ").strip()
        if q.lower() in {"exit", "quit"}:
            typer.echo("Bye.")
            return
        if not q:
            continue
        response = answer_with_store(
            q,
            vs,
            faiss_index=fi,
            top_k=top_k,
            use_hybrid=hybrid,
            use_rerank=rerank,
            rerank_initial_k=rerank_initial_k,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            temperature=temperature,
            llm_timeout=llm_timeout,
            llm_max_retries=llm_max_retries,
            llm_fallback_local=not no_fallback,
            min_relevance_score=None if min_relevance_score <= 0 else min_relevance_score,
        )
        typer.echo(render_response(response, include_debug=debug))


# ── eval ───────────────────────────────────────────

@app.command(name="eval")
def evaluate(
    eval_set: str = typer.Option("eval/eval_set.example.json", help="评测集 JSON 路径"),
    output: str = typer.Option("artifacts/eval/latest_report.json", help="报告输出路径"),
    top_k: int = typer.Option(DEFAULT_TOP_K, help="默认检索 top_k"),
    hybrid: bool = typer.Option(DEFAULT_USE_HYBRID, "--hybrid/--no-hybrid", help="启用 BM25 + Dense 混合检索"),
    rerank: bool = typer.Option(DEFAULT_USE_RERANK, "--rerank/--no-rerank", help="启用 Cross-Encoder 重排"),
    rerank_initial_k: int = typer.Option(DEFAULT_RERANK_INITIAL_K, help="Rerank 前粗召回数量"),
    llm_provider: str = typer.Option(_provider_default(), help="LLM provider"),
    llm_model: str = typer.Option(_model_default(), help="模型名"),
    llm_base_url: str = typer.Option(_base_url_default(), help="Base URL"),
    temperature: float = typer.Option(DEFAULT_TEMPERATURE, help="采样温度"),
    llm_timeout: float = typer.Option(DEFAULT_LLM_TIMEOUT, help="超时（秒）"),
    llm_max_retries: int = typer.Option(DEFAULT_LLM_MAX_RETRIES, help="重试次数"),
    min_relevance_score: float = typer.Option(0.0, help="最小相关度阈值"),
    no_fallback: bool = typer.Option(False, "--no-fallback", help="失败时不回退本地"),
    force_rebuild: bool = typer.Option(False, "--force-rebuild", help="忽略缓存"),
    chunk_size: int = typer.Option(DEFAULT_CHUNK_SIZE, help="chunk size"),
    overlap: int = typer.Option(DEFAULT_OVERLAP, help="overlap"),
    embed_dim: int = typer.Option(DEFAULT_EMBED_DIM, help="向量维度"),
    embed_backend: str = typer.Option(DEFAULT_EMBED_BACKEND, help="embedding 后端（auto/sentence_transformers/hash）"),
) -> None:
    """批量评估：跑评测集并输出指标报告。"""
    import json
    from pathlib import Path

    from evaluation import evaluate_cases, load_eval_cases
    from pipeline import answer_with_store, build_runtime

    cases = load_eval_cases(eval_set)
    vs, fi = build_runtime(force_rebuild=force_rebuild, chunk_size=chunk_size, overlap=overlap, embed_dim=embed_dim, embed_backend=embed_backend)

    def _answer_fn(case: dict) -> dict:
        case_top_k = int(case.get("top_k", top_k))
        return answer_with_store(
            query=str(case["query"]),
            vector_store=vs,
            faiss_index=fi,
            top_k=case_top_k,
            use_hybrid=hybrid,
            use_rerank=rerank,
            rerank_initial_k=rerank_initial_k,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            temperature=temperature,
            llm_timeout=llm_timeout,
            llm_max_retries=llm_max_retries,
            llm_fallback_local=not no_fallback,
            min_relevance_score=None if min_relevance_score <= 0 else min_relevance_score,
        )

    report = evaluate_cases(cases, _answer_fn)
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    s = report["summary"]
    typer.echo("[EVAL] 评估完成")
    typer.echo(f"  样本数: {s['total_cases']}")
    typer.echo(f"  answer_exact_match_avg: {s['answer_exact_match_avg']}")
    typer.echo(f"  answer_token_f1_avg: {s['answer_token_f1_avg']}")
    typer.echo(f"  keyword_recall_avg: {s['keyword_recall_avg']}")
    typer.echo(f"  source_recall_avg: {s['source_recall_avg']}")
    typer.echo(f"  source_hit_rate: {s['source_hit_rate']}")
    typer.echo(f"  报告路径: {out}")


# ── web ────────────────────────────────────────────

@app.command()
def web() -> None:
    """启动 Streamlit Web UI。"""
    typer.echo("[WEB] 启动 Streamlit …")
    subprocess.run([sys.executable, "-m", "streamlit", "run", "web_app.py"], check=False)


if __name__ == "__main__":
    app()
