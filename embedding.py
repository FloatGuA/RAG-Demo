"""
模块3：Embedding & Vector Store
将 Chunk 文本映射为向量，并提供向量存储持久化能力。
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import zlib
import importlib.util

import numpy as np


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")

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


def has_faiss() -> bool:
    """当前环境是否可用 FAISS。"""
    return importlib.util.find_spec("faiss") is not None and faiss is not None


def _require_faiss() -> None:
    if faiss is None:
        raise RuntimeError(
            "当前环境未安装或无法加载 faiss。请安装 faiss-cpu 后再使用索引功能。"
        ) from _FAISS_IMPORT_ERROR


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = sum(v * v for v in vec) ** 0.5
    if norm == 0:
        return vec
    return [v / norm for v in vec]


def embed_text(text: str, dim: int = 256) -> list[float]:
    """
    将文本编码为固定维度向量（哈希 BoW，轻量可复现）。
    """
    if dim <= 0:
        raise ValueError("dim 必须为正整数")

    vec = [0.0] * dim
    for token in _tokenize(text):
        idx = zlib.crc32(token.encode("utf-8")) % dim
        vec[idx] += 1.0
    return _l2_normalize(vec)


def build_vector_store(chunks: list[dict], dim: int = 256) -> VectorStore:
    """
    将 chunks 构建为 VectorStore。

    约定 chunks 中至少包含 text/source/page 字段。
    """
    vectors: list[list[float]] = []
    metadata: list[dict] = []
    for chunk in chunks:
        text = chunk.get("text", "")
        vectors.append(embed_text(text, dim=dim))
        metadata.append(
            {
                "text": text,
                "source": chunk.get("source"),
                "page": chunk.get("page"),
            }
        )
    return VectorStore(dim=dim, vectors=vectors, metadata=metadata)


def save_vectors(store: VectorStore, path: str) -> None:
    """保存向量存储为 JSON（可读优先）。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "dim": store.dim,
        "vectors": store.vectors,
        "metadata": store.metadata,
    }
    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_vectors(path: str) -> VectorStore:
    """加载向量存储，恢复 VectorStore。"""
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"vectors 文件不存在: {target}")
    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("vectors 文件格式错误：根对象应为 dict")
    return VectorStore(
        dim=int(data["dim"]),
        vectors=list(data["vectors"]),
        metadata=list(data["metadata"]),
    )


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
