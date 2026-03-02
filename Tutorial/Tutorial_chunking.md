# Tutorial_chunking

## 1. 模块作用（What）

`chunking.py` 负责把 `Document` 切成可检索的 `Chunk`，并提供 chunk 的持久化能力。

## 2. 设计思路（Why）

- LLM 和检索模型通常不适合直接处理长文档，需先切分。
- 通过 `chunk_size + overlap` 保留上下文连续性。
- 切块时尽量在句末/空白处断开，降低语义破碎。
- 直接内联 `save_chunks/load_chunks`，减少模块跳转，便于维护。

## 3. 核心实现（How）

- 切分函数：
  - `chunk_document(doc, chunk_size=500, overlap=50)`
  - `chunk_documents(documents, chunk_size=500, overlap=50)`
- 序列化函数：
  - `chunks_to_dicts(chunks)`
  - `dicts_to_chunks(raw_chunks)`
- 持久化函数（已内联）：
  - `save_chunks(chunks, path)`：JSON 保存，自动创建目录
  - `load_chunks(path)`：JSON 加载，含不存在/格式错误校验
- 运行逻辑（`__main__`）：
  - 优先读 `artifacts/chunks/chunks.json`
  - 兼容旧 `storage/chunks.json` 自动迁移
  - 无缓存则重新构建并保存

## 4. 数据流（Data Flow）

`List[Document] -> chunk_documents -> List[Chunk] -> chunks_to_dicts -> save_chunks(JSON)`

读取时：

`chunks.json -> load_chunks -> List[dict] -> dicts_to_chunks -> List[Chunk]`

## 5. 模块关系（上下游）

- 上游：`loader.py` 产出的 `List[Document]`
- 下游：
  - 近期：`main.py` 主流程编排
  - 后续：`embedding.py` 读取 `List[Chunk]` 做向量化
