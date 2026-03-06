# Tutorial_retriever

## 1. 模块作用（What）

`retriever` 模块负责根据用户 query 从向量库召回最相关的 Top-k chunks。

## 2. 设计思路（Why）

- RAG 的关键是"先找对上下文，再生成答案"。
- 检索与生成解耦，便于独立调参（Top-k、相似度阈值、重排序）。
- 召回结果需保留来源信息（source/page）用于可追溯输出。
- query 嵌入必须与索引使用相同的 embedding 后端，否则在不同语义空间比较毫无意义。

## 3. 核心实现（How）

当前状态：**已实现（Phase 3 + Phase 8 性能升级）**。核心接口：

- `retrieve_top_k(query, store, top_k=5, faiss_index=None) -> list[dict]`

关键点：

- 读取 `store.backend`，用相同后端将 query 向量化（保证语义空间一致）
- 维度不匹配防护：若 query 向量维度 ≠ 实际存储向量维度，立即报错并提示 `--force-rebuild`
- 有 `faiss_index` 时优先走 FAISS 检索；否则回退到 **numpy 矩阵运算**（`mat @ q`）
- 返回结果包含 `index/score/text/source/page`

## 4. 数据流（Data Flow）

```
query
  → embed_text(dim=store.dim, backend=store.backend)   # 与索引同后端
  → (dim mismatch check)
  → (faiss search | numpy mat @ q)
  → argsort → Top-k chunks + score
  → prompt builder
```

## 5. 模块关系（上下游）

- 上游：`embedding` 模块产出的 `VectorStore`（含 `backend` 字段）
- 下游：`prompt` 模块将 query + contexts 组装提示词

## 6. 接口细节（Inputs / Outputs）

- **函数**：`retrieve_top_k(query, store, top_k=5, faiss_index=None) -> list[dict]`
- **输入**：
  - `query: str`
  - `store: VectorStore`（需含 `backend` 字段）
  - `top_k: int`
  - `faiss_index`：可选索引
- **输出字段**（每条）：
  - `index`, `score`, `text`, `source`, `page`

## 7. 调参建议

- `top_k=1`：答案更聚焦、速度更快
- `top_k=3~5`：召回更全，但可能引入噪声
- 若回答"答非所问"：
  - 先检查 embedding backend（ST > hash）
  - 再减小 `top_k`
  - 再观察 `chunk_size/overlap`
- 若出现维度不匹配错误：运行 `--force-rebuild` 重建向量缓存

## 8. 异常与边界行为

- `top_k <= 0`：抛 `ValueError`
- 空 query：返回空列表，不进入后续阶段
- `store` 为空：返回空列表，不进入生成阶段
- query 向量维度 ≠ 存储向量维度：抛 `ValueError`，提示 `--force-rebuild`

## 9. 测试映射

- 对应：`tests/test_retriever.py`
- 覆盖点：
  - 正常 Top-k 排序（hash backend，显式指定）
  - 空 query/空 store
  - 非法 `top_k`
  - 维度不匹配报错
  - FAISS 路径（skipif 无 faiss）

## 10. 技术栈

- `Python 3`：检索逻辑编排
- `numpy`：矩阵运算加速暴力检索（`mat @ q` + `argsort`）
- `embedding.embed_text(backend=store.backend)`：Query 向量化（与索引同后端）
- `FAISS`（可选）：向量近邻搜索

## 11. 端到端流程（这一部分如何工作）

1. 输入 `query + VectorStore + top_k`
2. 读取 `store.backend`，用相同后端将 `query` 向量化
3. 维度检查：`len(qvec) != len(store.vectors[0])` → 报错
4. 选择检索路径：
   - 有 `faiss_index` → `search_faiss()`
   - 无索引 → numpy 矩阵运算：`scores = mat @ q`，`argsort` 取 Top-k
5. 组装输出字段：`index/score/text/source/page`

## 12. 核心函数在做什么，为什么这样做

- `retrieve_top_k()`：
  - **做什么**：返回与 query 最相关的上下文片段
  - **为什么**：RAG 质量首先取决于"检索到什么"，而不是"生成模型多强"
- numpy 矩阵运算路径（`mat @ q`）：
  - **做什么**：将所有存储向量组成矩阵，与 query 向量做矩阵乘法，一次性得到所有 chunk 的相似度分数
  - **为什么**：相较于旧版纯 Python 逐元素循环，numpy 依赖底层 BLAS 向量化指令，批量检索速度快 10-100x
- 维度不匹配检测：
  - **做什么**：比对 query 向量长度与实际存储向量长度
  - **为什么**：切换 embedding backend 后旧缓存向量维度不同（如 256 → 384），若不检测会导致矩阵乘法静默失败或错误结果
