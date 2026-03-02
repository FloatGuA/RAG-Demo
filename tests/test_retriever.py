"""
retriever.py 单元测试
"""

import pytest

from embedding import VectorStore, build_faiss_index, build_vector_store, has_faiss
from retriever import retrieve_top_k


class TestRetriever:
    def test_retrieve_top_k_basic(self):
        print("\n[TEST START] Basic top-k retrieval works | 基础 Top-k 检索可用")
        chunks = [
            {"text": "apple banana", "source": "a.pdf", "page": 1},
            {"text": "orange pear", "source": "b.pdf", "page": 2},
            {"text": "apple fruit", "source": "c.pdf", "page": 3},
        ]
        store = build_vector_store(chunks, dim=64)
        print("[INPUT] query='apple', top_k=2 | 查询 apple，返回前 2 条")
        print("[ACTION] call retrieve_top_k | 调用 retrieve_top_k")
        result = retrieve_top_k("apple", store, top_k=2)
        print("[EXPECTED] length=2 and has required keys | 长度为 2 且字段完整")
        assert len(result) == 2
        assert {"index", "score", "text", "source", "page"} <= set(result[0].keys())
        assert result[0]["score"] >= result[1]["score"]
        print("[PASS] basic retrieval ok | 基础检索正确\n")

    def test_retrieve_with_empty_query_returns_empty(self):
        print("\n[TEST START] Empty query returns empty list | 空查询返回空列表")
        store = VectorStore(dim=8, vectors=[[0.0] * 8], metadata=[{"text": "x"}])
        print("[INPUT] empty query string | 空字符串 query")
        print("[ACTION] call retrieve_top_k | 调用 retrieve_top_k")
        result = retrieve_top_k("   ", store, top_k=3)
        print("[EXPECTED] empty list | 返回空列表")
        assert result == []
        print("[PASS] empty query handling ok | 空查询处理正确\n")

    def test_retrieve_top_k_non_positive_raises(self):
        print("\n[TEST START] Non-positive top_k raises | 非正 top_k 报错")
        store = VectorStore(dim=8, vectors=[[0.0] * 8], metadata=[{"text": "x"}])
        print("[INPUT] top_k=0 | top_k 为 0")
        print("[ACTION] call retrieve_top_k | 调用 retrieve_top_k")
        print("[EXPECTED] ValueError | 抛出 ValueError")
        with pytest.raises(ValueError, match="top_k"):
            retrieve_top_k("hello", store, top_k=0)
        print("[PASS] top_k validation ok | top_k 参数校验正确\n")

    @pytest.mark.skipif(not has_faiss(), reason="需要 faiss 环境")
    def test_retrieve_top_k_with_faiss_index(self):
        print("\n[TEST START] Retrieval with FAISS index | 使用 FAISS 索引检索")
        chunks = [
            {"text": "machine learning", "source": "l1.pdf", "page": 1},
            {"text": "database systems", "source": "l2.pdf", "page": 2},
        ]
        store = build_vector_store(chunks, dim=64)
        index = build_faiss_index(store)
        print("[INPUT] query='machine', with faiss index | query=machine，提供 faiss 索引")
        print("[ACTION] call retrieve_top_k with faiss_index | 带 faiss_index 调用")
        result = retrieve_top_k("machine", store, top_k=1, faiss_index=index)
        print("[EXPECTED] at least one result | 至少返回一条结果")
        assert len(result) == 1
        assert result[0]["source"] is not None
        print("[PASS] faiss retrieval path ok | faiss 检索路径正确\n")
