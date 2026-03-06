"""
模块4：Retriever
根据 query 从向量存储中检索 Top-k 相关 chunks。
"""

from __future__ import annotations

import numpy as np

from ingestion.embedding import VectorStore, embed_text, has_faiss, search_faiss


def retrieve_top_k(
    query: str,
    store: VectorStore,
    *,
    top_k: int = 5,
    faiss_index: object | None = None,
) -> list[dict]:
    """
    检索与 query 最相关的 top_k 条 chunk。

    返回元素格式：
    {
        "index": int,
        "score": float,
        "text": str,
        "source": str | None,
        "page": int | None
    }
    """
    if top_k <= 0:
        raise ValueError("top_k 必须为正整数")
    if not query.strip():
        return []
    if not store.vectors:
        return []

    qvec = embed_text(query, dim=store.dim, backend=store.backend)

    actual_stored_dim = len(store.vectors[0]) if store.vectors else store.dim
    if len(qvec) != actual_stored_dim:
        raise ValueError(
            f"Query vector dim {len(qvec)} != stored vector dim {actual_stored_dim}. "
            "Please run --force-rebuild after switching embedding backend."
        )

    if faiss_index is not None and has_faiss():
        ranked = search_faiss(
            faiss_index,
            qvec,
            top_k=min(top_k, len(store.vectors)),
        )
    else:
        mat = np.array(store.vectors, dtype=np.float32)   # (n, dim)
        q = np.array(qvec, dtype=np.float32)               # (dim,)
        scores = mat @ q                                    # (n,)
        top_indices = np.argsort(scores)[::-1][:top_k]
        ranked = [(int(i), float(scores[i])) for i in top_indices]

    results: list[dict] = []
    for idx, score in ranked:
        meta = store.metadata[idx] if idx < len(store.metadata) else {}
        results.append(
            {
                "index": int(idx),
                "score": float(score),
                "text": meta.get("text", ""),
                "source": meta.get("source"),
                "page": meta.get("page"),
            }
        )
    return results
