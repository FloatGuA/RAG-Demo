"""
generator.py 与 formatter.py 单元测试
"""

import pytest

from retrieval.formatter import format_response
from retrieval.generator import _build_messages, generate_answer, generate_answer_stream


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


class TestBuildMessages:
    def test_build_messages_no_history(self):
        print("\n[TEST START] build_messages without history | 无历史时构建消息")
        msgs = _build_messages("hello", None)
        assert msgs[0]["role"] == "system"
        assert msgs[-1] == {"role": "user", "content": "hello"}
        assert len(msgs) == 2
        print("[PASS] no-history message structure ok\n")

    def test_build_messages_with_history(self):
        print("\n[TEST START] build_messages inserts history between system and user | 历史插入正确位置")
        history = [
            {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"},
        ]
        msgs = _build_messages("q2", history)
        assert msgs[0]["role"] == "system"
        assert msgs[1] == {"role": "user", "content": "q1"}
        assert msgs[2] == {"role": "assistant", "content": "a1"}
        assert msgs[3] == {"role": "user", "content": "q2"}
        print("[PASS] history insertion order ok\n")


class TestGenerateAnswerStream:
    def test_stream_no_context_yields_idk(self):
        print("\n[TEST START] stream with no context yields I don't know | 无上下文流式返回 IDK")
        chunks = list(generate_answer_stream("test", contexts=[], provider="local"))
        assert chunks == ["I don't know"]
        print("[PASS] no-context stream ok\n")

    def test_stream_local_yields_single_chunk(self):
        print("\n[TEST START] stream local provider yields single chunk | local 流式单次 yield")
        contexts = [{"text": "FAISS is fast. It handles billions of vectors."}]
        chunks = list(generate_answer_stream("test", contexts=contexts, provider="local"))
        assert len(chunks) == 1
        assert "FAISS" in chunks[0]
        print("[PASS] local stream single-chunk ok\n")

    def test_stream_accepts_chat_history(self):
        print("\n[TEST START] stream accepts chat_history without error | 流式接受 chat_history 不报错")
        history = [{"role": "user", "content": "prev"}, {"role": "assistant", "content": "prev_ans"}]
        contexts = [{"text": "A sentence about caching."}]
        chunks = list(generate_answer_stream("test", contexts=contexts, provider="local", chat_history=history))
        assert isinstance(chunks, list) and len(chunks) >= 1
        print("[PASS] chat_history accepted ok\n")


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
