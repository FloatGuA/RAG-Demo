# Tutorial_testing

## 1. 模块作用（What）

`tests/` 目录用于验证当前模块实现正确性，并为后续重构提供回归保障。

## 2. 设计思路（Why）

- 将测试前置，可尽早发现逻辑问题与边界问题。
- 每个核心模块配套测试，避免“改一处坏一片”。
- 通过标准化输出（含中英双语 print）提升学习和调试可读性。

## 3. 核心实现（How）

当前测试文件（Phase 1 + Phase 2 + Phase 3 + Phase 4）：

- `tests/test_loader.py`：测试 `loader.py`
- `tests/test_chunking.py`：测试 `chunking.py`
- `tests/test_storage_chunks.py`：测试 `chunking.py` 中 `save_chunks/load_chunks`
- `tests/test_embedding.py`：测试 `embedding.py`（向量化 + 向量持久化 + FAISS）
- `tests/test_retriever.py`：测试 `retriever.py`（Top-k 检索）
- `tests/test_prompt.py`：测试 `prompt.py`（prompt 组装）
- `tests/test_generator.py`：测试 `generator.py` + `formatter.py`
- `tests/test_app.py`：测试 `app.py`（CLI 应用流程与渲染）
- `tests/test_web_app.py`：测试 `web_app.py`（Web UI 辅助函数）
- `tests/test_evaluation.py`：测试 `evaluation.py`（评估指标计算与评测集加载）
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

## 6. 推荐测试策略（按改动范围）

- 仅改检索：`test_embedding.py` + `test_retriever.py`
- 仅改提示词：`test_prompt.py` + `test_generator.py`
- 改 UI 层：`test_app.py` + `test_web_app.py`
- 大改或发版前：`python -m pytest tests/ -v`

## 7. Windows 环境建议

- 优先使用：`python -m pytest tests/ -v`
- 若直接 `pytest` 不可用，通常是 PATH 未注入

## 8. 失败排查顺序

- 第一步：定位首个失败用例（不要先看最后一个）
- 第二步：确认输入 fixture 是否被改坏
- 第三步：确认接口签名是否变化但测试未同步
- 第四步：再看是否为环境依赖问题（如 FAISS）

## 9. 技术栈

- `pytest`：测试框架
- `fixture` / `monkeypatch`：测试数据与依赖隔离
- `skipif`：可选依赖场景（如 FAISS）分支测试
- `python -m pytest`：跨平台稳定执行入口

## 10. 测试流程（这一部分如何工作）

1. 准备 fixtures（临时文件、样本数据、运行参数）  
2. 调用模块函数  
3. 断言输出结构、关键字段与边界行为  
4. 汇总测试报告（pass/fail/skip/warnings）  
5. 作为合并前质量门禁

## 11. 测试函数在做什么，为什么这样做

- 模块级单测（如 `test_retriever.py`）：
  - **做什么**：验证单模块核心逻辑与参数校验
  - **为什么**：定位问题更快，回归成本更低
- 流程级单测（如 `test_app.py`）：
  - **做什么**：验证跨模块串联行为
  - **为什么**：防止接口变更导致链路断裂
- 评估单测（`test_evaluation.py`）：
  - **做什么**：验证指标计算稳定性
  - **为什么**：评估结果会指导优化，指标本身必须可靠
