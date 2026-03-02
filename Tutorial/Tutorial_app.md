# Tutorial_app

## 1. 模块作用（What）

`app.py` + `web_app.py` 提供应用层入口：前者是 CLI，后者是对话框式 Web UI。

## 2. 设计思路（Why）

- 先用 CLI 交付最小可用，再用 Streamlit 快速扩展对话框体验。
- 复用已实现模块，避免在 UI 层重复实现检索/生成逻辑。
- 兼容多 provider LLM 配置（local/openai/openai_compatible）。

## 3. 核心实现（How）

- `app.py`
  - `build_runtime()`：复用 `main.py` 缓存逻辑，加载向量与索引
  - `answer_with_store()`：串联 `retrieve -> prompt -> generate -> format`
  - `run_single_query()` / `run_interactive()`：CLI 单次与 REPL 模式
- `web_app.py`
  - 使用 Streamlit `chat_input` / `chat_message` 构建气泡对话界面
  - 侧边栏配置 `top_k/provider/model/temperature` 等参数
  - 通过 `session_state` 管理会话历史，支持清空对话

## 4. 数据流（Data Flow）

`UI input (CLI/Web) -> runtime(cache) -> retrieve -> prompt -> generator -> formatter -> Answer + Sources`

## 5. 模块关系（上下游）

- 上游：`main.py`（缓存加载函数）、`retriever.py`、`prompt.py`、`generator.py`
- 下游：用户交互与最终展示（CLI 文本输出 / Web 对话气泡）
