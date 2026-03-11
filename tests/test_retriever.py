"""
retriever.py 单元测试
"""

import pytest

from ingestion.embedding import VectorStore, build_faiss_index, build_vector_store, has_faiss
from retrieval.retriever import (
    retrieve_top_k,
    hybrid_retrieve,
    rerank_results,
    has_rank_bm25,
    has_cross_encoder,
    _bm25_retrieve,
    _bm25_cache,
    _get_bm25,
    _rrf_fusion,
)


class TestRetriever:
    def test_retrieve_top_k_basic(self):
        print("\n[TEST START] Basic top-k retrieval works | 基础 Top-k 检索可用")
        chunks = [
            {"text": "apple banana", "source": "a.pdf", "page": 1},
            {"text": "orange pear", "source": "b.pdf", "page": 2},
            {"text": "apple fruit", "source": "c.pdf", "page": 3},
        ]
        store = build_vector_store(chunks, dim=64, backend="hash")
        result = retrieve_top_k("apple", store, top_k=2)
        assert len(result) == 2
        assert {"index", "score", "text", "source", "page"} <= set(result[0].keys())
        assert result[0]["score"] >= result[1]["score"]
        print("[PASS] basic retrieval ok\n")

    def test_retrieve_with_empty_query_returns_empty(self):
        print("\n[TEST START] Empty query returns empty list | 空查询返回空列表")
        store = VectorStore(dim=8, vectors=[[0.0] * 8], metadata=[{"text": "x"}])
        result = retrieve_top_k("   ", store, top_k=3)
        assert result == []
        print("[PASS] empty query handling ok\n")

    def test_retrieve_top_k_non_positive_raises(self):
        print("\n[TEST START] Non-positive top_k raises | 非正 top_k 报错")
        store = VectorStore(dim=8, vectors=[[0.0] * 8], metadata=[{"text": "x"}])
        with pytest.raises(ValueError, match="top_k"):
            retrieve_top_k("hello", store, top_k=0)
        print("[PASS] top_k validation ok\n")

    def test_retrieve_dim_mismatch_raises(self):
        print("\n[TEST START] Dim mismatch raises ValueError | 维度不匹配报错")
        # store.dim=8 but vectors are 8-dim; embed_text with dim=8 will match
        # We manually create a store with wrong dim to trigger mismatch
        store = VectorStore(dim=999, vectors=[[0.0] * 8], metadata=[{"text": "x"}])
        with pytest.raises(ValueError, match="force-rebuild"):
            retrieve_top_k("hello", store, top_k=1)
        print("[PASS] dim mismatch handled ok\n")

    @pytest.mark.skipif(not has_faiss(), reason="需要 faiss 环境")
    def test_retrieve_top_k_with_faiss_index(self):
        print("\n[TEST START] Retrieval with FAISS index | 使用 FAISS 索引检索")
        chunks = [
            {"text": "machine learning", "source": "l1.pdf", "page": 1},
            {"text": "database systems", "source": "l2.pdf", "page": 2},
        ]
        store = build_vector_store(chunks, dim=64, backend="hash")
        index = build_faiss_index(store)
        result = retrieve_top_k("machine", store, top_k=1, faiss_index=index)
        assert len(result) == 1
        assert result[0]["source"] is not None
        print("[PASS] faiss retrieval path ok\n")


class TestBM25:
    def _make_store(self):
        chunks = [
            {"text": "apple banana fruit", "source": "a.pdf", "page": 1},
            {"text": "orange pear citrus", "source": "b.pdf", "page": 2},
            {"text": "machine learning neural", "source": "c.pdf", "page": 3},
        ]
        return build_vector_store(chunks, dim=64, backend="hash")

    @pytest.mark.skipif(not has_rank_bm25(), reason="需要 rank-bm25")
    def test_bm25_retrieve_basic(self):
        print("\n[TEST START] BM25 basic retrieval | BM25 基础检索")
        store = self._make_store()
        results = _bm25_retrieve("apple", store, top_k=2)
        assert len(results) == 2
        assert {"index", "score", "text", "source", "page"} <= set(results[0].keys())
        # apple 在第一个文档里，应该排第一
        assert results[0]["index"] == 0
        print("[PASS] BM25 basic retrieval ok\n")

    @pytest.mark.skipif(not has_rank_bm25(), reason="需要 rank-bm25")
    def test_bm25_retrieve_returns_top_k(self):
        print("\n[TEST START] BM25 returns exactly top_k | BM25 返回 top_k 条")
        store = self._make_store()
        results = _bm25_retrieve("fruit", store, top_k=1)
        assert len(results) == 1
        print("[PASS] BM25 top_k limit ok\n")

    @pytest.mark.skipif(not has_rank_bm25(), reason="需要 rank-bm25")
    def test_bm25_cache_reuses_same_object(self):
        print("\n[TEST START] BM25 cache returns same object for same store | BM25 缓存同一 store 返回同一对象")
        store = self._make_store()
        bm25_a = _get_bm25(store)
        bm25_b = _get_bm25(store)
        assert bm25_a is bm25_b
        print("[PASS] BM25 cache identity ok\n")

    @pytest.mark.skipif(not has_rank_bm25(), reason="需要 rank-bm25")
    def test_bm25_cache_different_store_different_object(self):
        print("\n[TEST START] Different stores get different BM25 objects | 不同 store 得到不同 BM25 对象")
        store_a = self._make_store()
        store_b = self._make_store()
        bm25_a = _get_bm25(store_a)
        bm25_b = _get_bm25(store_b)
        assert bm25_a is not bm25_b
        print("[PASS] BM25 cache isolation ok\n")


class TestRRFFusion:
    def test_rrf_fusion_combines_results(self):
        print("\n[TEST START] RRF fusion combines two lists | RRF 融合两路结果")
        dense = [
            {"index": 0, "score": 0.9, "text": "a", "source": None, "page": None},
            {"index": 1, "score": 0.5, "text": "b", "source": None, "page": None},
        ]
        sparse = [
            {"index": 1, "score": 5.0, "text": "b", "source": None, "page": None},
            {"index": 2, "score": 3.0, "text": "c", "source": None, "page": None},
        ]
        fused = _rrf_fusion(dense, sparse)
        indices = [r["index"] for r in fused]
        # index 1 出现在两路结果中，RRF 分数应该最高
        assert indices[0] == 1
        assert len(fused) == 3
        print("[PASS] RRF fusion ok\n")

    def test_rrf_fusion_scores_are_float(self):
        print("\n[TEST START] RRF scores are floats | RRF 分数为浮点数")
        dense = [{"index": 0, "score": 0.8, "text": "x", "source": None, "page": None}]
        sparse = [{"index": 0, "score": 1.0, "text": "x", "source": None, "page": None}]
        fused = _rrf_fusion(dense, sparse)
        assert isinstance(fused[0]["score"], float)
        print("[PASS] RRF score type ok\n")


class TestHybridRetrieve:
    def _make_store(self):
        chunks = [
            {"text": "apple banana fruit", "source": "a.pdf", "page": 1},
            {"text": "orange pear citrus", "source": "b.pdf", "page": 2},
            {"text": "machine learning model", "source": "c.pdf", "page": 3},
        ]
        return build_vector_store(chunks, dim=64, backend="hash")

    def test_hybrid_retrieve_dense_only_fallback(self):
        print("\n[TEST START] hybrid_retrieve falls back to dense when bm25=False | use_bm25=False 回退纯向量")
        store = self._make_store()
        result = hybrid_retrieve("apple", store, top_k=2, use_bm25=False, use_rerank=False)
        assert len(result) == 2
        assert {"index", "score", "text"} <= set(result[0].keys())
        print("[PASS] hybrid dense-only fallback ok\n")

    @pytest.mark.skipif(not has_rank_bm25(), reason="需要 rank-bm25")
    def test_hybrid_retrieve_with_bm25(self):
        print("\n[TEST START] hybrid_retrieve with BM25 | 启用 BM25 混合检索")
        store = self._make_store()
        result = hybrid_retrieve("apple", store, top_k=2, use_bm25=True, use_rerank=False)
        assert len(result) == 2
        assert result[0]["score"] >= result[1]["score"]
        print("[PASS] hybrid BM25 path ok\n")

    def test_hybrid_retrieve_empty_query(self):
        print("\n[TEST START] hybrid_retrieve returns [] on empty query | 空查询返回空")
        store = self._make_store()
        result = hybrid_retrieve("  ", store, top_k=3)
        assert result == []
        print("[PASS] hybrid empty query ok\n")

    def test_hybrid_retrieve_respects_top_k(self):
        print("\n[TEST START] hybrid_retrieve respects top_k limit | 结果数量 ≤ top_k")
        store = self._make_store()
        result = hybrid_retrieve("fruit", store, top_k=1, use_bm25=False)
        assert len(result) == 1
        print("[PASS] hybrid top_k limit ok\n")
