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

## 6. 接口细节（Inputs / Outputs）

- **函数**：`retrieve_top_k(query, store, top_k=5, faiss_index=None) -> list[dict]`
- **输入**：
  - `query: str`
  - `store: VectorStore`
  - `top_k: int`
  - `faiss_index`: 可选索引
- **输出字段**（每条）：
  - `index`, `score`, `text`, `source`, `page`

## 7. 调参建议

- `top_k=1`：答案更聚焦、速度更快
- `top_k=3~5`：召回更全，但可能引入噪声
- 若回答“答非所问”：
  - 先减小 `top_k`
  - 再观察 `chunk_size/overlap`

## 8. 异常与边界行为

- `top_k <= 0`：抛 `ValueError`
- 空 query：通常返回空结果
- `store` 为空：返回空结果，不进入生成阶段

## 9. 测试映射

- 对应：`tests/test_retriever.py`
- 覆盖点：
  - 正常 Top-k 排序
  - 空 query/空 store
  - 非法 `top_k`
  - FAISS 与非 FAISS 路径一致性

## 10. 技术栈

- `Python 3`：检索逻辑编排
- `embedding.embed_text()`：Query 向量化
- `FAISS`（可选）：向量近邻搜索
- 纯 Python 向量内积：FAISS 不可用时的回退路径

## 11. 端到端流程（这一部分如何工作）

1. 输入 `query + VectorStore + top_k`  
2. 将 `query` 向量化到与文档同维度  
3. 选择检索路径：
   - 有 `faiss_index` -> `search_faiss()`
   - 无索引 -> 向量内积排序  
4. 截取 Top-k 结果  
5. 组装输出字段：`score/text/source/page`

## 12. 核心函数在做什么，为什么这样做

- `retrieve_top_k()`：
  - **做什么**：返回与 query 最相关的上下文片段
  - **为什么**：RAG 质量首先取决于“检索到什么”，而不是“生成模型多强”
- `_dot()`：
  - **做什么**：计算两个向量的点积相似度
  - **为什么**：作为无 FAISS 时的稳定回退，保证功能可用性
