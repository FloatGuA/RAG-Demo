"""
retriever.py 单元测试
"""

import pytest

from ingestion.embedding import VectorStore, build_faiss_index, build_vector_store, has_faiss
from retrieval.retriever import retrieve_top_k


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
