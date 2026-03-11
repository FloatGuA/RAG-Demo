"""
模块4：Retriever
根据 query 从向量存储中检索 Top-k 相关 chunks。
支持：
  - 纯向量检索（Dense）
  - Hybrid 检索（Dense + BM25，RRF 融合）
  - Cross-Encoder Reranking
"""

from __future__ import annotations

import numpy as np

from ingestion.embedding import VectorStore, embed_text, has_faiss, search_faiss


# ── 可用性检测 ──────────────────────────────────────────────────────────────

def has_rank_bm25() -> bool:
    """检测 rank-bm25 是否可用。"""
    try:
        import rank_bm25  # noqa: F401
        return True
    except ImportError:
        return False


def has_cross_encoder() -> bool:
    """检测 sentence-transformers CrossEncoder 是否可用。"""
    try:
        from sentence_transformers import CrossEncoder  # noqa: F401
        return True
    except ImportError:
        return False


# ── BM25 索引缓存 ──────────────────────────────────────────────────────────

_bm25_cache: dict[int, object] = {}  # id(store) → BM25Okapi instance


def _get_bm25(store: VectorStore) -> object:
    """按 vector store 实例缓存 BM25 索引，同一进程内只构建一次。"""
    store_id = id(store)
    if store_id not in _bm25_cache:
        from rank_bm25 import BM25Okapi
        corpus = [meta.get("text", "").lower().split() for meta in store.metadata]
        _bm25_cache[store_id] = BM25Okapi(corpus)
    return _bm25_cache[store_id]


# ── Cross-Encoder 模型缓存 ──────────────────────────────────────────────────

_ce_cache: dict[str, object] = {}


def _get_cross_encoder(model_name: str) -> object:
    if model_name not in _ce_cache:
        from sentence_transformers import CrossEncoder
        _ce_cache[model_name] = CrossEncoder(model_name)
    return _ce_cache[model_name]


# ── Dense 检索 ─────────────────────────────────────────────────────────────

def retrieve_top_k(
    query: str,
    store: VectorStore,
    *,
    top_k: int = 5,
    faiss_index: object | None = None,
) -> list[dict]:
    """
    纯向量检索，返回 top_k 条最相关 chunk。

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


# ── BM25 稀疏检索 ──────────────────────────────────────────────────────────

def _bm25_retrieve(query: str, store: VectorStore, top_k: int) -> list[dict]:
    """BM25 关键词检索，返回 top_k 候选（索引缓存，同一进程内只构建一次）。"""
    bm25 = _get_bm25(store)
    scores = bm25.get_scores(query.lower().split())

    top_indices = np.argsort(scores)[::-1][:top_k]
    results: list[dict] = []
    for idx in top_indices:
        meta = store.metadata[idx] if idx < len(store.metadata) else {}
        results.append(
            {
                "index": int(idx),
                "score": float(scores[idx]),
                "text": meta.get("text", ""),
                "source": meta.get("source"),
                "page": meta.get("page"),
            }
        )
    return results


# ── RRF 融合 ───────────────────────────────────────────────────────────────

def _rrf_fusion(
    dense_results: list[dict],
    sparse_results: list[dict],
    *,
    rrf_k: int = 60,
) -> list[dict]:
    """
    Reciprocal Rank Fusion：将两路检索结果合并。
    score = Σ 1 / (rrf_k + rank + 1)
    """
    fused: dict[int, float] = {}
    index_to_item: dict[int, dict] = {}

    for rank, item in enumerate(dense_results):
        idx = item["index"]
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        index_to_item[idx] = item

    for rank, item in enumerate(sparse_results):
        idx = item["index"]
        fused[idx] = fused.get(idx, 0.0) + 1.0 / (rrf_k + rank + 1)
        if idx not in index_to_item:
            index_to_item[idx] = item

    sorted_indices = sorted(fused, key=lambda i: fused[i], reverse=True)
    results: list[dict] = []
    for idx in sorted_indices:
        item = dict(index_to_item[idx])
        item["score"] = fused[idx]
        results.append(item)
    return results


# ── Cross-Encoder Reranking ─────────────────────────────────────────────────

def rerank_results(
    query: str,
    candidates: list[dict],
    top_n: int,
    *,
    model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> list[dict]:
    """
    用 Cross-Encoder 对候选列表重新打分并取 top_n。
    每个 item 会增加 "rerank_score" 字段。
    """
    ce = _get_cross_encoder(model_name)
    pairs = [(query, c["text"]) for c in candidates]
    scores = ce.predict(pairs)  # type: ignore[attr-defined]
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    results: list[dict] = []
    for score, item in ranked[:top_n]:
        item = dict(item)
        item["rerank_score"] = float(score)
        results.append(item)
    return results


# ── Hybrid 入口 ────────────────────────────────────────────────────────────

def hybrid_retrieve(
    query: str,
    store: VectorStore,
    *,
    top_k: int = 5,
    faiss_index: object | None = None,
    use_bm25: bool = True,
    use_rerank: bool = False,
    rerank_initial_k: int = 20,
    rerank_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
) -> list[dict]:
    """
    混合检索主入口。

    流程：
      1. Dense 向量检索（top rerank_initial_k 或 top_k）
      2. [可选] BM25 检索 + RRF 融合
      3. [可选] Cross-Encoder 重排，取 top_k
      4. 返回最终 top_k 结果

    若所需依赖不可用（rank-bm25 / CrossEncoder），对应步骤优雅跳过。
    """
    if not query.strip():
        return []
    if not store.vectors:
        return []

    fetch_k = min(rerank_initial_k if use_rerank else top_k, len(store.vectors))

    # Step 1: Dense
    dense = retrieve_top_k(query, store, top_k=fetch_k, faiss_index=faiss_index)

    # Step 2: BM25 + RRF
    if use_bm25 and has_rank_bm25():
        sparse = _bm25_retrieve(query, store, top_k=fetch_k)
        candidates = _rrf_fusion(dense, sparse)[:fetch_k]
    else:
        candidates = dense

    # Step 3: Cross-Encoder rerank
    if use_rerank and has_cross_encoder():
        candidates = rerank_results(query, candidates, top_n=top_k, model_name=rerank_model)
    else:
        candidates = candidates[:top_k]

    return candidates
