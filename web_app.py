"""
RAG Demo Web UI — Chat + Evaluation Dashboard
运行方式：
    streamlit run web_app.py
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from config.env import load_env_defaults
from config.llm_presets import (
    get_default_base_url,
    get_default_timeout,
    get_models_for_provider,
    get_provider_options,
    load_llm_presets,
)
from pipeline import answer_with_store, answer_with_store_stream, build_runtime


# ── Chat helpers ────────────────────────────────────────────────────────────

def format_sources_lines(sources: list[dict]) -> list[str]:
    if not sources:
        return ["- (none)"]
    return [f"- {s.get('source')} (page {s.get('page')})" for s in sources]


def build_assistant_message(answer: str, sources: list[dict]) -> str:
    lines = [answer.strip() or "I don't know", "", "Sources:"]
    lines.extend(format_sources_lines(sources))
    return "\n".join(lines)


def format_debug_lines(debug: dict) -> list[str]:
    lat_r = debug.get("latency_retrieval_ms")
    lat_g = debug.get("latency_generation_ms")
    lat_t = debug.get("latency_total_ms")
    lat_str = (
        f"检索 {lat_r} ms / 生成 {lat_g} ms / 合计 {lat_t} ms"
        if lat_r is not None and lat_g is not None
        else f"检索 {lat_r} ms（流式，生成耗时含在网络中）"
        if lat_r is not None
        else "N/A"
    )
    return [
        f"- 时间戳 / Timestamp: {debug.get('generated_at')}",
        f"- 延迟分解 / Latency: {lat_str}",
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
        f"- 混合检索 / Hybrid enabled: {debug.get('hybrid_enabled')}",
        f"- BM25 可用 / BM25 available: {debug.get('bm25_available')}",
        f"- Rerank 已启用 / Rerank enabled: {debug.get('rerank_enabled')}",
        f"- Rerank 可用 / Rerank available: {debug.get('rerank_available')}",
        f"- Rerank 粗召回数 / Rerank initial k: {debug.get('rerank_initial_k')}",
        f"- 返回来源数 / Sources returned: {debug.get('sources_returned')}",
        f"- 允许回退 / Fallback enabled: {debug.get('fallback_enabled')}",
        f"- 发生回退 / Fallback triggered: {debug.get('fallback_triggered')}",
        f"- LLM 尝试次数 / LLM attempts: {debug.get('llm_attempts')}",
        f"- LLM 错误 / LLM error: {debug.get('llm_error')}",
    ]


def now_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_chat_history(messages: list[dict], max_turns: int = 6) -> list[dict]:
    """
    从 session messages 提取最近 max_turns 轮对话，格式化为 OpenAI messages 列表。
    每条 assistant 消息只保留原始答案文本（不含 Sources 格式化部分）。
    """
    history: list[dict] = []
    for msg in messages[-max_turns * 2:]:
        role = msg.get("role")
        if role == "user":
            history.append({"role": "user", "content": msg["content"]})
        elif role == "assistant":
            # 优先用存储的原始答案，避免把 Sources 格式带入历史
            answer_text = msg.get("answer") or msg["content"].split("\n\nSources:")[0].strip()
            history.append({"role": "assistant", "content": answer_text})
    return history


# ── Eval dashboard helpers ───────────────────────────────────────────────────

def get_available_reports(eval_dir: Path) -> list[Path]:
    if not eval_dir.exists():
        return []
    return sorted(eval_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def load_eval_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: float | None, pct: bool = False) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%" if pct else f"{value:.4f}"


def render_eval_summary(summary: dict) -> None:
    import streamlit as st
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("样本数 / Cases", summary.get("total_cases", "N/A"))
    c2.metric("Token F1", _fmt(summary.get("answer_token_f1_avg"), pct=True))
    c3.metric("Keyword Recall", _fmt(summary.get("keyword_recall_avg"), pct=True))
    c4.metric("Source Recall", _fmt(summary.get("source_recall_avg"), pct=True))
    c5.metric("Source Hit Rate", _fmt(summary.get("source_hit_rate"), pct=True))
    em = summary.get("answer_exact_match_avg")
    if em is not None:
        st.caption(f"Exact Match: {_fmt(em, pct=True)}")


def render_eval_cases(cases: list[dict]) -> None:
    import streamlit as st

    # 汇总表格
    rows = []
    for c in cases:
        m = c.get("metrics", {})
        rows.append({
            "ID": c.get("id", ""),
            "Query": c.get("query", "")[:60] + ("…" if len(c.get("query", "")) > 60 else ""),
            "Answer": c.get("answer", "")[:60] + ("…" if len(c.get("answer", "")) > 60 else ""),
            "KW Recall": _fmt(m.get("keyword_recall"), pct=True),
            "Src Recall": _fmt(m.get("source_recall"), pct=True),
            "Src Hit": "✅" if m.get("source_hit") else ("❌" if "source_hit" in m else "—"),
            "Token F1": _fmt(m.get("answer_token_f1"), pct=True),
        })

    st.dataframe(rows, use_container_width=True)

    # 逐条展开
    st.subheader("逐条详情 / Per-case Details")
    for c in cases:
        m = c.get("metrics", {})
        label = f"[{c.get('id', '?')}] {c.get('query', '')[:70]}"
        with st.expander(label):
            st.markdown(f"**Answer:** {c.get('answer', '(empty)')}")
            srcs = c.get("sources", [])
            if srcs:
                st.markdown("**Sources:** " + " · ".join(
                    f"{s.get('source')} p.{s.get('page')}" for s in srcs
                ))
            if m:
                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("KW Recall", _fmt(m.get("keyword_recall"), pct=True))
                mc2.metric("Src Recall", _fmt(m.get("source_recall"), pct=True))
                mc3.metric("Src Hit", "✅" if m.get("source_hit") else ("❌" if "source_hit" in m else "—"))
                mc4.metric("Token F1", _fmt(m.get("answer_token_f1"), pct=True))


# ── Main ─────────────────────────────────────────────────────────────────────

def run() -> None:
    try:
        import streamlit as st
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("请先安装 streamlit：python -m pip install streamlit") from exc

    env_values = load_env_defaults()
    presets = load_llm_presets()

    st.set_page_config(page_title="RAG Demo", page_icon="💬", layout="wide")
    st.title("RAG Demo")
    st.caption("基于课程资料的智能问答 / Course material Q&A (local · OpenAI · OpenAI-compatible)")

    # ── Sidebar ──────────────────────────────────────────────────────────────
    with st.sidebar:
        st.subheader("运行参数 / Runtime Settings")

        top_k = st.number_input("Top-k 检索数量 / Top-k Results", min_value=1, max_value=20, value=3, step=1)
        st.caption("返回最相关的 K 个文档片段 / Number of top relevant chunks to retrieve")

        min_relevance_score = st.number_input(
            "最小相关度 / Min Relevance Score",
            min_value=0.0, max_value=1.0, value=0.0, step=0.05,
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
            llm_provider = st.radio("LLM Provider", options=provider_options,
                                    index=provider_options.index(default_provider), horizontal=False)
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

        use_streaming = st.checkbox("流式输出 / Streaming Output", value=True)
        st.caption("逐字显示生成内容，无需等待完整响应 / Stream tokens as generated instead of waiting for full response")

        embed_backend = st.selectbox(
            "Embedding 后端 / Embedding Backend",
            options=["auto", "sentence_transformers", "hash"], index=0,
        )
        st.caption("auto = 优先语义嵌入，不可用时降级 hash / auto = prefer ST, fallback to hash if unavailable")

        st.divider()
        st.subheader("检索增强 / Retrieval Enhancement")

        use_hybrid = st.checkbox("混合检索 / Hybrid Retrieval (BM25 + Dense)", value=False)
        st.caption("Dense 向量 + BM25 关键词，RRF 融合，改善精确匹配 / Combine dense and keyword search via RRF")

        use_rerank = st.checkbox("Cross-Encoder 重排 / Rerank Results", value=False)
        st.caption("用 Cross-Encoder 对候选精排，提升准确率，速度略慢 / Rerank candidates with cross-encoder for higher precision")

        rerank_initial_k = st.number_input(
            "Rerank 粗召回数 / Rerank Initial K",
            min_value=5, max_value=50, value=20, step=5, disabled=not use_rerank,
        )
        st.caption("Rerank 前粗检索的候选数量（仅 Rerank 启用时有效）/ Candidates fetched before reranking")

        force_rebuild = st.checkbox("强制重建 / Force Rebuild Artifacts", value=False)
        st.caption("忽略缓存，重新构建 chunks / vectors / index / Ignore cache and rebuild all artifacts")

        if st.button("🗑️ 清除会话 / Clear Chat"):
            st.session_state["messages"] = []
            st.rerun()

    # ── Cached runtime ───────────────────────────────────────────────────────
    @st.cache_resource
    def _cached_runtime(force_rebuild_flag: bool, _chunk_size: int, _overlap: int,
                        _embed_dim: int, _embed_backend: str):
        return build_runtime(
            force_rebuild=force_rebuild_flag,
            chunk_size=_chunk_size, overlap=_overlap,
            embed_dim=_embed_dim, embed_backend=_embed_backend,
        )

    from config.defaults import DEFAULT_CHUNK_SIZE, DEFAULT_EMBED_DIM, DEFAULT_OVERLAP
    vector_store, faiss_index = _cached_runtime(
        force_rebuild, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP, DEFAULT_EMBED_DIM, embed_backend
    )

    # ── Tabs ─────────────────────────────────────────────────────────────────
    tab_chat, tab_eval = st.tabs(["💬 Chat", "📊 Evaluation Dashboard"])

    # ── Chat tab ─────────────────────────────────────────────────────────────
    with tab_chat:
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
        if query:
            user_ts = now_timestamp()
            chat_history = build_chat_history(st.session_state["messages"])
            st.session_state["messages"].append({"role": "user", "content": query, "timestamp": user_ts})
            with st.chat_message("user"):
                st.caption(f"时间 / Time: {user_ts}")
                st.markdown(query)

            with st.chat_message("assistant"):
                assistant_ts = now_timestamp()
                st.caption(f"时间 / Time: {assistant_ts}")

                common_kwargs = dict(
                    top_k=int(top_k), use_hybrid=use_hybrid,
                    use_rerank=use_rerank, rerank_initial_k=int(rerank_initial_k),
                    llm_provider=llm_provider, llm_model=llm_model,
                    llm_base_url=llm_base_url, temperature=float(temperature),
                    llm_timeout=float(llm_timeout),
                    llm_fallback_local=llm_fallback_local,
                    min_relevance_score=None if float(min_relevance_score) <= 0 else float(min_relevance_score),
                    chat_history=chat_history or None,
                )

                if use_streaming:
                    stream, sources, debug = answer_with_store_stream(
                        query, vector_store, faiss_index=faiss_index, **common_kwargs
                    )
                    answer_text = st.write_stream(stream)
                    answer_text = answer_text or "I don't know"
                    # Show sources below streamed answer
                    src_lines = format_sources_lines(sources)
                    st.markdown("**Sources:**\n" + "\n".join(src_lines))
                    content = build_assistant_message(answer_text, sources)
                else:
                    with st.spinner("思考中 / Thinking..."):
                        response = answer_with_store(
                            query, vector_store, faiss_index=faiss_index,
                            llm_max_retries=int(llm_max_retries), **common_kwargs
                        )
                    answer_text = response.get("answer", "")
                    sources = response.get("sources", [])
                    debug = response.get("debug", {})
                    content = build_assistant_message(answer_text, sources)
                    st.markdown(content)

                if show_debug:
                    with st.expander("调试信息 / Debug Info", expanded=False):
                        for line in format_debug_lines(debug):
                            st.markdown(line)

            st.session_state["messages"].append({
                "role": "assistant", "content": content, "answer": answer_text,
                "timestamp": assistant_ts, "debug": debug,
            })

    # ── Evaluation Dashboard tab ──────────────────────────────────────────────
    with tab_eval:
        eval_dir = Path("artifacts/eval")
        reports = get_available_reports(eval_dir)

        # ── 查看历史报告 ──────────────────────────────────────────────────────
        st.subheader("历史报告 / Saved Reports")
        if not reports:
            st.info("暂无评估报告。请先运行 `python cli.py eval` 生成报告。/ No reports found. Run `python cli.py eval` first.")
        else:
            report_names = [p.name for p in reports]
            selected_name = st.selectbox("选择报告 / Select Report", options=report_names)
            selected_path = eval_dir / selected_name

            report = load_eval_report(selected_path)
            summary = report.get("summary", {})
            cases = report.get("cases", [])

            st.caption(f"报告文件：`{selected_path}` · {len(cases)} 条样本")
            st.divider()

            st.subheader("汇总指标 / Summary Metrics")
            render_eval_summary(summary)

            st.divider()
            st.subheader("结果总览 / Results Table")
            render_eval_cases(cases)

        # ── 运行新评估 ────────────────────────────────────────────────────────
        st.divider()
        with st.expander("▶ 运行新评估 / Run New Evaluation", expanded=False):
            eval_set_path = st.text_input(
                "评测集路径 / Eval Set Path",
                value="eval/eval_set.example.json",
            )
            output_path = st.text_input(
                "报告输出路径 / Output Path",
                value="artifacts/eval/latest_report.json",
            )
            eval_top_k = st.number_input("Top-k（评估用）", min_value=1, max_value=20, value=int(top_k), step=1)
            eval_min_rel = st.number_input(
                "Min Relevance Score（评估用）", min_value=0.0, max_value=1.0, value=0.0, step=0.05,
            )

            if st.button("🚀 开始评估 / Run Eval"):
                from evaluation import evaluate_cases, load_eval_cases
                try:
                    cases_to_eval = load_eval_cases(eval_set_path)
                except FileNotFoundError as e:
                    st.error(str(e))
                else:
                    def _answer_fn(case: dict) -> dict:
                        return answer_with_store(
                            query=str(case["query"]),
                            vector_store=vector_store,
                            faiss_index=faiss_index,
                            top_k=int(case.get("top_k", eval_top_k)),
                            use_hybrid=use_hybrid,
                            use_rerank=use_rerank,
                            rerank_initial_k=int(rerank_initial_k),
                            llm_provider=llm_provider,
                            llm_model=llm_model,
                            llm_base_url=llm_base_url,
                            temperature=float(temperature),
                            llm_timeout=float(llm_timeout),
                            llm_max_retries=int(llm_max_retries),
                            llm_fallback_local=llm_fallback_local,
                            min_relevance_score=None if eval_min_rel <= 0 else float(eval_min_rel),
                        )

                    with st.spinner(f"评估 {len(cases_to_eval)} 条样本中… / Evaluating {len(cases_to_eval)} cases…"):
                        from evaluation import evaluate_cases
                        new_report = evaluate_cases(cases_to_eval, _answer_fn)

                    out = Path(output_path)
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(json.dumps(new_report, ensure_ascii=False, indent=2), encoding="utf-8")

                    st.success(f"✅ 评估完成，报告已保存至 `{out}`")
                    s = new_report["summary"]
                    st.subheader("本次结果 / Results")
                    render_eval_summary(s)
                    render_eval_cases(new_report["cases"])


if __name__ == "__main__":
    run()
