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
