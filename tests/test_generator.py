"""
generator.py 与 formatter.py 单元测试
"""

import pytest

from formatter import format_response
from generator import generate_answer


class TestGenerator:
    def test_generate_answer_without_context_returns_idk(self):
        print("\n[TEST START] No context returns I don't know | 无上下文返回 I don't know")
        print("[INPUT] prompt + empty contexts | prompt + 空 contexts")
        print("[ACTION] call generate_answer | 调用 generate_answer")
        answer = generate_answer("dummy prompt", contexts=[])
        print("[EXPECTED] exact I don't know | 精确返回 I don't know")
        assert answer == "I don't know"
        print("[PASS] no-context fallback ok | 无上下文回退正确\n")

    def test_generate_answer_from_first_context_sentence(self):
        print("\n[TEST START] Generate from first context sentence | 从首条上下文首句生成")
        contexts = [{"text": "AVL tree keeps balance. It supports log-time operations."}]
        print("[INPUT] prompt + one context text | prompt + 一条上下文文本")
        print("[ACTION] call generate_answer | 调用 generate_answer")
        answer = generate_answer("dummy prompt", contexts=contexts)
        print("[EXPECTED] answer equals first sentence | 返回首句内容")
        assert answer == "AVL tree keeps balance."
        print("[PASS] first-sentence generation ok | 首句生成正确\n")

    def test_openai_provider_without_key_falls_back_to_local(self, monkeypatch):
        print("\n[TEST START] OpenAI no-key fallback to local | OpenAI 无 key 回退本地")
        contexts = [{"text": "Greedy picks local optimum. It may fail globally."}]
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        print("[INPUT] provider=openai, no key, fallback enabled | provider=openai 且无 key，启用回退")
        print("[ACTION] call generate_answer | 调用 generate_answer")
        answer = generate_answer(
            "dummy prompt",
            contexts=contexts,
            provider="openai",
            fallback_to_local=True,
        )
        print("[EXPECTED] return local fallback sentence | 返回本地回退首句")
        assert answer == "Greedy picks local optimum."
        print("[PASS] missing-key fallback behavior ok | 缺 key 回退行为正确\n")

    def test_invalid_provider_raises(self):
        print("\n[TEST START] Invalid provider raises error | 非法 provider 报错")
        contexts = [{"text": "x"}]
        print("[INPUT] provider='bad_provider' | 非法 provider")
        print("[ACTION] call generate_answer | 调用 generate_answer")
        print("[EXPECTED] ValueError | 抛出 ValueError")
        with pytest.raises(ValueError, match="provider"):
            generate_answer("dummy prompt", contexts=contexts, provider="bad_provider")
        print("[PASS] invalid provider validation ok | provider 校验正确\n")


class TestFormatter:
    def test_format_response_with_deduplicated_sources(self):
        print("\n[TEST START] Format response deduplicates sources | 输出格式会去重来源")
        contexts = [
            {"source": "L1.pdf", "page": 3, "text": "A"},
            {"source": "L1.pdf", "page": 3, "text": "B"},
            {"source": "L2.pdf", "page": 7, "text": "C"},
        ]
        print("[INPUT] answer + duplicated source contexts | answer + 含重复来源的 contexts")
        print("[ACTION] call format_response | 调用 format_response")
        response = format_response("ok", contexts)
        print("[EXPECTED] answer kept and sources deduplicated | 保留答案且来源去重")
        assert response["answer"] == "ok"
        assert len(response["sources"]) == 2
        print("[PASS] response format ok | 响应格式正确\n")
