"""在线问答逻辑 — 检索、生成、格式化。零 IO 绑定。"""

from __future__ import annotations

import time
from collections.abc import Iterator
from datetime import datetime

from config.defaults import DEFAULT_RERANK_MODEL
from retrieval import (
    format_response,
    generate_answer_with_meta,
    generate_answer_stream,
    build_prompt,
    retrieve_top_k,
    hybrid_retrieve,
    has_rank_bm25,
    has_cross_encoder,
)


def answer_with_store(
    query: str,
    vector_store: object,
    *,
    faiss_index: object | None = None,
    top_k: int = 3,
    use_hybrid: bool = False,
    use_rerank: bool = False,
    rerank_initial_k: int = 20,
    rerank_model: str = DEFAULT_RERANK_MODEL,
    llm_provider: str = "local",
    llm_model: str = "gpt-4o-mini",
    llm_base_url: str = "",
    temperature: float = 0.2,
    llm_timeout: float = 120.0,
    llm_max_retries: int = 1,
    llm_fallback_local: bool = True,
    min_relevance_score: float | None = None,
    chat_history: list[dict] | None = None,
) -> dict:
    """执行完整问答链路，返回 {answer, sources, debug} dict。"""
    if top_k <= 0:
        raise ValueError("top_k 必须为正整数")
    if min_relevance_score is not None and not (0.0 <= min_relevance_score <= 1.0):
        raise ValueError("min_relevance_score 必须在 [0, 1] 区间内")

    t_start = time.monotonic()

    if use_hybrid or use_rerank:
        retrieved = hybrid_retrieve(
            query,
            vector_store,  # type: ignore[arg-type]
            top_k=top_k,
            faiss_index=faiss_index,
            use_bm25=use_hybrid,
            use_rerank=use_rerank,
            rerank_initial_k=rerank_initial_k,
            rerank_model=rerank_model,
        )
    else:
        retrieved = retrieve_top_k(
            query,
            vector_store,  # type: ignore[arg-type]
            top_k=top_k,
            faiss_index=faiss_index,
        )

    t_retrieved = time.monotonic()

    best_retrieval_score = float(retrieved[0]["score"]) if retrieved else None
    relevance_filter_triggered = False
    if min_relevance_score is not None:
        retrieved = [r for r in retrieved if float(r.get("score", -1.0)) >= min_relevance_score]
        if best_retrieval_score is not None and not retrieved:
            relevance_filter_triggered = True

    prompt_text = build_prompt(query, retrieved)
    answer, llm_meta = generate_answer_with_meta(
        prompt_text,
        contexts=retrieved,
        provider=llm_provider,
        model=llm_model,
        base_url=llm_base_url or None,
        temperature=temperature,
        timeout=llm_timeout,
        max_retries=llm_max_retries,
        fallback_to_local=llm_fallback_local,
        chat_history=chat_history,
    )

    t_done = time.monotonic()

    response = format_response(answer, retrieved)
    response["debug"] = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "used_remote_llm": bool(llm_meta.get("used_remote_llm", False)),
        "requested_provider": llm_meta.get("requested_provider"),
        "used_provider": llm_meta.get("used_provider"),
        "llm_model": llm_model,
        "llm_base_url": llm_base_url or "(none)",
        "fallback_enabled": llm_fallback_local,
        "fallback_triggered": bool(llm_meta.get("fallback_triggered", False)),
        "llm_attempts": int(llm_meta.get("attempts", 0)),
        "llm_error": llm_meta.get("error"),
        "top_k_requested": int(top_k),
        "min_relevance_score": min_relevance_score,
        "best_retrieval_score": best_retrieval_score,
        "relevance_filter_triggered": relevance_filter_triggered,
        "retrieved_chunks": len(retrieved),
        "faiss_enabled": faiss_index is not None,
        "sources_returned": len(response.get("sources", [])),
        "hybrid_enabled": use_hybrid,
        "bm25_available": has_rank_bm25(),
        "rerank_enabled": use_rerank,
        "rerank_available": has_cross_encoder(),
        "rerank_initial_k": rerank_initial_k if use_rerank else None,
        "rerank_model": rerank_model if use_rerank else None,
        "latency_retrieval_ms": round((t_retrieved - t_start) * 1000),
        "latency_generation_ms": round((t_done - t_retrieved) * 1000),
        "latency_total_ms": round((t_done - t_start) * 1000),
    }
    return response


def answer_with_store_stream(
    query: str,
    vector_store: object,
    *,
    faiss_index: object | None = None,
    top_k: int = 3,
    use_hybrid: bool = False,
    use_rerank: bool = False,
    rerank_initial_k: int = 20,
    rerank_model: str = DEFAULT_RERANK_MODEL,
    llm_provider: str = "local",
    llm_model: str = "gpt-4o-mini",
    llm_base_url: str = "",
    temperature: float = 0.2,
    llm_timeout: float = 120.0,
    llm_fallback_local: bool = True,
    min_relevance_score: float | None = None,
    chat_history: list[dict] | None = None,
) -> tuple[Iterator[str], list[dict], dict]:
    """
    流式问答：先做检索，再流式生成。
    返回 (stream, sources, partial_debug)。
    stream: 文本 chunk 迭代器（传给 st.write_stream）
    sources: 来源列表
    partial_debug: 检索侧 debug 信息（不含 LLM meta，因为流未结束）
    """
    if top_k <= 0:
        raise ValueError("top_k 必须为正整数")

    t_start = time.monotonic()

    # 检索
    if use_hybrid or use_rerank:
        retrieved = hybrid_retrieve(
            query, vector_store,  # type: ignore[arg-type]
            top_k=top_k, faiss_index=faiss_index,
            use_bm25=use_hybrid, use_rerank=use_rerank,
            rerank_initial_k=rerank_initial_k, rerank_model=rerank_model,
        )
    else:
        retrieved = retrieve_top_k(
            query, vector_store,  # type: ignore[arg-type]
            top_k=top_k, faiss_index=faiss_index,
        )

    t_retrieved = time.monotonic()

    best_retrieval_score = float(retrieved[0]["score"]) if retrieved else None
    relevance_filter_triggered = False
    if min_relevance_score is not None:
        retrieved = [r for r in retrieved if float(r.get("score", -1.0)) >= min_relevance_score]
        if best_retrieval_score is not None and not retrieved:
            relevance_filter_triggered = True

    prompt_text = build_prompt(query, retrieved)
    response = format_response("", retrieved)  # answer filled in after streaming

    partial_debug = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "used_remote_llm": llm_provider not in ("local",),
        "requested_provider": llm_provider,
        "used_provider": llm_provider,
        "llm_model": llm_model,
        "llm_base_url": llm_base_url or "(none)",
        "fallback_enabled": llm_fallback_local,
        "fallback_triggered": False,
        "llm_attempts": 1,
        "llm_error": None,
        "top_k_requested": int(top_k),
        "min_relevance_score": min_relevance_score,
        "best_retrieval_score": best_retrieval_score,
        "relevance_filter_triggered": relevance_filter_triggered,
        "retrieved_chunks": len(retrieved),
        "faiss_enabled": faiss_index is not None,
        "sources_returned": len(response.get("sources", [])),
        "hybrid_enabled": use_hybrid,
        "bm25_available": has_rank_bm25(),
        "rerank_enabled": use_rerank,
        "rerank_available": has_cross_encoder(),
        "rerank_initial_k": rerank_initial_k if use_rerank else None,
        "rerank_model": rerank_model if use_rerank else None,
        "latency_retrieval_ms": round((t_retrieved - t_start) * 1000),
        "latency_generation_ms": None,  # 流式模式下生成耗时由 UI 层统计
        "latency_total_ms": None,
    }

    stream = generate_answer_stream(
        prompt_text,
        contexts=retrieved,
        provider=llm_provider,
        model=llm_model,
        base_url=llm_base_url or None,
        temperature=temperature,
        timeout=llm_timeout,
        fallback_to_local=llm_fallback_local,
        chat_history=chat_history,
    )
    return stream, response.get("sources", []), partial_debug


def _debug_to_lines(debug: dict) -> list[str]:
    return [
        f"- used_remote_llm: {debug.get('used_remote_llm')}",
        f"- requested_provider: {debug.get('requested_provider')}",
        f"- used_provider: {debug.get('used_provider')}",
        f"- llm_model: {debug.get('llm_model')}",
        f"- llm_base_url: {debug.get('llm_base_url')}",
        f"- top_k_requested: {debug.get('top_k_requested')}",
        f"- retrieved_chunks: {debug.get('retrieved_chunks')}",
        f"- faiss_enabled: {debug.get('faiss_enabled')}",
        f"- hybrid_enabled: {debug.get('hybrid_enabled')}",
        f"- bm25_available: {debug.get('bm25_available')}",
        f"- rerank_enabled: {debug.get('rerank_enabled')}",
        f"- rerank_available: {debug.get('rerank_available')}",
        f"- rerank_initial_k: {debug.get('rerank_initial_k')}",
        f"- sources_returned: {debug.get('sources_returned')}",
        f"- fallback_enabled: {debug.get('fallback_enabled')}",
        f"- fallback_triggered: {debug.get('fallback_triggered')}",
        f"- llm_attempts: {debug.get('llm_attempts')}",
        f"- llm_error: {debug.get('llm_error')}",
        f"- min_relevance_score: {debug.get('min_relevance_score')}",
        f"- best_retrieval_score: {debug.get('best_retrieval_score')}",
        f"- relevance_filter_triggered: {debug.get('relevance_filter_triggered')}",
    ]


def render_response(response: dict, *, include_debug: bool = False) -> str:
    """将 answer_with_store 返回的 dict 格式化为可打印字符串。"""
    lines = [f"Answer: {response.get('answer', '')}", "", "Sources:"]
    sources = response.get("sources", [])
    if not sources:
        lines.append("- (none)")
    else:
        for s in sources:
            lines.append(f"- {s.get('source')} (page {s.get('page')})")
    if include_debug:
        lines.extend(["", "Debug:", *_debug_to_lines(response.get("debug", {}))])
    return "\n".join(lines)
