"""
模块5：Prompt Builder
将 query 与检索到的上下文片段组装为 RAG prompt。
"""

from __future__ import annotations


def build_prompt(
    query: str,
    contexts: list[dict],
    *,
    max_context_chars: int = 4000,
) -> str:
    """
    构建 grounded prompt。
    - 仅允许基于 contexts 回答；
    - 若 contexts 不足以回答，必须输出 I don't know。
    """
    if max_context_chars <= 0:
        raise ValueError("max_context_chars 必须为正整数")

    context_blocks: list[str] = []
    used = 0
    for i, ctx in enumerate(contexts, start=1):
        text = str(ctx.get("text", "")).strip()
        source = ctx.get("source", "unknown")
        page = ctx.get("page", "?")
        block = f"[Context {i}] source={source}, page={page}\n{text}"
        if used + len(block) > max_context_chars:
            remain = max_context_chars - used
            if remain <= 0:
                break
            block = block[:remain]
            context_blocks.append(block)
            break
        context_blocks.append(block)
        used += len(block)

    context_text = "\n\n".join(context_blocks) if context_blocks else "[No context retrieved]"
    return (
        "You are a course assistant.\n"
        "Answer the question ONLY based on the provided context.\n"
        "If the context is insufficient, reply exactly: I don't know.\n\n"
        f"Question:\n{query.strip()}\n\n"
        f"Context:\n{context_text}\n\n"
        "Return a concise answer."
    )
