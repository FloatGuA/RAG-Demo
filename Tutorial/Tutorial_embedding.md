# Tutorial_embedding

## 1. 模块作用（What）

`embedding` 模块负责将 `Chunk` 文本转换为向量，并构建可检索的向量索引（如 FAISS）。

## 2. 设计思路（Why）

- 语义检索需要向量空间相似度，而非关键词精确匹配。
- embedding 与索引独立，便于替换模型或向量库。
- 需要持久化向量结果，避免重复计算。
- `VectorStore` 记录建索引时使用的 backend，确保检索时 query 与文档在同一语义空间比较。

## 3. 核心实现（How）

当前状态：**已实现（Phase 2 + Phase 8 升级）**。核心接口：

- `embed_text(text, dim=256, *, backend="auto")`：将文本编码为向量
  - `backend="auto"`（默认）：优先 sentence-transformers，未安装时自动降级 hash，离线可用
  - `backend="sentence_transformers"`：语义嵌入，all-MiniLM-L6-v2，输出 384-dim，未安装时报错
  - `backend="hash"`：哈希 BoW + L2 归一化，dim 参数有效
- `has_sentence_transformers()`：检测环境是否可用 sentence-transformers
- `build_vector_store(chunks, dim=256, *, backend="auto")`：构建 `VectorStore`，自动检测实际 dim；backend 透传自 `pipeline/build.py`，可通过 `DEFAULT_EMBED_BACKEND` 统一配置
- `save_vectors(store, path)` / `load_vectors(path)`：向量持久化
  - 保存格式：**numpy npz 压缩**（`.npz`），相比旧 JSON 加载快 5-10x、体积缩小 3-5x
  - 加载时自动检测后缀：`.npz` 走 numpy 路径，`.json` 走旧 JSON 路径（向后兼容）
- `build_faiss_index(store)` / `search_faiss(index, query_vector, top_k)`：FAISS 索引与检索
- `save_faiss_index(index, path)` / `load_faiss_index(path)`：FAISS 索引持久化
- `has_faiss()`：检测环境是否可用 FAISS（不可用时主流程优雅降级）

默认路径：

- `artifacts/vectors/`：向量数据
- `artifacts/index/`：索引数据

## 4. 数据流（Data Flow）

```
List[Chunk]
  → embed_text(backend="auto")        # ST 或 hash，自动选择
  → build_vector_store()              # 聚合为 VectorStore(dim, vectors, metadata, backend)
  → save_vectors()                    # 持久化 npz（含 backend 字段，自动压缩）
  → (optional) build_faiss_index()    # 构建 FAISS 索引
  → artifacts 持久化
```

## 5. 模块关系（上下游）

- 上游：`ingestion/chunking.py` 的 `List[Chunk]` 或 `chunks.json`
- 下游：
  - `pipeline/build.py` 编排 offline 构建
  - `retrieval/retriever.py` 使用 `store.backend` 保持 query embedding 一致性

## 6. 接口细节（Inputs / Outputs）

- `embed_text(text, dim, *, backend)` → `list[float]`
  - hash backend：长度 = `dim`
  - sentence_transformers backend：长度固定 = 384（忽略 `dim` 参数）
- `build_vector_store(chunks, dim, *, backend)` → `VectorStore`
  - `store.dim` = 实际向量长度（由首个向量决定，可能与入参 `dim` 不同）
  - `store.backend` = resolved backend（"sentence_transformers" 或 "hash"）
- `build_faiss_index(store)` → faiss index
- `search_faiss(index, query_vector, top_k)` → `list[tuple[int, float]]`

## 7. 关键参数建议

- `backend`：
  - 生产/演示环境安装 `sentence-transformers` 并使用 `auto`（默认）
  - 无网络/纯离线环境使用 `hash`
- `dim`（仅 hash backend 有效）：
  - 调试建议 `64~256`
  - 切换后端后需 `--force-rebuild`

## 8. 异常与边界行为

- `dim <= 0`（hash backend）：抛 `ValueError`
- 无 `faiss` 依赖时调用索引能力：抛 `RuntimeError`
- 向量文件不存在：`FileNotFoundError`
- 切换 backend 后使用旧缓存（维度不匹配）：`retrieve_top_k` 会捕获并提示 `--force-rebuild`

## 9. 测试映射

- 对应：`tests/test_embedding.py`
- 覆盖点：
  - hash backend 向量维度/可复现性（显式传 `backend="hash"`）
  - auto backend 返回非空向量 + 可复现性
  - ST backend 384 维（skipif 无 sentence-transformers）
  - `build_vector_store` 自动检测 actual dim
  - 向量持久化一致性
  - FAISS 可用/不可用两条路径

## 10. 技术栈

- `Python 3`：Embedding 与索引调度
- `numpy`：向量数组、矩阵运算、L2 归一化
- `sentence-transformers`（可选，推荐）：语义嵌入，all-MiniLM-L6-v2
- `zlib.crc32`：轻量哈希特征映射（hash BoW fallback）
- `faiss-cpu`（可选）：高效近邻检索索引
- `json`：向量存储持久化

## 11. 端到端流程（这一部分如何工作）

1. 输入 `List[Chunk]`（或 `chunks` 字典）
2. `embed_text(backend="auto")` 自动选择后端，将文本映射到向量
3. `build_vector_store()` 聚合为 `VectorStore(vectors, metadata, backend)`
4. 保存到 `artifacts/vectors/vectors.npz`（numpy 压缩，含 `backend` 字段）
5. 若环境支持 FAISS，构建/加载 `artifacts/index/faiss.index`
6. 输出给 `retriever` — retriever 读取 `store.backend` 保持 query 与索引后端一致

## 12. 核心函数在做什么，为什么这样做

- `embed_text()`：
  - **做什么**：把任意文本变成固定维度向量并归一化
  - **为什么**：让后续相似度计算可比较；ST backend 提供真实语义理解，大幅提升检索质量
- `_get_st_model()`：
  - **做什么**：懒加载 sentence-transformers 模型并缓存到模块级变量
  - **为什么**：模型加载约 1-2 秒，缓存后同进程内后续调用无额外开销
- `build_vector_store()`：
  - **做什么**：批量向量化并绑定元数据，记录 resolved backend
  - **为什么**：检索时要同时返回 `text/source/page`，且需记录 backend 保证一致性
- `build_faiss_index()/search_faiss()`：
  - **做什么**：可选地使用 FAISS 加速近邻搜索
  - **为什么**：数据量增大时，即使 numpy 矩阵运算也会成为瓶颈；FAISS 提供亚线性搜索
