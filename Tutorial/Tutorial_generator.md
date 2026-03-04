# Tutorial_generator

## 1. 模块作用（What）

`generator` 模块负责调用 LLM，根据 prompt 生成最终答案。

## 2. 设计思路（Why）

- 生成逻辑应与检索逻辑解耦，便于替换模型/API。
- 统一输出结构便于后续 formatter/UI 使用。
- 需要可配置参数（temperature、max tokens）以平衡稳定性与创造性。

## 3. 核心实现（How）

当前状态：**已实现可插拔版本（Phase 3）**。核心接口：

- `generate_answer(prompt, contexts, provider, model, base_url, timeout, max_retries, fallback_to_local)`

当前行为：

- 无上下文：返回 `I don't know`
- `provider=local`：返回首条 context 的首句（离线联调）
- `provider=openai`：调用 OpenAI 官方 API
- `provider=openai_compatible`：调用兼容 OpenAI 协议的第三方/本地服务
- 支持 `.env` 自动读取与调用失败回退（可关闭回退）

## 4. 数据流（Data Flow）

`prompt string -> LLM API / local model -> answer`

## 5. 模块关系（上下游）

- 上游：`prompt` 模块构建的 prompt
- 下游：`response formatter` / `app UI` 展示答案与来源

## 6. 接口细节（Inputs / Outputs）

- 推荐主接口：`generate_answer_with_meta(...) -> tuple[str, dict]`
- 兼容接口：`generate_answer(...) -> str`
- 关键输入：
  - `provider`: `local` / `openai` / `openai_compatible`
  - `model`, `base_url`, `timeout`, `max_retries`
  - `fallback_to_local`: 远程失败是否回退本地
- 元信息（meta）常见字段：
  - `used_remote_llm`, `provider`, `actual_provider`, `model`
  - `attempts`, `fallback_triggered`, `error`

## 7. 超时与重试语义

- `timeout` 是**总预算**（跨重试累计），不是单次请求无限叠加
- `max_retries=0` 表示仅尝试 1 次
- 为避免 SDK 隐式重试，内部显式控制重试策略

## 8. 常见错误与处理建议

- `model_not_found`：模型名拼写/大小写错误，先核对预置配置
- `AccessDenied.Unpurchased`：账号无模型权限，需开通或切模型
- `LLM 调用超时（总预算）`：先降 `top_k`、提 `timeout`、减重试
- 生产环境建议关闭明文 key，统一走环境变量与 `.env`

## 9. 测试映射

- 对应：`tests/test_generator.py`
- 覆盖点：
  - 本地 provider 输出
  - 远程 provider 参数分发
  - 错误回退与禁用回退路径
  - 元信息字段完整性

## 10. 技术栈

- `Python 3`：Provider 抽象与容错逻辑
- `openai` SDK：OpenAI 与 OpenAI-compatible 调用
- `.env` 解析：本地配置读取（无额外依赖）
- 指数退避重试 + 总超时预算：稳定性保障

## 11. 端到端流程（这一部分如何工作）

1. 输入 `prompt + contexts + provider 配置`  
2. 若 `contexts` 为空，直接返回 `I don't know`  
3. 根据 `provider` 选择执行路径：
   - `local`：本地占位逻辑
   - `openai/openai_compatible`：远程 API 调用  
4. 在总超时预算内进行重试  
5. 失败时按 `fallback_to_local` 决定是否回退  
6. 输出 `answer`（可选 `meta` 调试信息）

## 12. 核心函数在做什么，为什么这样做

- `generate_answer_with_meta()`：
  - **做什么**：统一生成入口并返回可观测元数据
  - **为什么**：方便 UI 与评估定位问题（超时、回退、失败原因）
- `_call_openai_chat()`：
  - **做什么**：封装 SDK 调用细节
  - **为什么**：把网络层与业务层分离，便于测试和替换
- `_local_fallback_answer()`：
  - **做什么**：本地占位回答策略
  - **为什么**：离线联调和远程失败兜底都需要稳定可用路径
