"""
Phase 4 后续：对话框式 Web UI（Streamlit）
运行方式：
    streamlit run web_app.py
"""

from __future__ import annotations

import os
from datetime import datetime

from config.env import load_env_defaults
from config.llm_presets import (
    get_default_base_url,
    get_default_timeout,
    get_models_for_provider,
    get_provider_options,
    load_llm_presets,
)
from pipeline import answer_with_store, build_runtime


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
        f"- 时间戳 / Timestamp: {debug.get('generated_at')}",
        f"- 是否使用大模型 / Remote LLM used: {debug.get('used_remote_llm')}",
        f"- 请求 Provider / Requested provider: {debug.get('requested_provider')}",
        f"- 实际 Provider / Used provider: {debug.get('used_provider')}",
        f"- 模型 / Model: {debug.get('llm_model')}",
        f"- Base URL: {debug.get('llm_base_url')}",
        f"- Top-k 检索数 / Retrieved chunks: {debug.get('retrieved_chunks')} (requested {debug.get('top_k_requested')})",
        f"- 最小相关度 / Min relevance score: {debug.get('min_relevance_score')}",
        f"- 最高检索分数 / Best retrieval score: {debug.get('best_retrieval_score')}",
        f"- 触发低相关过滤 / Relevance filter triggered: {debug.get('relevance_filter_triggered')}",
        f"- FAISS 已启用 / FAISS enabled: {debug.get('faiss_enabled')}",
        f"- 返回来源数 / Sources returned: {debug.get('sources_returned')}",
        f"- 允许回退 / Fallback enabled: {debug.get('fallback_enabled')}",
        f"- 发生回退 / Fallback triggered: {debug.get('fallback_triggered')}",
        f"- LLM 尝试次数 / LLM attempts: {debug.get('llm_attempts')}",
        f"- LLM 错误 / LLM error: {debug.get('llm_error')}",
    ]


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run() -> None:
    try:
        import streamlit as st
    except Exception as exc:  # pragma: no cover - 运行时依赖
        raise RuntimeError("请先安装 streamlit：python -m pip install streamlit") from exc

    env_values = load_env_defaults()
    presets = load_llm_presets()

    st.set_page_config(page_title="RAG Chat UI", page_icon="💬", layout="wide")
    st.title("💬 RAG Chat UI")
    st.caption("基于课程资料的智能问答界面 / Course material Q&A (local · OpenAI · OpenAI-compatible)")

    with st.sidebar:
        st.subheader("运行参数 / Runtime Settings")

        top_k = st.number_input("Top-k 检索数量 / Top-k Results", min_value=1, max_value=20, value=3, step=1)
        st.caption("返回最相关的 K 个文档片段 / Number of top relevant chunks to retrieve")

        min_relevance_score = st.number_input(
            "最小相关度 / Min Relevance Score",
            min_value=0.0,
            max_value=1.0,
            value=0.0,
            step=0.05,
        )
        st.caption("低于此分数的结果将被丢弃，0 表示关闭 / Discard results below this score (0 = off)")

        st.divider()
        st.subheader("模型配置 / Model Configuration")

        provider_options = get_provider_options(presets)
        default_provider = env_values.get("LLM_PROVIDER", presets.get("default_provider", provider_options[0]))
        if default_provider not in provider_options:
            default_provider = provider_options[0]

        tab_provider, tab_model, tab_endpoint = st.tabs(["Provider", "Model", "Endpoint"])

        with tab_provider:
            llm_provider = st.radio(
                "LLM Provider",
                options=provider_options,
                index=provider_options.index(default_provider),
                horizontal=False,
            )
            st.caption("选择模型服务提供方 / Choose the LLM service provider")

        models = get_models_for_provider(presets, llm_provider)
        with tab_model:
            llm_model = st.selectbox("模型 / Model", options=models, index=0)
            st.caption("当前 Provider 下可用的模型 / Available models for the selected provider")

        preset_base_url = get_default_base_url(presets, llm_provider)
        with tab_endpoint:
            if llm_provider == "local":
                llm_base_url = ""
                st.info("本地模式无需配置 Base URL。/ No Base URL needed in local mode.")
            else:
                llm_base_url = st.text_input("Base URL", value=preset_base_url)
                st.caption("当前 Provider 的预置地址，可手动覆盖 / Preset endpoint URL, editable")
            api_key_ready = bool(env_values.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))
            st.caption(f"API Key：{'✅ 已加载 / Loaded' if api_key_ready else '⚠️ 未检测到 / Not found'}")

        st.divider()
        st.subheader("生成参数 / Generation Settings")

        temperature = st.slider("Temperature 采样温度", min_value=0.0, max_value=1.5, value=0.2, step=0.1)
        st.caption("越低越稳定，越高越发散 / Lower = more focused, higher = more creative")

        timeout_default = get_default_timeout(presets, llm_provider)
        llm_timeout = st.number_input("超时时间 / Timeout (sec)", min_value=1.0, max_value=300.0, value=timeout_default)
        st.caption("含重试的总超时预算（秒）/ Total timeout budget including retries")

        llm_max_retries = st.number_input("最大重试次数 / Max Retries", min_value=0, max_value=5, value=1, step=1)
        st.caption("请求失败时自动重试的最大次数 / Max number of auto-retries on failure")

        llm_fallback_local = st.checkbox("回退本地 / Fallback to local on failure", value=True)
        st.caption("远程调用失败时回退到本地占位回答 / Use local placeholder answer if remote LLM fails")

        st.divider()
        st.subheader("界面选项 / UI Options")

        show_debug = st.checkbox("显示调试信息 / Show Debug Info", value=True)
        st.caption("在每条回答中附加检索状态、模型信息等 / Append retrieval stats and model info to each reply")

        embed_backend = st.selectbox(
            "Embedding 后端 / Embedding Backend",
            options=["auto", "sentence_transformers", "hash"],
            index=0,
        )
        st.caption("auto = 优先语义嵌入，不可用时降级 hash / auto = prefer ST, fallback to hash if unavailable")

        force_rebuild = st.checkbox("强制重建 / Force Rebuild Artifacts", value=False)
        st.caption("忽略缓存，重新构建 chunks / vectors / index / Ignore cache and rebuild all artifacts")

        if st.button("🗑️ 清除会话 / Clear Chat"):
            st.session_state["messages"] = []
            st.rerun()

    @st.cache_resource
    def _cached_runtime(force_rebuild_flag: bool, _chunk_size: int, _overlap: int, _embed_dim: int, _embed_backend: str):
        return build_runtime(
            force_rebuild=force_rebuild_flag,
            chunk_size=_chunk_size,
            overlap=_overlap,
            embed_dim=_embed_dim,
            embed_backend=_embed_backend,
        )

    from config.defaults import DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_EMBED_DIM
    vector_store, faiss_index = _cached_runtime(force_rebuild, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_EMBED_DIM, embed_backend)

    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.caption(f"时间 / Time: {msg.get('timestamp', '-')}")
            st.markdown(msg["content"])
            if msg.get("role") == "assistant" and show_debug and msg.get("debug"):
                with st.expander("调试信息 / Debug Info", expanded=False):
                    for line in format_debug_lines(msg.get("debug", {})):
                        st.markdown(line)

    query = st.chat_input("输入问题 / Ask a question about your course materials...")
    if not query:
        return

    user_ts = now_timestamp()
    st.session_state["messages"].append({"role": "user", "content": query, "timestamp": user_ts})
    with st.chat_message("user"):
        st.caption(f"时间 / Time: {user_ts}")
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("思考中 / Thinking..."):
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
                min_relevance_score=None if float(min_relevance_score) <= 0 else float(min_relevance_score),
            )
            content = build_assistant_message(response.get("answer", ""), response.get("sources", []))
            assistant_ts = now_timestamp()
            st.caption(f"时间 / Time: {assistant_ts}")
            st.markdown(content)
            if show_debug:
                with st.expander("调试信息 / Debug Info", expanded=False):
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
