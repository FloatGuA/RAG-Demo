"""
app.py 单元测试
"""

import pytest

from app import answer_with_store, render_response
from embedding import build_vector_store


class TestAppFlow:
    def test_answer_with_store_returns_structured_result(self):
        print("\n[TEST START] App single query returns structured output | App 单次查询返回结构化结果")
        chunks = [
            {"text": "Dynamic programming solves overlapping subproblems.", "source": "l1.pdf", "page": 10},
            {"text": "Greedy chooses local optimum.", "source": "l2.pdf", "page": 8},
        ]
        store = build_vector_store(chunks, dim=64)
        print("[INPUT] query + local provider + vector store | query + 本地 provider + 向量存储")
        print("[ACTION] call answer_with_store | 调用 answer_with_store")
        response = answer_with_store("What is dynamic programming?", store, top_k=2, llm_provider="local")
        print("[EXPECTED] has answer and sources keys | 包含 answer 与 sources 字段")
        assert "answer" in response
        assert "sources" in response
        assert "debug" in response
        assert "generated_at" in response["debug"]
        assert isinstance(response["sources"], list)
        assert response["debug"]["retrieved_chunks"] >= 1
        print("[PASS] structured response ok | 结构化响应正确\n")

    def test_answer_with_store_no_match_returns_idk(self):
        print("\n[TEST START] Empty query path returns IDK | 空查询路径返回 I don't know")
        chunks = [{"text": "Any text", "source": "l1.pdf", "page": 1}]
        store = build_vector_store(chunks, dim=32)
        print("[INPUT] empty query | 空 query")
        print("[ACTION] call answer_with_store | 调用 answer_with_store")
        response = answer_with_store("   ", store, llm_provider="local")
        print("[EXPECTED] answer equals I don't know | answer 为 I don't know")
        assert response["answer"] == "I don't know"
        print("[PASS] grounded fallback ok | grounded 回退正确\n")

    def test_answer_with_store_invalid_top_k_raises(self):
        print("\n[TEST START] Invalid top_k raises in app | app 中非法 top_k 报错")
        chunks = [{"text": "x", "source": "l1.pdf", "page": 1}]
        store = build_vector_store(chunks, dim=16)
        print("[INPUT] top_k=0 | top_k 为 0")
        print("[ACTION] call answer_with_store | 调用 answer_with_store")
        print("[EXPECTED] ValueError | 抛出 ValueError")
        with pytest.raises(ValueError, match="top_k"):
            answer_with_store("hello", store, top_k=0)
        print("[PASS] app top_k validation ok | app top_k 校验正确\n")


class TestAppRender:
    def test_render_response_contains_sources(self):
        print("\n[TEST START] Render output contains source list | 渲染输出包含来源列表")
        response = {
            "answer": "A short answer.",
            "sources": [{"source": "l1.pdf", "page": 3}, {"source": "l2.pdf", "page": 7}],
        }
        print("[INPUT] response dict with two sources | 含两个来源的 response 字典")
        print("[ACTION] call render_response | 调用 render_response")
        text = render_response(response)
        print("[EXPECTED] contains Answer/Sources and source rows | 包含 Answer/Sources 与来源行")
        assert "Answer:" in text
        assert "Sources:" in text
        assert "l1.pdf" in text and "page 3" in text
        print("[PASS] response rendering ok | 响应渲染正确\n")
