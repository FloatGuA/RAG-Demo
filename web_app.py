"""
Phase 4 后续：对话框式 Web UI（Streamlit）
运行方式：
    streamlit run web_app.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from app import answer_with_store, build_runtime


DEFAULT_PRESETS = {
    "default_provider": "openai_compatible",
    "providers": {
        "local": {"base_url": "", "timeout_sec": 120, "models": ["local-fallback"]},
        "openai": {
            "base_url": "https://api.openai.com/v1",
            "timeout_sec": 120,
            "models": ["gpt-4o-mini", "gpt-4o"],
        },
        "openai_compatible": {
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "timeout_sec": 120,
            "models": ["qwen3.5-plus", "qwen-plus"],
        },
    },
}


def load_env_file(path: str = ".env") -> dict[str, str]:
    values: dict[str, str] = {}
    p = Path(path)
    if not p.exists():
        return values
    for raw_line in p.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def load_llm_presets(path: str = "llm_presets.json") -> dict:
    p = Path(path)
    if not p.exists():
        return DEFAULT_PRESETS
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_PRESETS
    if not isinstance(data, dict) or "providers" not in data:
        return DEFAULT_PRESETS
    providers = data.get("providers")
    if not isinstance(providers, dict) or not providers:
        return DEFAULT_PRESETS
    return data


def get_provider_options(presets: dict) -> list[str]:
    providers = presets.get("providers", {})
    if not isinstance(providers, dict):
        return list(DEFAULT_PRESETS["providers"].keys())
    options = list(providers.keys())
    return options or list(DEFAULT_PRESETS["providers"].keys())


def get_models_for_provider(presets: dict, provider: str) -> list[str]:
    providers = presets.get("providers", {})
    info = providers.get(provider, {}) if isinstance(providers, dict) else {}
    models = info.get("models", []) if isinstance(info, dict) else []
    if not isinstance(models, list) or not models:
        return ["local-fallback"] if provider == "local" else ["gpt-4o-mini"]
    return [str(m) for m in models]


def get_default_base_url(presets: dict, provider: str) -> str:
    providers = presets.get("providers", {})
    info = providers.get(provider, {}) if isinstance(providers, dict) else {}
    base_url = info.get("base_url", "") if isinstance(info, dict) else ""
    return str(base_url)


def get_default_timeout(presets: dict, provider: str) -> float:
    providers = presets.get("providers", {})
    info = providers.get(provider, {}) if isinstance(providers, dict) else {}
    timeout_sec = info.get("timeout_sec", 120) if isinstance(info, dict) else 120
    try:
        val = float(timeout_sec)
    except (TypeError, ValueError):
        return 120.0
    return val if val > 0 else 120.0


def format_sources_lines(sources: list[dict]) -> list[str]:
    """将 sources 转为可渲染行文本。"""
    if not sources:
        return ["- (none)"]
    return [f"- {s.get('source')} (page {s.get('page')})" for s in sources]


def build_assistant_message(answer: str, sources: list[dict]) -> str:
    """构建助手气泡展示文本。"""
    lines = [answer.strip() or "I don't know", "", "Sources:"]
    lines.extend(format_sources_lines(sources))
    return "\n".join(lines)


def format_debug_lines(debug: dict) -> list[str]:
    return [
        f"- 时间戳: {debug.get('generated_at')}",
        f"- 是否使用大模型: {debug.get('used_remote_llm')}",
        f"- 请求 Provider: {debug.get('requested_provider')}",
        f"- 实际使用 Provider: {debug.get('used_provider')}",
        f"- 模型: {debug.get('llm_model')}",
        f"- Base URL: {debug.get('llm_base_url')}",
        f"- Top-k: {debug.get('top_k_requested')}",
        f"- 检索到的 chunks 数: {debug.get('retrieved_chunks')}",
        f"- 是否启用 FAISS: {debug.get('faiss_enabled')}",
        f"- 返回来源数: {debug.get('sources_returned')}",
        f"- 是否允许回退本地: {debug.get('fallback_enabled')}",
        f"- 是否发生回退: {debug.get('fallback_triggered')}",
        f"- LLM 尝试次数: {debug.get('llm_attempts')}",
        f"- LLM 错误: {debug.get('llm_error')}",
    ]


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run() -> None:
    try:
        import streamlit as st
    except Exception as exc:  # pragma: no cover - 运行时依赖
        raise RuntimeError("请先安装 streamlit：python -m pip install streamlit") from exc

    env_values = load_env_file(".env")
    presets = load_llm_presets("llm_presets.json")

    st.set_page_config(page_title="RAG Chat UI", page_icon="💬", layout="wide")
    st.title("💬 RAG Chat UI")
    st.caption("基于课程资料的问答界面（支持 local / OpenAI / OpenAI-compatible）")

    with st.sidebar:
        st.subheader("Runtime")
        st.caption("Top-k：返回 K 个最可能相关的检索结果。")
        top_k = st.number_input("Top-k", min_value=1, max_value=20, value=3, step=1)
        provider_options = get_provider_options(presets)
        default_provider = env_values.get("LLM_PROVIDER", presets.get("default_provider", provider_options[0]))
        if default_provider not in provider_options:
            default_provider = provider_options[0]

        tab_provider, tab_model, tab_endpoint = st.tabs(["Provider", "Model", "Endpoint"])
        with tab_provider:
            st.caption("LLM Provider：选择模型服务提供方（本地 / OpenAI / OpenAI 兼容接口）。")
            llm_provider = st.radio(
                "LLM Provider",
                options=provider_options,
                index=provider_options.index(default_provider),
                horizontal=False,
            )

        models = get_models_for_provider(presets, llm_provider)
        default_model = env_values.get("LLM_MODEL", models[0])
        if default_model not in models:
            default_model = models[0]
        with tab_model:
            st.caption("Model：选择当前 Provider 下可用的模型。")
            llm_model = st.selectbox(
                "Model",
                options=models,
                index=models.index(default_model),
            )

        preset_base_url = get_default_base_url(presets, llm_provider)
        default_base_url = env_values.get("LLM_BASE_URL", preset_base_url)
        with tab_endpoint:
            if llm_provider == "local":
                llm_base_url = ""
                st.info("本地模式无需配置 Base URL。")
            else:
                st.caption("Base URL：模型服务接口地址（通常由预置配置自动带出）。")
                llm_base_url = st.text_input("Base URL", value=default_base_url)
            api_key_ready = bool(env_values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
            st.caption(f"API Key 状态：{'已加载' if api_key_ready else '未检测到'}")

        st.caption("Temperature：控制回答随机性，越低越稳定，越高越发散。")
        temperature = st.slider("Temperature", min_value=0.0, max_value=1.5, value=0.2, step=0.1)
        timeout_default = get_default_timeout(presets, llm_provider)
        st.caption("Timeout：本次回答总超时预算（含重试，单位秒）。")
        llm_timeout = st.number_input("Timeout (sec)", min_value=1.0, max_value=300.0, value=timeout_default)
        st.caption("Max retries：请求失败时自动重试次数。")
        llm_max_retries = st.number_input("Max retries", min_value=0, max_value=5, value=1, step=1)
        st.caption("Fallback：远程调用失败时，是否自动回退本地占位回答。")
        llm_fallback_local = st.checkbox("Fallback to local on provider failure", value=True)
        show_debug = st.checkbox("Show debug info in reply", value=True)
        st.caption("在每条回答中输出调试信息（模型、检索 chunk 数、FAISS、回退状态等）。")

        st.caption("Force rebuild：忽略缓存，重新构建 chunks / vectors / index。")
        force_rebuild = st.checkbox("Force rebuild artifacts", value=False)
        if st.button("Clear chat"):
            st.session_state["messages"] = []
            st.rerun()

    @st.cache_resource
    def _cached_runtime(force_rebuild_flag: bool):
        return build_runtime(force_rebuild=force_rebuild_flag)

    vector_store, faiss_index = _cached_runtime(force_rebuild)

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.caption(f"时间: {msg.get('timestamp', '-')}")
            st.markdown(msg["content"])
            if msg.get("role") == "assistant" and show_debug and msg.get("debug"):
                with st.expander("Debug Info", expanded=False):
                    for line in format_debug_lines(msg.get("debug", {})):
                        st.markdown(line)

    query = st.chat_input("Ask a question about your course materials...")
    if not query:
        return

    user_ts = now_timestamp()
    st.session_state["messages"].append({"role": "user", "content": query, "timestamp": user_ts})
    with st.chat_message("user"):
        st.caption(f"时间: {user_ts}")
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = answer_with_store(
                query,
                vector_store,
                faiss_index=faiss_index,
                top_k=int(top_k),
                llm_provider=llm_provider,
                llm_model=llm_model,
                llm_base_url=llm_base_url,
                temperature=float(temperature),
                llm_timeout=float(llm_timeout),
                llm_max_retries=int(llm_max_retries),
                llm_fallback_local=llm_fallback_local,
            )
            content = build_assistant_message(response.get("answer", ""), response.get("sources", []))
            assistant_ts = now_timestamp()
            st.caption(f"时间: {assistant_ts}")
            st.markdown(content)
            if show_debug:
                with st.expander("Debug Info", expanded=False):
                    for line in format_debug_lines(response.get("debug", {})):
                        st.markdown(line)
    st.session_state["messages"].append(
        {
            "role": "assistant",
            "content": content,
            "timestamp": assistant_ts,
            "debug": response.get("debug", {}),
        }
    )


if __name__ == "__main__":
    run()
