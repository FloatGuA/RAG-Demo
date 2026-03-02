"""
prompt.py 单元测试
"""

import pytest

from prompt import build_prompt


class TestPromptBuilder:
    def test_build_prompt_contains_query_and_context(self):
        print("\n[TEST START] Prompt includes query/context | Prompt 包含 query 与上下文")
        contexts = [{"text": "Sorting has O(n log n) average complexity.", "source": "L3.pdf", "page": 12}]
        print("[INPUT] one query + one context | 一个 query + 一个 context")
        print("[ACTION] call build_prompt | 调用 build_prompt")
        prompt = build_prompt("What is sorting complexity?", contexts)
        print("[EXPECTED] prompt has question/source/page/text | prompt 含问题与来源信息")
        assert "What is sorting complexity?" in prompt
        assert "L3.pdf" in prompt
        assert "page=12" in prompt
        assert "Sorting has O(n log n)" in prompt
        print("[PASS] prompt content assembled correctly | prompt 内容拼装正确\n")

    def test_build_prompt_without_context(self):
        print("\n[TEST START] Prompt handles empty contexts | Prompt 处理空上下文")
        print("[INPUT] query + empty contexts | query + 空 contexts")
        print("[ACTION] call build_prompt | 调用 build_prompt")
        prompt = build_prompt("Unknown question", [])
        print("[EXPECTED] contains no-context marker and grounded rule | 含无上下文标记与 grounded 约束")
        assert "[No context retrieved]" in prompt
        assert "I don't know" in prompt
        print("[PASS] empty context prompt behavior ok | 空上下文 prompt 行为正确\n")

    def test_build_prompt_non_positive_max_context_chars_raises(self):
        print("\n[TEST START] Invalid max_context_chars raises | 非法 max_context_chars 报错")
        print("[INPUT] max_context_chars=0 | max_context_chars 为 0")
        print("[ACTION] call build_prompt | 调用 build_prompt")
        print("[EXPECTED] ValueError | 抛出 ValueError")
        with pytest.raises(ValueError, match="max_context_chars"):
            build_prompt("q", [{"text": "x"}], max_context_chars=0)
        print("[PASS] max_context_chars validation ok | max_context_chars 校验正确\n")
