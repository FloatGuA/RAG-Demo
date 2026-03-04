# Tutorial_prompt

## 1. 模块作用（What）

`prompt` 模块负责将用户问题和检索到的上下文拼装为可控的 LLM 输入。

## 2. 设计思路（Why）

- 同样的上下文，不同 prompt 会显著影响答案质量。
- 需要明确“仅基于 context 回答”，降低幻觉风险。
- 统一 prompt 模板便于测试、回归与调优。

## 3. 核心实现（How）

当前状态：**已实现（Phase 3）**。核心接口：

- `build_prompt(query: str, contexts: list[dict], max_context_chars: int = 4000) -> str`

当前模板包含：

- 系统约束（仅用 context）
- 不确定时输出 "I don't know"
- context 结构化块（含 source/page）

## 4. 数据流（Data Flow）

`query + retrieved chunks -> prompt template -> final prompt string`

## 5. 模块关系（上下游）

- 上游：`retriever` 模块输出 Top-k chunks
- 下游：`generator` 模块消费 prompt 调用 LLM

## 6. 接口细节（Inputs / Outputs）

- **函数**：`build_prompt(query, contexts, max_context_chars=4000)`
- **输入**：
  - `query: str` 用户问题
  - `contexts: list[dict]` 检索结果列表（通常含 `text/source/page`）
  - `max_context_chars: int` 上下文截断预算
- **输出**：
  - `str` 完整 prompt 文本（包含系统约束、问题、上下文块）

## 7. 关键参数建议

- `max_context_chars`
  - 调试期建议 `1500~3000`，便于观察 prompt 变化
  - 线上可提升到 `3000~6000`，平衡召回信息与请求时延
- `contexts` 条数通常与 `top_k` 对齐，建议先从 `1~3` 起步

## 8. 边界行为与常见问题

- `max_context_chars <= 0` 会抛 `ValueError`
- 空 `contexts` 时会写入 `[No context retrieved]`，并保留 `I don't know` 约束
- 若回答幻觉增多，优先检查：
  - 是否保留了 “ONLY based on context”
  - `top_k` 是否过高导致噪声上下文过多

## 9. 测试映射

- 对应测试文件：`tests/test_prompt.py`
- 重点覆盖：
  - query/context 组装正确
  - 空 contexts 的回退语义
  - 参数校验（`max_context_chars`）

## 10. 技术栈

- `Python 3`：模板拼接与上下文截断
- 字符串模板策略：控制 LLM 行为（grounded generation）
- 结构化 `contexts` 输入：保留 `source/page` 便于追溯

## 11. 端到端流程（这一部分如何工作）

1. 输入 `query` 与 `retriever` 返回的 `contexts`  
2. 按顺序拼接 `[Context i] source=..., page=...`  
3. 根据 `max_context_chars` 执行上下文预算截断  
4. 注入系统约束：
   - 仅基于 context 回答
   - 信息不足必须返回 `I don't know`  
5. 输出最终 prompt 字符串给 `generator`

## 12. 核心函数在做什么，为什么这样做

- `build_prompt()`：
  - **做什么**：把“问题 + 证据”转换成 LLM 可执行指令
  - **为什么**：直接把 query 喂给模型容易幻觉，必须显式加边界与证据格式
