"""
项目主流程入口（Phase 1）

功能：
1) 优先加载已有 chunk 缓存；
2) 若无缓存则从 data/ 读取 PDF -> chunking -> 持久化；
3) 打印流程统计与样例预览。
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

from chunking import chunk_documents, chunks_to_dicts, dicts_to_chunks, load_chunks, save_chunks
from embedding import (
    build_faiss_index,
    build_vector_store,
    has_faiss,
    load_faiss_index,
    load_vectors,
    save_faiss_index,
    save_vectors,
)
from formatter import format_response
from generator import generate_answer
from loader import load_pdfs_from_dir
from prompt import build_prompt
from retriever import retrieve_top_k


CHUNKS_PATH = Path("artifacts/chunks/chunks.json")
LEGACY_CHUNKS_PATH = Path("storage/chunks.json")
VECTORS_PATH = Path("artifacts/vectors/vectors.json")
FAISS_INDEX_PATH = Path("artifacts/index/faiss.index")


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


def build_or_load_chunks(
    *,
    force_rebuild: bool = False,
    chunk_size: int = 500,
    overlap: int = 50,
) -> tuple[list, str]:
    """
    返回 chunks 以及来源说明（cache/rebuild/migrated）。
    """
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    if not force_rebuild and CHUNKS_PATH.exists():
        raw_chunks = load_chunks(str(CHUNKS_PATH))
        return dicts_to_chunks(raw_chunks), "cache"

    if not force_rebuild and LEGACY_CHUNKS_PATH.exists():
        raw_chunks = load_chunks(str(LEGACY_CHUNKS_PATH))
        save_chunks(raw_chunks, str(CHUNKS_PATH))
        return dicts_to_chunks(raw_chunks), "migrated"

    docs = load_pdfs_from_dir("data")
    chunks = chunk_documents(docs, chunk_size=chunk_size, overlap=overlap)
    save_chunks(chunks_to_dicts(chunks), str(CHUNKS_PATH))
    return chunks, "rebuild"


def build_or_load_vectors(
    chunks: list,
    *,
    force_rebuild: bool = False,
    dim: int = 256,
) -> tuple[object, str]:
    """
    返回 vectors store 以及来源说明（cache/rebuild）。
    """
    if dim <= 0:
        raise ValueError("embed_dim 必须为正整数")

    if not force_rebuild and VECTORS_PATH.exists():
        store = load_vectors(str(VECTORS_PATH))
        return store, "cache"

    raw_chunks = chunks_to_dicts(chunks)
    store = build_vector_store(raw_chunks, dim=dim)
    save_vectors(store, str(VECTORS_PATH))
    return store, "rebuild"


def build_or_load_faiss_index(
    vector_store: object,
    *,
    force_rebuild: bool = False,
) -> tuple[object | None, str]:
    """
    返回 faiss index 及来源说明：
    - unavailable: 环境不支持 faiss
    - cache: 读取已有索引
    - rebuild: 新构建并保存
    """
    if not has_faiss():
        return None, "unavailable"

    if not force_rebuild and FAISS_INDEX_PATH.exists():
        return load_faiss_index(str(FAISS_INDEX_PATH)), "cache"

    index = build_faiss_index(vector_store)  # type: ignore[arg-type]
    save_faiss_index(index, str(FAISS_INDEX_PATH))
    return index, "rebuild"


def parse_args() -> argparse.Namespace:
    env_defaults = _load_env_defaults(".env")
    parser = argparse.ArgumentParser(description="RAG-Demo 主流程入口（offline + online）")
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="忽略缓存，强制重新构建 chunks",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="每个 chunk 的最大字符数（默认 500）",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=50,
        help="chunk 之间重叠字符数（默认 50）",
    )
    parser.add_argument(
        "--preview",
        type=int,
        default=3,
        help="打印前 N 个 chunk 预览（默认 3）",
    )
    parser.add_argument(
        "--embed-dim",
        type=int,
        default=256,
        help="向量维度（默认 256）",
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
        default=3,
        help="在线检索返回的 Top-k 条上下文数量（默认 3）",
    )
    parser.add_argument(
        "--use-openai",
        action="store_true",
        help="兼容旧参数：等价于 --llm-provider openai",
    )
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
        default=0.2,
        help="采样温度（默认 0.2）",
    )
    parser.add_argument(
        "--llm-timeout",
        type=float,
        default=120.0,
        help="LLM 请求超时时间秒（默认 120）",
    )
    parser.add_argument(
        "--llm-max-retries",
        type=int,
        default=1,
        help="LLM 失败重试次数（默认 1）",
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
        print(f"[MAIN] 检测到旧缓存 {LEGACY_CHUNKS_PATH}，已迁移到 {CHUNKS_PATH}")
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
        retrieved = retrieve_top_k(
            args.query,
            vector_store,
            top_k=args.top_k,
            faiss_index=None if faiss_source == "unavailable" else faiss_index,
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
