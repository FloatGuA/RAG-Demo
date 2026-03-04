"""
web_app.py 单元测试（不依赖 streamlit 运行时）
"""

from pathlib import Path

from config.env import load_env_defaults
from web_app import (
    build_assistant_message,
    format_sources_lines,
    format_debug_lines,
    get_default_base_url,
    get_default_timeout,
    get_models_for_provider,
    get_provider_options,
    load_llm_presets,
    now_timestamp,
)


class TestWebAppHelpers:
    def test_format_sources_lines_with_items(self):
        print("\n[TEST START] Format sources lines with data | 有来源数据时格式化来源文本")
        sources = [{"source": "L1.pdf", "page": 2}, {"source": "L2.pdf", "page": 9}]
        print("[INPUT] two source items | 两条来源")
        print("[ACTION] call format_sources_lines | 调用 format_sources_lines")
        lines = format_sources_lines(sources)
        print("[EXPECTED] two formatted bullet lines | 返回两条格式化来源文本")
        assert len(lines) == 2
        assert "L1.pdf" in lines[0] and "page 2" in lines[0]
        print("[PASS] source line formatting ok | 来源文本格式化正确\n")

    def test_format_sources_lines_without_items(self):
        print("\n[TEST START] Format sources lines when empty | 来源为空时格式化")
        print("[INPUT] empty list | 空列表")
        print("[ACTION] call format_sources_lines | 调用 format_sources_lines")
        lines = format_sources_lines([])
        print("[EXPECTED] fallback '- (none)' | 返回 '- (none)'")
        assert lines == ["- (none)"]
        print("[PASS] empty source fallback ok | 空来源回退正确\n")

    def test_build_assistant_message_contains_answer_and_sources(self):
        print("\n[TEST START] Assistant message includes answer/sources | 助手消息包含答案与来源")
        answer = "Dynamic programming is a method."
        sources = [{"source": "L3.pdf", "page": 5}]
        print("[INPUT] answer text + one source | 一条答案和一条来源")
        print("[ACTION] call build_assistant_message | 调用 build_assistant_message")
        text = build_assistant_message(answer, sources)
        print("[EXPECTED] contains answer, Sources label, and source line | 包含答案、Sources 标题和来源行")
        assert "Dynamic programming is a method." in text
        assert "Sources:" in text
        assert "L3.pdf" in text
        print("[PASS] assistant message composition ok | 助手消息组装正确\n")

    def test_load_env_file_reads_key_values(self, tmp_path):
        print("\n[TEST START] Load env file key-values | 读取 env 键值")
        env_path = tmp_path / ".env"
        env_path.write_text("LLM_PROVIDER=openai_compatible\nLLM_MODEL=qwen3.5-plus\n", encoding="utf-8")
        print("[INPUT] temp .env with provider/model | 包含 provider/model 的临时 .env")
        print("[ACTION] call load_env_defaults | 调用 load_env_defaults")
        data = load_env_defaults(str(env_path))
        print("[EXPECTED] dict contains parsed values | 字典包含解析后的值")
        assert data["LLM_PROVIDER"] == "openai_compatible"
        assert data["LLM_MODEL"] == "qwen3.5-plus"
        print("[PASS] env parsing ok | env 解析正确\n")

    def test_load_llm_presets_fallback_when_missing(self, tmp_path):
        print("\n[TEST START] Missing preset file falls back | 预置文件缺失时回退默认")
        missing = tmp_path / "not_exists.json"
        print("[INPUT] non-existing presets path | 不存在的预置文件路径")
        print("[ACTION] call load_llm_presets | 调用 load_llm_presets")
        presets = load_llm_presets(str(missing))
        print("[EXPECTED] has default providers | 返回默认 provider 配置")
        options = get_provider_options(presets)
        assert "openai_compatible" in options
        assert "local" in options
        print("[PASS] preset fallback ok | 预置回退正确\n")

    def test_provider_model_base_url_mapping(self):
        print("\n[TEST START] Provider maps to model/base_url | Provider 映射模型与地址")
        print("[INPUT] default preset config | 默认预置配置")
        print("[ACTION] load presets and resolve mapping | 读取预置并解析映射")
        repo_root = Path(__file__).resolve().parents[1]
        presets = load_llm_presets(str(repo_root / "llm_presets.json"))
        models = get_models_for_provider(presets, "openai_compatible")
        base_url = get_default_base_url(presets, "openai_compatible")
        print("[EXPECTED] qwen3.5-plus and qwen-plus in models | 模型含 qwen3.5-plus 与 qwen-plus")
        assert "qwen3.5-plus" in models
        assert "qwen-plus" in models
        assert "dashscope.aliyuncs.com/compatible-mode/v1" in base_url
        assert get_default_timeout(presets, "openai_compatible") == 120.0
        print("[PASS] provider mapping ok | Provider 映射正确\n")

    def test_format_debug_lines_contains_key_signals(self):
        print("\n[TEST START] Debug lines include key fields | 调试行包含关键字段")
        debug = {
            "generated_at": "2026-03-02 12:00:00",
            "used_remote_llm": True,
            "requested_provider": "openai_compatible",
            "used_provider": "openai_compatible",
            "llm_model": "qwen-plus",
            "top_k_requested": 3,
            "retrieved_chunks": 3,
        }
        print("[INPUT] minimal debug dict | 最小调试信息字典")
        print("[ACTION] call format_debug_lines | 调用 format_debug_lines")
        lines = format_debug_lines(debug)
        print("[EXPECTED] lines contain llm/chunk fields | 输出包含 llm/chunk 字段")
        text = "\n".join(lines)
        assert "时间戳" in text
        assert "是否使用大模型" in text
        assert "检索到的 chunks 数" in text
        assert "qwen-plus" in text
        print("[PASS] debug line rendering ok | 调试行渲染正确\n")

    def test_now_timestamp_has_expected_format(self):
        print("\n[TEST START] now_timestamp format check | 时间戳格式检查")
        print("[ACTION] call now_timestamp | 调用 now_timestamp")
        ts = now_timestamp()
        print("[EXPECTED] format YYYY-MM-DD HH:MM:SS | 格式为 年-月-日 时:分:秒")
        assert len(ts) == 19
        assert ts[4] == "-" and ts[7] == "-" and ts[10] == " "
        assert ts[13] == ":" and ts[16] == ":"
        print("[PASS] timestamp format ok | 时间戳格式正确\n")
