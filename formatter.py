"""
模块7：Response Formatter
将 answer 与检索上下文整合为结构化输出。
"""

from __future__ import annotations


def format_response(answer: str, contexts: list[dict]) -> dict:
    """
    返回：
    {
      "answer": str,
      "sources": [{"source": str|None, "page": int|None}]
    }
    """
    seen: set[tuple[object, object]] = set()
    sources: list[dict] = []
    for ctx in contexts:
        key = (ctx.get("source"), ctx.get("page"))
        if key in seen:
            continue
        seen.add(key)
        sources.append({"source": ctx.get("source"), "page": ctx.get("page")})
    return {"answer": answer, "sources": sources}
