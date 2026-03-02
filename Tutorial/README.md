# RAG Tutorial Index

本目录用于说明项目各核心模块的设计与实现思路，帮助快速理解当前代码与后续开发方向。

## 整体 RAG Pipeline

当前目标流程（按模块）：

1. `loader`：读取 PDF，输出 `List[Document]`
2. `chunking`：将 `Document` 切分为 `List[Chunk]`
3. `embedding`：将 `Chunk` 向量化并写入向量存储（已实现）
4. `retriever`：根据 query 检索 Top-k 相关片段（待实现）
5. `prompt`：将 query + contexts 组装为提示词（待实现）
6. `generator`：调用 LLM 生成答案（待实现）
7. `formatter`：输出答案 + 来源（待实现）

## 模块教程列表

- [Tutorial_loader.md](./Tutorial_loader.md)
- [Tutorial_chunking.md](./Tutorial_chunking.md)
- [Tutorial_main.md](./Tutorial_main.md)
- [Tutorial_embedding.md](./Tutorial_embedding.md)
- [Tutorial_retriever.md](./Tutorial_retriever.md)
- [Tutorial_prompt.md](./Tutorial_prompt.md)
- [Tutorial_generator.md](./Tutorial_generator.md)
- [Tutorial_testing.md](./Tutorial_testing.md)

## 当前实现状态

- 已实现：`loader`、`chunking`、`main`、`embedding`、chunk/vector 持久化、FAISS 接口（可选依赖）
- 待实现：`retriever`、`prompt`、`generator`、`formatter`

## 当前实现状态矩阵

| 模块 | 状态 | 代码位置 |
|------|------|----------|
| Loader | 已实现 | `loader.py` |
| Chunking | 已实现 | `chunking.py` |
| Chunk 持久化 | 已实现（内联） | `chunking.py` |
| Main 流程 | 已实现 | `main.py` |
| Embedding | 已实现 | `embedding.py` |
| Retriever | 待实现 | `retriever.py` |
| Prompt Builder | 待实现 | `prompt.py` |
| Generator | 待实现 | `generator.py` |
| Testing | 已实现（Phase 1 + Phase 2） | `tests/` |

## 建议阅读顺序

1. `Tutorial_loader.md`
2. `Tutorial_chunking.md`
3. `Tutorial_main.md`
4. `Tutorial_testing.md`
5. `Tutorial_embedding.md` → `Tutorial_retriever.md` → `Tutorial_prompt.md` → `Tutorial_generator.md`
