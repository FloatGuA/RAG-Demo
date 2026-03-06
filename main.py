"""
项目主流程入口（Phase 1）

功能：
1) 优先加载已有 chunk 缓存；
2) 若无缓存则从 data/ 读取文档（pdf/pptx/docx/md）-> chunking -> 持久化；
3) 打印流程统计与样例预览。
"""

from __future__ import annotations

import argparse
import os
import sys

from ingestion import chunks_to_dicts
from config.defaults import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBED_DIM,
    DEFAULT_LLM_MAX_RETRIES,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_OVERLAP,
    DEFAULT_PREVIEW,
    DEFAULT_TOP_K,
    DEFAULT_TEMPERATURE,
)
from config.env import get_llm_default, load_env_defaults
from config.paths import CHUNKS_PATH, FAISS_INDEX_PATH, VECTORS_PATH
from retrieval import format_response, generate_answer, build_prompt, retrieve_top_k
from pipeline.build import build_or_load_chunks, build_or_load_faiss_index, build_or_load_vectors


def parse_args() -> argparse.Namespace:
    env_defaults = load_env_defaults()
    parser = argparse.ArgumentParser(description="RAG-Demo 主流程入口（offline + online）")
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="忽略缓存，强制重新构建 chunks",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"每个 chunk 的最大字符数（默认 {DEFAULT_CHUNK_SIZE}）",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help=f"chunk 之间重叠字符数（默认 {DEFAULT_OVERLAP}）",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=DEFAULT_PREVIEW,
        help=f"打印前 N 个 chunk 预览（默认 {DEFAULT_PREVIEW}）",
    )
    parser.add_argument(
        "--embed-dim",
        type=int,
        default=DEFAULT_EMBED_DIM,
        help=f"向量维度（默认 {DEFAULT_EMBED_DIM}）",
    )
    parser.add_argument(
        "--query",
        type=str,
        default="",
        help="可选：执行在线查询（Query → Retrieval → Prompt → Generator）",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=DEFAULT_TOP_K,
        help=f"在线检索返回的 Top-k 条上下文数量（默认 {DEFAULT_TOP_K}）",
    )
    parser.add_argument(
        "--min-relevance-score",
        type=float,
        default=0.0,
        help="检索最小相关度阈值（0 表示关闭；低于阈值的上下文将被丢弃）",
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="兼容旧参数：等价于 --llm-provider openai",
    )
    parser.add_argument(
        "--llm-provider",
        type=str,
        default=get_llm_default("LLM_PROVIDER", DEFAULT_LLM_PROVIDER, env_defaults=env_defaults),
        choices=["local", "openai", "openai_compatible"],
        help="LLM provider：local/openai/openai_compatible",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=get_llm_default("LLM_MODEL", DEFAULT_LLM_MODEL, env_defaults=env_defaults),
        help="模型名（对 openai/openai_compatible 生效）",
    )
    parser.add_argument(
        "--llm-base-url",
        type=str,
        default=get_llm_default("LLM_BASE_URL", "", env_defaults=env_defaults),
        help="OpenAI 兼容接口的 base_url（如本地服务）",
    )
    parser.add_argument(
        "--llm-api-key-env",
        type=str,
        default="OPENAI_API_KEY",
        help="读取 API Key 的环境变量名（默认 OPENAI_API_KEY）",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=DEFAULT_TEMPERATURE,
        help=f"采样温度（默认 {DEFAULT_TEMPERATURE}）",
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=DEFAULT_LLM_TIMEOUT,
        help=f"LLM 请求超时时间秒（默认 {DEFAULT_LLM_TIMEOUT}）",
    )
    parser.add_argument(
        "--llm-max-retries",
        type=int,
        default=DEFAULT_LLM_MAX_RETRIES,
        help=f"LLM 失败重试次数（默认 {DEFAULT_LLM_MAX_RETRIES}）",
    )
    parser.add_argument(
        "--no-llm-fallback-local",
        action="store_true",
        help="LLM 调用失败时不回退到本地占位实现，直接报错",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    CHUNKS_PATH.parent.mkdir(parents=True, exist_ok=True)
    VECTORS_PATH.parent.mkdir(parents=True, exist_ok=True)
    FAISS_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    chunks, source = build_or_load_chunks(
        force_rebuild=args.force_rebuild,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    vector_store, vector_source = build_or_load_vectors(
        chunks,
        force_rebuild=args.force_rebuild,
        dim=args.embed_dim,
    )
    faiss_index, faiss_source = build_or_load_faiss_index(
        vector_store,
        force_rebuild=args.force_rebuild,
    )

    if source == "cache":
        print(f"[MAIN] 使用缓存: {CHUNKS_PATH}")
    elif source == "migrated":
        print(f"[MAIN] 检测到旧缓存 {CHUNKS_PATH}，已迁移到 {CHUNKS_PATH}")
    else:
        print(f"[MAIN] 新构建完成并保存到: {CHUNKS_PATH}")

    print(f"[MAIN] 当前 chunks 数量: {len(chunks)}")
    if vector_source == "cache":
        print(f"[MAIN] 向量缓存命中: {VECTORS_PATH}")
    else:
        print(f"[MAIN] 向量新构建并保存到: {VECTORS_PATH}")
    print(f"[MAIN] 向量维度: {vector_store.dim}，向量数量: {len(vector_store.vectors)}")
    if faiss_source == "unavailable":
        print("[MAIN] FAISS 不可用：已跳过索引构建（安装 faiss-cpu 后可启用）")
    elif faiss_source == "cache":
        print(f"[MAIN] FAISS 索引缓存命中: {FAISS_INDEX_PATH}")
    else:
        print(f"[MAIN] FAISS 索引新构建并保存到: {FAISS_INDEX_PATH}")
    print(f"[MAIN] 预览前 {args.preview} 个 chunks:")
    stdout_encoding = sys.stdout.encoding or "utf-8"
    for c in chunks[: max(args.preview, 0)]:
        preview_text = c.text[:80]
        safe_preview_text = preview_text.encode(stdout_encoding, errors="replace").decode(
            stdout_encoding,
            errors="replace",
        )
        print(f"  - [{c.source} p.{c.page}] {safe_preview_text}...")

    if args.query.strip():
        if args.top_k <= 0:
            raise ValueError("top_k 必须为正整数")
        if not (0.0 <= float(args.min_relevance_score) <= 1.0):
            raise ValueError("min_relevance_score 必须在 [0, 1] 区间内")
        retrieved = retrieve_top_k(
            args.query,
            vector_store,
            top_k=args.top_k,
            faiss_index=None if faiss_source == "unavailable" else faiss_index,
        )
        best_retrieval_score = float(retrieved[0]["score"]) if retrieved else None
        if args.min_relevance_score > 0:
            retrieved = [r for r in retrieved if float(r.get("score", -1.0)) >= args.min_relevance_score]
            if best_retrieval_score is not None and not retrieved:
                print(
                    "[ONLINE] 触发低相关过滤："
                    f"best_score={best_retrieval_score:.4f} < min_relevance_score={args.min_relevance_score:.4f}"
                )
        prompt_text = build_prompt(args.query, retrieved)
        provider = "openai" if args.use_openai else args.llm_provider
        answer = generate_answer(
            prompt_text,
            contexts=retrieved,
            provider=provider,
            model=args.llm_model,
            temperature=args.temperature,
            base_url=args.llm_base_url or None,
            api_key_env=args.llm_api_key_env,
            timeout=args.llm_timeout,
            max_retries=args.llm_max_retries,
            fallback_to_local=not args.no_llm_fallback_local,
        )
        response = format_response(answer, retrieved)

        print("\n[ONLINE] 查询完成")
        print(f"[ONLINE] Query: {args.query}")
        print(f"[ONLINE] Retrieved: {len(retrieved)}")
        print(f"[ONLINE] Answer: {response['answer']}")
        if response["sources"]:
            print("[ONLINE] Sources:")
            for s in response["sources"]:
                print(f"  - {s['source']} p.{s['page']}")
        else:
            print("[ONLINE] Sources: (none)")


if __name__ == "__main__":
    main()
