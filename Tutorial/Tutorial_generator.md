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
