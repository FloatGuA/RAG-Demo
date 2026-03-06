"""离线构建逻辑 — chunks / vectors / FAISS index 的 cache-first 加载与构建。"""

from __future__ import annotations

from config.defaults import DEFAULT_CHUNK_SIZE, DEFAULT_EMBED_BACKEND, DEFAULT_EMBED_DIM, DEFAULT_OVERLAP
from config.paths import (
    CHUNKS_PATH,
    FAISS_INDEX_PATH,
    LEGACY_CHUNKS_PATH,
    LEGACY_VECTORS_PATH,
    VECTORS_PATH,
)

from ingestion import (
    chunk_documents,
    chunks_to_dicts,
    dicts_to_chunks,
    load_chunks,
    save_chunks,
    load_documents_from_dir,
    build_faiss_index,
    build_vector_store,
    has_faiss,
    load_faiss_index,
    load_vectors,
    save_faiss_index,
    save_vectors,
)


def build_or_load_chunks(
    *,
    force_rebuild: bool = False,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> tuple[list, str]:
    """
    返回 (chunks, source)，source 为 'cache' | 'migrated' | 'rebuild'。
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

    docs = load_documents_from_dir("data")
    chunks = chunk_documents(docs, chunk_size=chunk_size, overlap=overlap)
    save_chunks(chunks_to_dicts(chunks), str(CHUNKS_PATH))
    return chunks, "rebuild"


def build_or_load_vectors(
    chunks: list,
    *,
    force_rebuild: bool = False,
    dim: int = DEFAULT_EMBED_DIM,
    backend: str = DEFAULT_EMBED_BACKEND,
) -> tuple[object, str]:
    """
    返回 (vector_store, source)，source 为 'cache' | 'migrated' | 'rebuild'。

    迁移策略：若新 .npz 缓存不存在但旧 .json 缓存存在，自动迁移并保存为 .npz。
    """
    if dim <= 0:
        raise ValueError("embed_dim 必须为正整数")

    if not force_rebuild and VECTORS_PATH.exists():
        store = load_vectors(str(VECTORS_PATH))
        return store, "cache"

    if not force_rebuild and LEGACY_VECTORS_PATH.exists():
        store = load_vectors(str(LEGACY_VECTORS_PATH))
        save_vectors(store, str(VECTORS_PATH))
        return store, "migrated"

    raw_chunks = chunks_to_dicts(chunks)
    store = build_vector_store(raw_chunks, dim=dim, backend=backend)
    save_vectors(store, str(VECTORS_PATH))
    return store, "rebuild"


def build_or_load_faiss_index(
    vector_store: object,
    *,
    force_rebuild: bool = False,
) -> tuple[object | None, str]:
    """
    返回 (faiss_index | None, source)，source 为 'unavailable' | 'cache' | 'rebuild'。
    """
    if not has_faiss():
        return None, "unavailable"

    if not force_rebuild and FAISS_INDEX_PATH.exists():
        return load_faiss_index(str(FAISS_INDEX_PATH)), "cache"

    index = build_faiss_index(vector_store)  # type: ignore[arg-type]
    save_faiss_index(index, str(FAISS_INDEX_PATH))
    return index, "rebuild"


def build_runtime(
    *,
    force_rebuild: bool = False,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
    embed_dim: int = DEFAULT_EMBED_DIM,
    embed_backend: str = DEFAULT_EMBED_BACKEND,
) -> tuple[object, object | None]:
    """一步构建/加载完整运行时（vector_store + faiss_index）。"""
    chunks, _ = build_or_load_chunks(
        force_rebuild=force_rebuild,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    vector_store, _ = build_or_load_vectors(
        chunks,
        force_rebuild=force_rebuild,
        dim=embed_dim,
        backend=embed_backend,
    )
    faiss_index, _ = build_or_load_faiss_index(vector_store, force_rebuild=force_rebuild)
    return vector_store, faiss_index
