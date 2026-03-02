"""
项目主流程入口（Phase 1）

功能：
1) 优先加载已有 chunk 缓存；
2) 若无缓存则从 data/ 读取 PDF -> chunking -> 持久化；
3) 打印流程统计与样例预览。
"""

from __future__ import annotations

import argparse
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
from loader import load_pdfs_from_dir


CHUNKS_PATH = Path("artifacts/chunks/chunks.json")
LEGACY_CHUNKS_PATH = Path("storage/chunks.json")
VECTORS_PATH = Path("artifacts/vectors/vectors.json")
FAISS_INDEX_PATH = Path("artifacts/index/faiss.index")


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
    parser = argparse.ArgumentParser(description="RAG-Demo Phase 1 主流程入口")
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
    _, faiss_source = build_or_load_faiss_index(
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


if __name__ == "__main__":
    main()
