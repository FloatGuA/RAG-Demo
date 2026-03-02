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
