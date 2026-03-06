""".env 文件加载与 LLM 默认值解析。"""

from __future__ import annotations

import os
from pathlib import Path


class EnvNotFoundError(FileNotFoundError):
    """环境配置文件缺失。"""


def load_env_defaults(path: str | None = None) -> dict[str, str]:
    """解析 .env 文件，返回 key-value 字典。文件不存在时抛出 EnvNotFoundError 并提示创建方式。"""
    p = Path(path) if path else Path(".env")
    if not p.exists():
        raise EnvNotFoundError(
            f"环境配置文件不存在: {p}\n"
            "请在项目根目录创建 .env 文件，参考格式：\n"
            "  OPENAI_API_KEY=your_key_here\n"
            "  LLM_PROVIDER=ollama"
        )
    values: dict[str, str] = {}
    _parse_env_file(p, values)
    return values


def _parse_env_file(path: Path, out: dict[str, str]) -> None:
    """解析 .env 格式文件，结果写入 out。"""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            out[key] = value


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
