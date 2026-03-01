"""
Chunk 持久化模块（JSON）
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List


def save_chunks(chunks: List[dict], path: str) -> None:
    """
    将 chunks 保存到 JSON 文件（可读性优先）。

    Args:
        chunks: List[dict]
        path: 目标文件路径
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)

    with target.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)


def load_chunks(path: str) -> List[dict]:
    """
    从 JSON 文件加载 chunks。

    Args:
        path: chunks 文件路径

    Returns:
        List[dict]
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"chunks 文件不存在: {target}")

    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"chunks 文件格式错误，期望 list，实际: {type(data).__name__}")
    return data
