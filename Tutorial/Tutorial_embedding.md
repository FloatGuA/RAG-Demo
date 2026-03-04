# Tutorial_embedding

## 1. 模块作用（What）

`embedding` 模块负责将 `Chunk` 文本转换为向量，并构建可检索的向量索引（如 FAISS）。

## 2. 设计思路（Why）

- 语义检索需要向量空间相似度，而非关键词精确匹配。
- embedding 与索引独立，便于替换模型或向量库。
- 需要持久化向量结果，避免重复计算。

## 3. 核心实现（How）

当前状态：**已实现（Phase 2）**。核心接口：

- `embed_text(text, dim=256)`：哈希 BoW + L2 归一化向量化
- `build_vector_store(chunks, dim=256)`：构建 `VectorStore(dim, vectors, metadata)`
- `save_vectors(store, path)` / `load_vectors(path)`：向量 JSON 持久化
- `build_faiss_index(store)` / `search_faiss(index, query_vector, top_k)`：FAISS 索引与检索
- `save_faiss_index(index, path)` / `load_faiss_index(path)`：FAISS 索引持久化
- `has_faiss()`：检测环境是否可用 FAISS（不可用时主流程优雅降级）

默认路径：

- `artifacts/vectors/`：向量数据
- `artifacts/index/`：索引数据

## 4. 数据流（Data Flow）

`List[Chunk] -> embed_text/build_vector_store -> vectors(json) -> (optional) faiss index -> artifacts 持久化`

## 5. 模块关系（上下游）

- 上游：`chunking.py` 的 `List[Chunk]` 或 `chunks.json`
- 下游：
  - 当前：`main.py` 统一编排 offline pipeline
  - 后续：`retriever.py` 使用 vectors/faiss 执行 Top-k 召回

## 6. 接口细节（Inputs / Outputs）

- `embed_text(text, dim)`：`str -> list[float]`
- `build_vector_store(chunks, dim)`：`list[dict] -> VectorStore`
- `build_faiss_index(store)`：`VectorStore -> faiss index`
- `search_faiss(index, query_vector, top_k)`：返回 `(idx, score)` 列表

## 7. 关键参数建议

- `dim`：
  - 开发调试建议 `64~256`
  - 线上可用 `256+`（结合性能预算）
- `top_k`：
  - 先从 `1~3` 起步观察回答质量

## 8. 异常与边界行为

- `dim <= 0`：抛 `ValueError`
- 无 `faiss` 依赖时调用索引能力：抛 `RuntimeError`
- 向量文件不存在：`FileNotFoundError`

## 9. 测试映射

- 对应：`tests/test_embedding.py`
- 覆盖点：
  - 向量维度/可复现性
  - 向量持久化一致性
  - FAISS 可用/不可用两条路径

## 10. 技术栈

- `Python 3`：Embedding 与索引调度
- `numpy`：向量数组与数值计算
- `zlib.crc32`：轻量哈希特征映射（BoW）
- `faiss-cpu`（可选）：高效近邻检索索引
- `json`：向量存储持久化

## 11. 端到端流程（这一部分如何工作）

1. 输入 `List[Chunk]`（或 `chunks` 字典）  
2. `embed_text()` 将文本映射到固定维度向量  
3. `build_vector_store()` 聚合为 `VectorStore(vectors, metadata)`  
4. 保存到 `artifacts/vectors/vectors.json`  
5. 若环境支持 FAISS，构建/加载 `artifacts/index/faiss.index`  
6. 输出给 `retriever` 执行 Top-k 检索

## 12. 核心函数在做什么，为什么这样做

- `embed_text()`：
  - **做什么**：把任意文本变成固定维度向量并归一化
  - **为什么**：让后续相似度计算可比较、可复现
- `build_vector_store()`：
  - **做什么**：批量向量化并绑定元数据
  - **为什么**：检索时要同时返回 `text/source/page`，不能只有向量
- `build_faiss_index()/search_faiss()`：
  - **做什么**：可选地使用 FAISS 加速近邻搜索
  - **为什么**：数据量增大时，纯 Python 排序性能会成为瓶颈
