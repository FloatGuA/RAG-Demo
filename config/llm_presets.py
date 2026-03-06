"""
LLM 预置配置：从 llm_presets.json 加载各 Provider 的 base_url / models 等。
Web 与 CLI 共用，前端选择哪个 Provider 即加载对应参数。
"""

from __future__ import annotations

import json
from pathlib import Path

_DEFAULT_PATH = Path(__file__).resolve().parent.parent / "llm_presets.json"

DEFAULT_PRESETS = {
    "default_provider": "openai_compatible",
    "providers": {
        "local": {"base_url": "", "timeout_sec": 120, "models": ["local-fallback"]},
        "ollama": {
            "base_url": "http://localhost:11434/v1",
            "timeout_sec": 120,
            "models": ["qwen3:8b"],
        },
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


def load_llm_presets(path: str | Path | None = None) -> dict:
    """加载 llm_presets.json，不存在则返回内置默认。"""
    p = Path(path) if path else _DEFAULT_PATH
    if not p.exists():
        return DEFAULT_PRESETS.copy()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_PRESETS.copy()
    if not isinstance(data, dict) or "providers" not in data:
        return DEFAULT_PRESETS.copy()
    providers = data.get("providers")
    if not isinstance(providers, dict) or not providers:
        return DEFAULT_PRESETS.copy()
    return data


def get_provider_options(presets: dict) -> list[str]:
    """返回可用的 Provider 名称列表。"""
    providers = presets.get("providers", {})
    if not isinstance(providers, dict):
        return list(DEFAULT_PRESETS["providers"].keys())
    options = list(providers.keys())
    return options or list(DEFAULT_PRESETS["providers"].keys())


def get_models_for_provider(presets: dict, provider: str) -> list[str]:
    """返回指定 Provider 下的可选模型列表。"""
    providers = presets.get("providers", {})
    info = providers.get(provider, {}) if isinstance(providers, dict) else {}
    models = info.get("models", []) if isinstance(info, dict) else []
    if not isinstance(models, list) or not models:
        return ["local-fallback"] if provider == "local" else ["gpt-4o-mini"]
    return [str(m) for m in models]


def get_default_base_url(presets: dict, provider: str) -> str:
    """返回指定 Provider 的默认 base_url。"""
    providers = presets.get("providers", {})
    info = providers.get(provider, {}) if isinstance(providers, dict) else {}
    base_url = info.get("base_url", "") if isinstance(info, dict) else ""
    return str(base_url)


def get_default_timeout(presets: dict, provider: str) -> float:
    """返回指定 Provider 的默认 timeout（秒）。"""
    providers = presets.get("providers", {})
    info = providers.get(provider, {}) if isinstance(providers, dict) else {}
    timeout_sec = info.get("timeout_sec", 120) if isinstance(info, dict) else 120
    try:
        val = float(timeout_sec)
    except (TypeError, ValueError):
        return 120.0
    return val if val > 0 else 120.0


def get_default_model(presets: dict, provider: str) -> str:
    """返回指定 Provider 的默认模型（首个）。"""
    models = get_models_for_provider(presets, provider)
    return models[0] if models else "gpt-4o-mini"
