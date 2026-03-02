"""
Phase 4 应用入口（CLI UI）
提供交互式问答界面，串联 Retrieval -> Prompt -> LLM -> Response。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from datetime import datetime

from formatter import format_response
from generator import generate_answer_with_meta
from main import build_or_load_chunks, build_or_load_faiss_index, build_or_load_vectors
from prompt import build_prompt
from retriever import retrieve_top_k


def _load_env_defaults(path: str = ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return values
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def answer_with_store(
    query: str,
    vector_store: object,
    *,
    faiss_index: object | None = None,
    top_k: int = 3,
    llm_provider: str = "local",
    llm_model: str = "gpt-4o-mini",
    llm_base_url: str = "",
    temperature: float = 0.2,
    llm_timeout: float = 120.0,
    llm_max_retries: int = 1,
    llm_fallback_local: bool = True,
) -> dict:
    if top_k <= 0:
        raise ValueError("top_k 必须为正整数")
    retrieved = retrieve_top_k(
        query,
        vector_store,  # type: ignore[arg-type]
        top_k=top_k,
        faiss_index=faiss_index,
    )
    prompt_text = build_prompt(query, retrieved)
    answer, llm_meta = generate_answer_with_meta(
        prompt_text,
        contexts=retrieved,
        provider=llm_provider,
        model=llm_model,
        base_url=llm_base_url or None,
        temperature=temperature,
        timeout=llm_timeout,
        max_retries=llm_max_retries,
        fallback_to_local=llm_fallback_local,
    )
    response = format_response(answer, retrieved)
    response["debug"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "used_remote_llm": bool(llm_meta.get("used_remote_llm", False)),
        "requested_provider": llm_meta.get("requested_provider"),
        "used_provider": llm_meta.get("used_provider"),
        "llm_model": llm_model,
        "llm_base_url": llm_base_url or "(none)",
        "fallback_enabled": llm_fallback_local,
        "fallback_triggered": bool(llm_meta.get("fallback_triggered", False)),
        "llm_attempts": int(llm_meta.get("attempts", 0)),
        "llm_error": llm_meta.get("error"),
        "top_k_requested": int(top_k),
        "retrieved_chunks": len(retrieved),
        "faiss_enabled": faiss_index is not None,
        "sources_returned": len(response.get("sources", [])),
    }
    return response


def build_runtime(
    *,
    force_rebuild: bool = False,
    chunk_size: int = 500,
    overlap: int = 50,
    embed_dim: int = 256,
) -> tuple[object, object | None]:
    chunks, _ = build_or_load_chunks(
        force_rebuild=force_rebuild,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    vector_store, _ = build_or_load_vectors(
        chunks,
        force_rebuild=force_rebuild,
        dim=embed_dim,
    )
    faiss_index, _ = build_or_load_faiss_index(vector_store, force_rebuild=force_rebuild)
    return vector_store, faiss_index


def _debug_to_lines(debug: dict) -> list[str]:
    return [
        f"- used_remote_llm: {debug.get('used_remote_llm')}",
        f"- requested_provider: {debug.get('requested_provider')}",
        f"- used_provider: {debug.get('used_provider')}",
        f"- llm_model: {debug.get('llm_model')}",
        f"- llm_base_url: {debug.get('llm_base_url')}",
        f"- top_k_requested: {debug.get('top_k_requested')}",
        f"- retrieved_chunks: {debug.get('retrieved_chunks')}",
        f"- faiss_enabled: {debug.get('faiss_enabled')}",
        f"- sources_returned: {debug.get('sources_returned')}",
        f"- fallback_enabled: {debug.get('fallback_enabled')}",
        f"- fallback_triggered: {debug.get('fallback_triggered')}",
        f"- llm_attempts: {debug.get('llm_attempts')}",
        f"- llm_error: {debug.get('llm_error')}",
    ]


def render_response(response: dict, *, include_debug: bool = False) -> str:
    lines = [f"Answer: {response.get('answer', '')}", "", "Sources:"]
    sources = response.get("sources", [])
    if not sources:
        lines.append("- (none)")
    else:
        for s in sources:
            lines.append(f"- {s.get('source')} (page {s.get('page')})")
    if include_debug:
        lines.extend(["", "Debug:", *_debug_to_lines(response.get("debug", {}))])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    env_defaults = _load_env_defaults(".env")
    parser = argparse.ArgumentParser(description="RAG-Demo Phase 4 CLI 应用入口")
    parser.add_argument("--query", type=str, default="", help="单次查询；留空则进入交互模式")
    parser.add_argument("--top-k", type=int, default=3, help="检索 top_k（默认 3）")
    parser.add_argument("--force-rebuild", action="store_true", help="忽略缓存，重建中间结果")
    parser.add_argument("--chunk-size", type=int, default=500, help="chunk size（默认 500）")
    parser.add_argument("--overlap", type=int, default=50, help="chunk overlap（默认 50）")
    parser.add_argument("--embed-dim", type=int, default=256, help="embedding 维度（默认 256）")

    parser.add_argument(
        "--llm-provider",
        type=str,
        default=os.getenv("LLM_PROVIDER") or env_defaults.get("LLM_PROVIDER", "local"),
        choices=["local", "openai", "openai_compatible"],
        help="LLM provider：local/openai/openai_compatible",
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default=os.getenv("LLM_MODEL") or env_defaults.get("LLM_MODEL", "gpt-4o-mini"),
        help="模型名（对 openai/openai_compatible 生效）",
    )
    parser.add_argument(
        "--llm-base-url",
        type=str,
        default=os.getenv("LLM_BASE_URL") or env_defaults.get("LLM_BASE_URL", ""),
        help="OpenAI 兼容接口 base_url",
    )
    parser.add_argument("--temperature", type=float, default=0.2, help="采样温度（默认 0.2）")
    parser.add_argument("--llm-timeout", type=float, default=120.0, help="LLM 超时时间（秒）")
    parser.add_argument("--llm-max-retries", type=int, default=1, help="LLM 重试次数（默认 1）")
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
