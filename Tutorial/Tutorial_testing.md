# Tutorial_testing

## 1. 模块作用（What）

`tests/` 目录用于验证当前模块实现正确性，并为后续重构提供回归保障。

## 2. 设计思路（Why）

- 将测试前置，可尽早发现逻辑问题与边界问题。
- 每个核心模块配套测试，避免“改一处坏一片”。
- 通过标准化输出（含中英双语 print）提升学习和调试可读性。

## 3. 核心实现（How）

当前测试文件（Phase 1 + Phase 2 + Phase 3）：

- `tests/test_loader.py`：测试 `loader.py`
- `tests/test_chunking.py`：测试 `chunking.py`
- `tests/test_storage_chunks.py`：测试 `chunking.py` 中 `save_chunks/load_chunks`
- `tests/test_embedding.py`：测试 `embedding.py`（向量化 + 向量持久化 + FAISS）
- `tests/test_retriever.py`：测试 `retriever.py`（Top-k 检索）
- `tests/test_prompt.py`：测试 `prompt.py`（prompt 组装）
- `tests/test_generator.py`：测试 `generator.py` + `formatter.py`
- `tests/conftest.py`：公共 fixtures（临时 PDF、示例 Document 等）

运行命令：

- `pytest tests/ -v`
- `pytest tests/ -v -s`（显示中英双语步骤输出）

## 4. 数据流（Data Flow）

`fixtures -> module function call -> assertions/exception checks -> pytest report`

## 5. 模块关系（上下游）

- 上游：项目需求与模块设计（loader/chunking/embedding/retriever/prompt/generator）
- 下游：
  - 开发流程：作为每次改动后的质量门禁
  - 文档流程：`tests/README.md` 记录运行方法与覆盖清单
