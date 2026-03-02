"""
模块6：LLM Generator
统一 LLM 调用入口，支持：
1) local 占位实现（离线可运行）
2) openai 官方 API
3) openai_compatible（兼容 OpenAI 协议的第三方/本地服务）
"""

from __future__ import annotations

import os
import re
import time

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - 依赖可能未安装
    OpenAI = None  # type: ignore


def _first_sentence(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return ""
    parts = re.split(r"(?<=[.!?。！？])\s+", cleaned, maxsplit=1)
    return parts[0].strip()


def _local_fallback_answer(contexts: list[dict] | None) -> str:
    if not contexts:
        return "I don't know"
    first = contexts[0].get("text", "")
    sentence = _first_sentence(str(first))
    if not sentence:
        return "I don't know"
    return sentence


def _load_dotenv_if_present(path: str = ".env") -> None:
    """
    轻量读取 .env（仅加载当前进程尚未设置的变量）。
    不依赖 python-dotenv，避免引入额外耦合。
    """
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        # 读取失败时静默跳过，避免影响主流程
        return


def _resolve_provider(provider: str | None, use_openai: bool) -> str:
    if provider:
        resolved = provider.strip().lower()
    else:
        resolved = "openai" if use_openai else "local"
    allowed = {"local", "openai", "openai_compatible"}
    if resolved not in allowed:
        raise ValueError(f"不支持的 provider: {resolved}，可选: {sorted(allowed)}")
    return resolved


def _call_openai_chat(
    *,
    prompt: str,
    model: str,
    temperature: float,
    api_key: str | None,
    base_url: str | None,
    timeout: float,
):
    if OpenAI is None:
        raise RuntimeError("未安装 openai 依赖，请先执行: python -m pip install openai")

    client_kwargs: dict = {"api_key": api_key or "DUMMY_KEY_FOR_LOCAL", "timeout": timeout}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = OpenAI(**client_kwargs)
    return client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=[
            {"role": "system", "content": "You are a helpful course assistant."},
            {"role": "user", "content": prompt},
        ],
    )


def generate_answer(
    prompt: str,
    contexts: list[dict] | None = None,
    *,
    provider: str | None = None,
    use_openai: bool = False,
    model: str = "gpt-4o-mini",
    temperature: float = 0.2,
    base_url: str | None = None,
    api_key: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    timeout: float = 30.0,
    max_retries: int = 1,
    fallback_to_local: bool = True,
) -> str:
    """
    统一回答生成入口（可插拔 provider）。

    provider:
    - local: 本地占位生成（无网络）
    - openai: OpenAI 官方 API
    - openai_compatible: 兼容 OpenAI 协议的 API（可用于本地服务）
    """
    if not contexts:
        return "I don't know"

    chosen_provider = _resolve_provider(provider, use_openai)
    if chosen_provider == "local":
        _ = prompt
        return _local_fallback_answer(contexts)

    if max_retries < 0:
        raise ValueError("max_retries 不能小于 0")
    if timeout <= 0:
        raise ValueError("timeout 必须为正数")

    _load_dotenv_if_present()
    resolved_key = api_key or os.getenv(api_key_env) or os.getenv("OPENAI_API_KEY")
    if chosen_provider == "openai" and not resolved_key:
        if fallback_to_local:
            return _local_fallback_answer(contexts)
        raise RuntimeError(f"未检测到 API Key，请设置环境变量: {api_key_env}")

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = _call_openai_chat(
                prompt=prompt,
                model=model,
                temperature=temperature,
                api_key=resolved_key,
                base_url=base_url,
                timeout=timeout,
            )
            content = resp.choices[0].message.content or ""
            normalized = content.strip()
            return normalized or "I don't know"
        except Exception as exc:  # pragma: no cover - 依赖外部网络/服务
            last_error = exc
            if attempt < max_retries:
                time.sleep(min(0.5 * (2**attempt), 2.0))
                continue
            if fallback_to_local:
                return _local_fallback_answer(contexts)
            raise RuntimeError(f"LLM 调用失败（provider={chosen_provider}）: {exc}") from exc

    # 理论上不会到达，作为防御性返回
    if last_error is not None and not fallback_to_local:
        raise RuntimeError(f"LLM 调用失败: {last_error}") from last_error
    return _local_fallback_answer(contexts)
