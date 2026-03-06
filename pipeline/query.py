"""在线问答逻辑 — 检索、生成、格式化。零 IO 绑定。"""

from __future__ import annotations

from datetime import datetime

from retrieval import (
    format_response,
    generate_answer_with_meta,
    build_prompt,
    retrieve_top_k,
)


def answer_with_store(
    query: str,
    vector_store: object,
    *,
    faiss_index: object | None = None,
    top_k: int = 3,
    llm_provider: str = "local",
    llm_model: str = "gpt-4o-mini",
    llm_base_url: str = "",
    temperature: float = 0.2,
    llm_timeout: float = 120.0,
    llm_max_retries: int = 1,
    llm_fallback_local: bool = True,
    min_relevance_score: float | None = None,
) -> dict:
    """执行完整问答链路，返回 {answer, sources, debug} dict。"""
    if top_k <= 0:
        raise ValueError("top_k 必须为正整数")
    if min_relevance_score is not None and not (0.0 <= min_relevance_score <= 1.0):
        raise ValueError("min_relevance_score 必须在 [0, 1] 区间内")

    retrieved = retrieve_top_k(
        query,
        vector_store,  # type: ignore[arg-type]
        top_k=top_k,
        faiss_index=faiss_index,
    )
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
    )
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
    }
    return response


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
