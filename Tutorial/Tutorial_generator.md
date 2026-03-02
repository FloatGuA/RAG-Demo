# Tutorial_generator

## 1. 模块作用（What）

`generator` 模块负责调用 LLM，根据 prompt 生成最终答案。

## 2. 设计思路（Why）

- 生成逻辑应与检索逻辑解耦，便于替换模型/API。
- 统一输出结构便于后续 formatter/UI 使用。
- 需要可配置参数（temperature、max tokens）以平衡稳定性与创造性。

## 3. 核心实现（How）

当前状态：**待实现**。建议实现以下接口：

- `generate(prompt: str) -> str`
- 可扩展：`generate_with_meta(prompt: str) -> dict`

建议输出：

- `answer` 文本
- （可选）模型名、token 消耗、耗时等元信息

## 4. 数据流（Data Flow）

`prompt string -> LLM API / local model -> answer`

## 5. 模块关系（上下游）

- 上游：`prompt` 模块构建的 prompt
- 下游：`response formatter` / `app UI` 展示答案与来源
