# Tutorial_retriever

## 1. 模块作用（What）

`retriever` 模块负责根据用户 query 从向量库召回最相关的 Top-k chunks。

## 2. 设计思路（Why）

- RAG 的关键是“先找对上下文，再生成答案”。
- 检索与生成解耦，便于独立调参（Top-k、相似度阈值、重排序）。
- 召回结果需保留来源信息（source/page）用于可追溯输出。

## 3. 核心实现（How）

当前状态：**已实现（Phase 3）**。核心接口：

- `retrieve_top_k(query, store, top_k=5, faiss_index=None) -> list[dict]`

关键点：

- query embedding 与文档 embedding 复用 `embedding.embed_text`
- 有 `faiss_index` 时优先走 FAISS 检索；否则回退到纯 Python 向量内积排序
- 返回结果包含 `index/score/text/source/page`

## 4. 数据流（Data Flow）

`query -> query embedding -> (faiss search | dot-product ranking) -> Top-k chunks(+score) -> prompt builder`

## 5. 模块关系（上下游）

- 上游：`embedding` 模块产出的向量索引
- 下游：`prompt` 模块将 query + contexts 组装提示词
