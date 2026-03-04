# Tutorial_app

## 1. 模块作用（What）

`app.py` + `web_app.py` 提供应用层入口：前者是 CLI，后者是对话框式 Web UI。

## 2. 设计思路（Why）

- 先用 CLI 交付最小可用，再用 Streamlit 快速扩展对话框体验。
- 核心业务逻辑已提取到 `pipeline/` 包，UI 层仅负责 IO 与参数解析。
- 兼容多 provider LLM 配置（local/openai/openai_compatible）。
- Phase 6 新增了统一 CLI 入口 `cli.py`（typer），旧入口 `app.py` 仍可用。

## 3. 核心实现（How）

- `app.py`（旧 CLI 入口，从 `pipeline` 导入核心函数）
  - `run_single_query()` / `run_interactive()`：CLI 单次与 REPL 模式
  - 核心逻辑 `answer_with_store()` / `build_runtime()` / `render_response()` 已移至 `pipeline/`
- `web_app.py`
  - 使用 Streamlit `chat_input` / `chat_message` 构建气泡对话界面
  - 侧边栏配置 `top_k/provider/model/temperature` 等参数
  - 通过 `session_state` 管理会话历史，支持清空对话

## 4. 数据流（Data Flow）

`UI input (CLI/Web) -> runtime(cache) -> retrieve -> prompt -> generator -> formatter -> Answer + Sources`

## 5. 模块关系（上下游）

- 上游：`pipeline/`（核心管线：`build_runtime` / `answer_with_store` / `render_response`）
- 上游：`config/`（共享配置）
- 下游：用户交互与最终展示（CLI 文本输出 / Web 对话气泡）

## 6. CLI 与 Web 的职责边界

- `cli.py`（推荐）：统一入口，子命令 `build/query/chat/eval/web`
- `app.py`（旧入口）：脚本化联调、快速验收、日志可控
- `web_app.py`：交互演示、参数可视化、会话态展示
- 三者都从 `pipeline` 导入 `answer_with_store()`，保证行为一致

## 7. Web 配置联动说明

- Provider 变化会驱动可选 Model 与默认 Base URL
- 预置来源：`llm_presets.json`
- Provider 为 `local` 时，Base URL 输入会隐藏
- Debug 信息统一放在可折叠区域，避免正文重复
- 支持 `Min relevance score`：低于阈值的检索结果会被过滤，用于抑制“无关上下文误答”

## 8. 常见问题排查

- UI 改了模型但没生效：
  - 先看 Debug 里的 `请求 Provider/模型`
  - 再看 `是否使用大模型` 与 `实际使用 Provider`
- 会话是否记忆同问同答：
  - 当前默认不做“问答缓存命中复用”，每次都会重新检索与生成
  - 仅保留会话历史用于展示，不直接复用旧答案
- 明显越界问题没有返回 `I don't know`：
  - 先提高 `Min relevance score`（如 `0.15 ~ 0.30`）
  - 再观察 Debug 中 `best_retrieval_score` 与 `relevance_filter_triggered`

## 9. 测试映射

- 对应：`tests/test_app.py`、`tests/test_web_app.py`
- 覆盖点：
  - CLI 组装与渲染
  - Web 工具函数（时间戳、debug 格式化、预置读取）

## 10. 技术栈

- `argparse`：CLI 运行参数
- `streamlit`：Web 对话 UI
- `session_state`：多轮会话状态
- 项目内模块复用：`retrieve/prompt/generator/formatter`

## 11. 端到端流程（这一部分如何工作）

1. UI 接收用户问题与配置参数（Top-k、Provider、阈值等）  
2. `build_runtime()` 加载/构建向量与索引  
3. `answer_with_store()` 执行完整链路：
   - 检索
   - 低相关过滤（可选）
   - Prompt 构建
   - 生成
   - 格式化  
4. 输出 Answer + Sources + Debug（可选）

## 12. 核心函数在做什么，为什么这样做

- `answer_with_store()`：
  - **做什么**：应用层统一问答入口
  - **为什么**：让 CLI/Web/Evaluation 共用一套业务逻辑，避免行为漂移
- `render_response()` / `build_assistant_message()`：
  - **做什么**：把结构化结果渲染成用户可读文本
  - **为什么**：展示层与业务层解耦，便于替换 UI
- `format_debug_lines()`：
  - **做什么**：统一调试信息输出格式
  - **为什么**：联调时快速定位 provider/检索/回退问题
