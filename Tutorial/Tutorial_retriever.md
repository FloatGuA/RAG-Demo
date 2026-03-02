# Tutorial_retriever

## 1. 模块作用（What）

`retriever` 模块负责根据用户 query 从向量库召回最相关的 Top-k chunks。

## 2. 设计思路（Why）

- RAG 的关键是“先找对上下文，再生成答案”。
- 检索与生成解耦，便于独立调参（Top-k、相似度阈值、重排序）。
- 召回结果需保留来源信息（source/page）用于可追溯输出。

## 3. 核心实现（How）

当前状态：**待实现**。建议实现以下接口：

- `retrieve(query: str, top_k: int = 5) -> list[Chunk]`
- `retrieve_with_scores(query: str, top_k: int = 5) -> list[tuple[Chunk, float]]`

关键点：

- query embedding 与文档 embedding 使用同一模型
- 先 ANN 召回，再按需做 rerank（可选）
- 返回结果含 `text/source/page`

## 4. 数据流（Data Flow）

`query -> query embedding -> vector search -> Top-k chunks(+score) -> prompt builder`

## 5. 模块关系（上下游）

- 上游：`embedding` 模块产出的向量索引
- 下游：`prompt` 模块将 query + contexts 组装提示词
