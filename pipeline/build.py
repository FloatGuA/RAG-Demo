"""离线构建逻辑 — chunks / vectors / FAISS index 的 cache-first 加载与构建。"""

from __future__ import annotations

import json
import os

from config.defaults import DEFAULT_CHUNK_SIZE, DEFAULT_EMBED_BACKEND, DEFAULT_EMBED_DIM, DEFAULT_OVERLAP
from config.paths import (
    CHUNKS_PATH,
    FAISS_INDEX_PATH,
    LEGACY_CHUNKS_PATH,
    LEGACY_VECTORS_PATH,
    MANIFEST_PATH,
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
    embed_text,
)
from ingestion.embedding import VectorStore


# ── Manifest helpers ─────────────────────────────────────────────────────────

def _load_manifest() -> dict[str, float]:
    """加载文件清单（filepath → mtime），不存在时返回空 dict。"""
    if not MANIFEST_PATH.exists():
        return {}
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_manifest(manifest: dict[str, float]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def _scan_data_dir(data_dir: str = "data") -> dict[str, float]:
    """扫描 data 目录，返回 {相对路径: mtime}。"""
    result: dict[str, float] = {}
    base = os.path.abspath(data_dir)
    if not os.path.isdir(base):
        return result
    for root, _, files in os.walk(base):
        for fname in files:
            fpath = os.path.join(root, fname)
            rel = os.path.relpath(fpath, start=".").replace("\\", "/")
            result[rel] = os.path.getmtime(fpath)
    return result


# ── Core builders ─────────────────────────────────────────────────────────────

def build_or_load_chunks(
    *,
    force_rebuild: bool = False,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> tuple[list, str, list]:
    """
    返回 (all_chunks, source, new_chunks)。
    source: 'cache' | 'migrated' | 'rebuild' | 'incremental'
    new_chunks: 本次新处理的 chunks（cache 时为空列表）

    增量策略：
    - cache 命中 + 有新文件 → 只处理新文件，合并到已有 chunks
    - 检测到已有文件修改或删除 → 打印警告，建议 --force-rebuild
    - force_rebuild=True → 全量重建
    """
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    # ── 全量重建 ─────────────────────────────────────────────────────────────
    if force_rebuild:
        docs = load_documents_from_dir("data")
        chunks = chunk_documents(docs, chunk_size=chunk_size, overlap=overlap)
        save_chunks(chunks_to_dicts(chunks), str(CHUNKS_PATH))
        manifest = _scan_data_dir()
        _save_manifest(manifest)
        return chunks, "rebuild", chunks

    # ── 旧格式迁移 ────────────────────────────────────────────────────────────
    if not CHUNKS_PATH.exists() and LEGACY_CHUNKS_PATH.exists():
        raw_chunks = load_chunks(str(LEGACY_CHUNKS_PATH))
        save_chunks(raw_chunks, str(CHUNKS_PATH))
        chunks = dicts_to_chunks(raw_chunks)
        _save_manifest(_scan_data_dir())
        return chunks, "migrated", chunks

    # ── 无缓存全量构建 ────────────────────────────────────────────────────────
    if not CHUNKS_PATH.exists():
        docs = load_documents_from_dir("data")
        chunks = chunk_documents(docs, chunk_size=chunk_size, overlap=overlap)
        save_chunks(chunks_to_dicts(chunks), str(CHUNKS_PATH))
        _save_manifest(_scan_data_dir())
        return chunks, "rebuild", chunks

    # ── 有缓存：检查增量 ──────────────────────────────────────────────────────
    existing_raw = load_chunks(str(CHUNKS_PATH))
    existing_chunks = dicts_to_chunks(existing_raw)

    manifest = _load_manifest()
    current_files = _scan_data_dir()

    new_files = {p: mt for p, mt in current_files.items() if p not in manifest}
    changed_files = {p for p in current_files if p in manifest and current_files[p] != manifest[p]}
    removed_files = {p for p in manifest if p not in current_files}

    if changed_files or removed_files:
        import warnings
        msg_parts = []
        if changed_files:
            msg_parts.append(f"已修改文件 {sorted(changed_files)}")
        if removed_files:
            msg_parts.append(f"已删除文件 {sorted(removed_files)}")
        warnings.warn(
            f"[增量索引] 检测到 {', '.join(msg_parts)}。"
            "已修改/删除的内容不会自动更新，请运行 --force-rebuild 重建完整索引。",
            UserWarning,
            stacklevel=3,
        )

    if not new_files:
        return existing_chunks, "cache", []

    # 处理新文件
    new_docs = []
    for fpath in sorted(new_files):
        abs_path = os.path.abspath(fpath)
        if os.path.exists(abs_path):
            from ingestion.loader import load_document
            new_docs.extend(load_document(abs_path))

    new_chunks = chunk_documents(new_docs, chunk_size=chunk_size, overlap=overlap)
    all_chunks = existing_chunks + new_chunks

    # 保存合并后的 chunks 和更新后的 manifest
    save_chunks(chunks_to_dicts(all_chunks), str(CHUNKS_PATH))
    manifest.update(new_files)
    _save_manifest(manifest)

    return all_chunks, "incremental", new_chunks


def build_or_load_vectors(
    chunks: list,
    *,
    force_rebuild: bool = False,
    dim: int = DEFAULT_EMBED_DIM,
    backend: str = DEFAULT_EMBED_BACKEND,
    new_chunks: list | None = None,
) -> tuple[object, str]:
    """
    返回 (vector_store, source)，source 为 'cache' | 'migrated' | 'rebuild' | 'incremental'。

    new_chunks: 增量新增的 chunks（由 build_or_load_chunks 返回）。
    当 new_chunks 非空且 VECTORS_PATH 存在时，只对新 chunks 做 embedding 并追加，不重新处理已有向量。

    迁移策略：若新 .npz 缓存不存在但旧 .json 缓存存在，自动迁移并保存为 .npz。
    """
    if dim <= 0:
        raise ValueError("embed_dim 必须为正整数")

    # ── 增量 embedding ────────────────────────────────────────────────────────
    if not force_rebuild and new_chunks and VECTORS_PATH.exists():
        existing_store = load_vectors(str(VECTORS_PATH))
        new_raw = chunks_to_dicts(new_chunks)
        new_vectors = [
            embed_text(c["text"], dim=existing_store.dim, backend=existing_store.backend)
            for c in new_raw
        ]
        merged = VectorStore(
            dim=existing_store.dim,
            vectors=existing_store.vectors + new_vectors,
            metadata=existing_store.metadata + new_raw,
            backend=existing_store.backend,
        )
        save_vectors(merged, str(VECTORS_PATH))
        return merged, "incremental"

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
    chunks, chunk_src, new_chunks = build_or_load_chunks(
        force_rebuild=force_rebuild,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    # 增量时只对新 chunks 做 embedding；其他情况走原有逻辑
    incremental_new = new_chunks if chunk_src == "incremental" else None
    vector_store, _ = build_or_load_vectors(
        chunks,
        force_rebuild=force_rebuild,
        dim=embed_dim,
        backend=embed_backend,
        new_chunks=incremental_new,
    )
    # FAISS 在增量时也需要重建（追加了新向量后位置变化）
    faiss_force = force_rebuild or chunk_src == "incremental"
    faiss_index, _ = build_or_load_faiss_index(vector_store, force_rebuild=faiss_force)
    return vector_store, faiss_index
