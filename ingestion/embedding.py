"""
模块3：Embedding & Vector Store
将 Chunk 文本映射为向量，并提供向量存储持久化能力。

Embedding 后端（backend 参数）：
  "auto"                 — 优先使用 sentence-transformers，不可用时降级 hash
  "sentence_transformers"— 语义嵌入（all-MiniLM-L6-v2，384 dim），需安装依赖
  "hash"                 — 哈希 BoW（轻量，离线可用，dim 参数有效）
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import re
import zlib

import numpy as np


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

# sentence-transformers 模块级模型缓存（避免重复加载）
_st_model_cache: dict[str, object] = {}
_ST_DEFAULT_MODEL = "all-MiniLM-L6-v2"

try:
    import faiss  # type: ignore
except Exception as exc:  # pragma: no cover - 依赖可能不存在
    faiss = None  # type: ignore
    _FAISS_IMPORT_ERROR = exc
else:
    _FAISS_IMPORT_ERROR = None


@dataclass
class VectorStore:
    """轻量向量存储结构。"""

    dim: int
    vectors: list[list[float]]
    metadata: list[dict]
    backend: str = "hash"  # 建索引时使用的 embedding 后端，检索时需保持一致


def has_faiss() -> bool:
    """当前环境是否可用 FAISS。"""
    return importlib.util.find_spec("faiss") is not None and faiss is not None


def has_sentence_transformers() -> bool:
    """当前环境是否可用 sentence-transformers。"""
    return importlib.util.find_spec("sentence_transformers") is not None


def _require_faiss() -> None:
    if faiss is None:
        raise RuntimeError(
            "当前环境未安装或无法加载 faiss。请安装 faiss-cpu 后再使用索引功能。"
        ) from _FAISS_IMPORT_ERROR


def _get_st_model(model_name: str = _ST_DEFAULT_MODEL):
    """懒加载并缓存 sentence-transformers 模型。"""
    if model_name not in _st_model_cache:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _st_model_cache[model_name] = SentenceTransformer(model_name)
    return _st_model_cache[model_name]


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _l2_normalize_hash(arr: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(arr)
    if norm == 0:
        return arr
    return arr / norm


def embed_text(text: str, dim: int = 256, *, backend: str = "auto") -> list[float]:
    """
    将文本编码为向量。

    Args:
        text:    输入文本
        dim:     hash 后端的向量维度（sentence-transformers 后端忽略此参数）
        backend: "auto" | "sentence_transformers" | "hash"

    Returns:
        L2 归一化后的向量（list[float]）
    """
    resolved = backend
    if resolved == "auto":
        resolved = "sentence_transformers" if has_sentence_transformers() else "hash"

    if resolved == "sentence_transformers":
        model = _get_st_model()
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()

    # hash BoW 后端
    if dim <= 0:
        raise ValueError("dim 必须为正整数")
    arr = np.zeros(dim, dtype=np.float64)
    for token in _tokenize(text):
        idx = zlib.crc32(token.encode("utf-8")) % dim
        arr[idx] += 1.0
    return _l2_normalize_hash(arr).tolist()


def build_vector_store(chunks: list[dict], dim: int = 256, *, backend: str = "auto") -> VectorStore:
    """
    将 chunks 构建为 VectorStore。

    约定 chunks 中至少包含 text/source/page 字段。
    实际 dim 由首个向量长度决定（sentence-transformers 后端会覆盖 dim 参数）。
    """
    vectors: list[list[float]] = []
    metadata: list[dict] = []
    actual_dim = dim
    for chunk in chunks:
        text = chunk.get("text", "")
        vec = embed_text(text, dim=dim, backend=backend)
        if not vectors:
            actual_dim = len(vec)
        vectors.append(vec)
        metadata.append(
            {
                "text": text,
                "source": chunk.get("source"),
                "page": chunk.get("page"),
            }
        )
    # Resolve the actual backend used (for retrieval consistency)
    resolved_backend = backend
    if resolved_backend == "auto":
        resolved_backend = "sentence_transformers" if has_sentence_transformers() else "hash"
    return VectorStore(dim=actual_dim, vectors=vectors, metadata=metadata, backend=resolved_backend)


def save_vectors(store: VectorStore, path: str) -> None:
    """
    保存向量存储为 npz 压缩格式。

    文件布局（单个 .npz）：
      vectors      — float32 矩阵 (n, dim)
      metadata_json — 单元素字符串数组，存 JSON 序列化的 metadata list
      dim          — 单元素 int64 数组
      backend      — 单元素字符串数组
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    arr = np.array(store.vectors, dtype=np.float32) if store.vectors else np.empty((0, store.dim), dtype=np.float32)
    meta_json = json.dumps(store.metadata, ensure_ascii=False)
    # np.savez_compressed appends .npz when the path has no .npz suffix;
    # strip it first so the file lands exactly at `target`.
    save_stem = str(target.with_suffix("")) if target.suffix == ".npz" else str(target)
    np.savez_compressed(
        save_stem,
        vectors=arr,
        metadata_json=np.array([meta_json]),
        dim=np.array([store.dim]),
        backend=np.array([store.backend]),
    )


def load_vectors(path: str) -> VectorStore:
    """
    加载向量存储，恢复 VectorStore。

    支持两种格式（按文件后缀自动检测）：
      .npz  — 当前默认格式（numpy 压缩）
      .json — 旧格式，向后兼容
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"vectors 文件不存在: {target}")

    if target.suffix.lower() == ".json":
        # 旧 JSON 格式（向后兼容）
        with target.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("vectors 文件格式错误：根对象应为 dict")
        return VectorStore(
            dim=int(data["dim"]),
            vectors=list(data["vectors"]),
            metadata=list(data["metadata"]),
            backend=str(data.get("backend", "hash")),
        )

    # npz 格式
    raw = np.load(str(target), allow_pickle=False)
    vectors: list[list[float]] = raw["vectors"].tolist()
    metadata: list[dict] = json.loads(str(raw["metadata_json"][0]))
    dim = int(raw["dim"][0])
    backend = str(raw["backend"][0])
    return VectorStore(dim=dim, vectors=vectors, metadata=metadata, backend=backend)


def build_faiss_index(store: VectorStore):
    """
    基于 VectorStore 构建 FAISS IndexFlatIP。
    """
    _require_faiss()
    index = faiss.IndexFlatIP(store.dim)  # type: ignore[attr-defined]
    if store.vectors:
        arr = np.array(store.vectors, dtype="float32")
        index.add(arr)
    return index


def search_faiss(index, query_vector: list[float], top_k: int = 5) -> list[tuple[int, float]]:
    """
    在 FAISS 索引中检索 top_k，返回 (idx, score)。
    """
    _require_faiss()
    if top_k <= 0:
        raise ValueError("top_k 必须为正整数")
    query = np.array([query_vector], dtype="float32")
    scores, indices = index.search(query, top_k)
    result: list[tuple[int, float]] = []
    for idx, score in zip(indices[0].tolist(), scores[0].tolist()):
        if idx >= 0:
            result.append((int(idx), float(score)))
    return result


def save_faiss_index(index, path: str) -> None:
    """持久化 FAISS 索引到文件。"""
    _require_faiss()
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(target))  # type: ignore[attr-defined]


def load_faiss_index(path: str):
    """从文件加载 FAISS 索引。"""
    _require_faiss()
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"faiss index 文件不存在: {target}")
    return faiss.read_index(str(target))  # type: ignore[attr-defined]
