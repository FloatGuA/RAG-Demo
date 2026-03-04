""".env 文件加载与 LLM 默认值解析。"""

from __future__ import annotations

import os
from pathlib import Path


def load_env_defaults(path: str = ".env") -> dict[str, str]:
    """解析 .env 文件，返回 key-value 字典。不存在时返回空 dict。"""
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


def get_llm_default(key: str, fallback: str = "", *, env_defaults: dict[str, str] | None = None) -> str:
    """依次从 os.environ、env_defaults 中取值，都没有则返回 fallback。"""
    val = os.getenv(key)
    if val:
        return val
    if env_defaults:
        val = env_defaults.get(key, "")
        if val:
            return val
    return fallback
