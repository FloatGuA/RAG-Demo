"""
Phase 4 应用入口（CLI UI）
提供交互式问答界面，串联 Retrieval -> Prompt -> LLM -> Response。
"""

from __future__ import annotations

import argparse
import os

from config.defaults import (
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBED_DIM,
    DEFAULT_LLM_MAX_RETRIES,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_OVERLAP,
    DEFAULT_TOP_K,
    DEFAULT_TEMPERATURE,
)
from config.env import get_llm_default, load_env_defaults
from pipeline import answer_with_store, build_runtime, render_response


def parse_args() -> argparse.Namespace:
    env_defaults = load_env_defaults(".env")
    parser = argparse.ArgumentParser(description="RAG-Demo Phase 4 CLI 应用入口")
    parser.add_argument("--query", type=str, default="", help="单次查询；留空则进入交互模式")
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K, help=f"检索 top_k（默认 {DEFAULT_TOP_K}）")
    parser.add_argument("--force-rebuild", action="store_true", help="忽略缓存，重建中间结果")
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help=f"chunk size（默认 {DEFAULT_CHUNK_SIZE}）")
    parser.add_argument("--overlap", type=int, default=DEFAULT_OVERLAP, help=f"chunk overlap（默认 {DEFAULT_OVERLAP}）")
    parser.add_argument("--embed-dim", type=int, default=DEFAULT_EMBED_DIM, help=f"embedding 维度（默认 {DEFAULT_EMBED_DIM}）")

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
        help="OpenAI 兼容接口 base_url",
    )
    parser.add_argument("--temperature", type=float, default=DEFAULT_TEMPERATURE, help=f"采样温度（默认 {DEFAULT_TEMPERATURE}）")
    parser.add_argument("--llm-timeout", type=float, default=DEFAULT_LLM_TIMEOUT, help=f"LLM 超时时间（秒，默认 {DEFAULT_LLM_TIMEOUT}）")
    parser.add_argument("--llm-max-retries", type=int, default=DEFAULT_LLM_MAX_RETRIES, help=f"LLM 重试次数（默认 {DEFAULT_LLM_MAX_RETRIES}）")
    parser.add_argument(
        "--min-relevance-score",
        type=float,
        default=0.0,
        help="检索最小相关度阈值（0 表示关闭；低于阈值的上下文将被丢弃）",
    )
    parser.add_argument(
        "--no-llm-fallback-local",
        action="store_true",
        help="LLM 失败时不回退本地占位答案",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="输出调试信息（provider、检索 chunk 数、faiss、回退状态等）",
    )
    return parser.parse_args()


def run_single_query(args: argparse.Namespace, vector_store: object, faiss_index: object | None) -> None:
    response = answer_with_store(
        args.query,
        vector_store,
        faiss_index=faiss_index,
        top_k=args.top_k,
        llm_provider=args.llm_provider,
        llm_model=args.llm_model,
        llm_base_url=args.llm_base_url,
        temperature=args.temperature,
        llm_timeout=args.llm_timeout,
        llm_max_retries=args.llm_max_retries,
        llm_fallback_local=not args.no_llm_fallback_local,
        min_relevance_score=None if args.min_relevance_score <= 0 else float(args.min_relevance_score),
    )
    print(render_response(response, include_debug=args.debug))


def run_interactive(args: argparse.Namespace, vector_store: object, faiss_index: object | None) -> None:
    print("RAG CLI 已启动。输入问题后回车；输入 exit/quit 退出。")
    while True:
        query = input("\nQuestion> ").strip()
        if query.lower() in {"exit", "quit"}:
            print("Bye.")
            return
        if not query:
            continue
        response = answer_with_store(
            query,
            vector_store,
            faiss_index=faiss_index,
            top_k=args.top_k,
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
        print(render_response(response, include_debug=args.debug))


def main() -> None:
    args = parse_args()
    vector_store, faiss_index = build_runtime(
        force_rebuild=args.force_rebuild,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        embed_dim=args.embed_dim,
    )
    if args.query.strip():
        run_single_query(args, vector_store, faiss_index)
    else:
        run_interactive(args, vector_store, faiss_index)


if __name__ == "__main__":
    main()
