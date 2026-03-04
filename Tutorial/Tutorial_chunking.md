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

## 6. 接口细节（Inputs / Outputs）

- **数据结构**：`Chunk(text: str, source: str, page: int)`
- `chunk_document(doc, chunk_size=500, overlap=50) -> list[Chunk]`
- `chunk_documents(documents, chunk_size=500, overlap=50) -> list[Chunk]`
- `save_chunks(chunks: list[dict], path: str) -> None`
- `load_chunks(path: str) -> list[dict]`

## 7. 关键参数建议

- `chunk_size`：常用 `300~800`
- `overlap`：常用 `30~120`，需满足 `< chunk_size`
- 若命中质量差：
  - 优先减小 `chunk_size`
  - 再小幅增大 `overlap`

## 8. 异常与边界行为

- `overlap >= chunk_size`：抛 `ValueError`
- 文本为空：返回空列表
- `load_chunks` 文件不存在：`FileNotFoundError`
- `load_chunks` JSON 根对象非 list：`ValueError`

## 9. 测试映射

- 对应：`tests/test_chunking.py`、`tests/test_storage_chunks.py`
- 覆盖点：
  - 切分逻辑与顺序
  - 边界参数校验
  - 持久化 round-trip 一致性

## 10. 技术栈

- `Python 3`：切块逻辑与序列化逻辑
- `dataclasses`：`Chunk` 结构
- `json`：`chunks` 可读持久化
- `pathlib/os`：目录自动创建与路径处理

## 11. 端到端流程（这一部分如何工作）

1. 接收 `List[Document]`  
2. 按 `chunk_size/overlap` 将长文本分割成多个 `Chunk`  
3. 每个 `Chunk` 保留原始 `source/page` 元数据  
4. 调用 `chunks_to_dicts()` 转为可持久化结构  
5. 调用 `save_chunks()` 写入 `artifacts/chunks/chunks.json`  
6. 运行时优先 `load_chunks()` 复用缓存

## 12. 核心函数在做什么，为什么这样做

- `chunk_document()`：
  - **做什么**：单文档切块，控制长度与重叠
  - **为什么**：保证检索粒度可控，避免上下文过长导致召回不准
- `chunk_documents()`：
  - **做什么**：批量文档切块并合并输出
  - **为什么**：统一多文档处理入口，简化主流程编排
- `save_chunks()/load_chunks()`：
  - **做什么**：切块结果持久化与恢复
  - **为什么**：减少重复预处理时间，支持可复现实验
