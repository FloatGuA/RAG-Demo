# RAG Tutorial Index

本目录用于说明项目各核心模块的设计与实现思路，帮助快速理解当前代码与后续开发方向。
本版为**详细教程**，每篇尽量覆盖：

- 模块作用 / 设计动机
- 关键接口（输入、输出、参数）
- 边界行为与常见错误
- 与测试文件的对应关系
- 快速验证建议

## 教程写作规范（统一模板）

每篇模块教程按统一结构编写，保证“看一篇会看全部”：

1. 模块作用（What）
2. 设计思路（Why）
3. 核心实现（How）
4. 数据流（Data Flow）
5. 模块关系（上下游）
6. 接口细节（输入 / 输出）
7. 参数建议与边界行为
8. 测试映射
9. 技术栈
10. 端到端流程
11. 核心函数职责与设计原因

## 整体 RAG Pipeline

当前目标流程（按模块）：

1. `loader`：读取多类型文档（PDF/PPTX/DOCX/MD），输出 `List[Document]`
2. `chunking`：将 `Document` 切分为 `List[Chunk]`
3. `embedding`：将 `Chunk` 向量化并写入向量存储
4. `retriever`：根据 query 检索 Top-k 相关片段
5. `prompt`：将 query + contexts 组装为提示词
6. `generator`：调用 LLM 生成答案（支持多 provider）
7. `formatter`：输出答案 + 来源
8. `evaluation`：批量评测问答效果并输出指标报告
9. `config/`：共享配置层（默认值、路径、`.env` 加载）
10. `pipeline/`：核心管线层（离线构建 + 在线问答，零 IO 绑定）
11. `cli.py`：统一 CLI 入口（typer，子命令 build/query/chat/eval/web）

## 模块教程列表

- [Tutorial_loader.md](./Tutorial_loader.md)
- [Tutorial_chunking.md](./Tutorial_chunking.md)
- [Tutorial_main.md](./Tutorial_main.md)
- [Tutorial_embedding.md](./Tutorial_embedding.md)
- [Tutorial_retriever.md](./Tutorial_retriever.md)
- [Tutorial_prompt.md](./Tutorial_prompt.md)
- [Tutorial_generator.md](./Tutorial_generator.md)
- [Tutorial_app.md](./Tutorial_app.md)
- [Tutorial_evaluation.md](./Tutorial_evaluation.md)
- [Tutorial_config.md](./Tutorial_config.md)
- [Tutorial_pipeline.md](./Tutorial_pipeline.md)
- [Tutorial_cli.md](./Tutorial_cli.md)
- [Tutorial_testing.md](./Tutorial_testing.md)

## 当前实现状态

- 已实现：`loader`、`chunking`、`main`、`embedding`、`retriever`、`prompt`、`generator`、`formatter`、chunk/vector 持久化、FAISS 接口（可选依赖）
- 已实现：`evaluation`（离线评测数据集 + 指标汇总报告）
- 待实现：更高级交互能力（如多会话持久化、登录态、反馈闭环）

## 当前实现状态矩阵

| 模块 | 状态 | 代码位置 |
|------|------|----------|
| Loader | 已实现 | `ingestion/loader.py` |
| Chunking | 已实现 | `ingestion/chunking.py` |
| Chunk 持久化 | 已实现（内联） | `ingestion/chunking.py` |
| Main 流程 | 已实现 | `main.py` |
| Embedding | 已实现 | `ingestion/embedding.py` |
| Retriever | 已实现 | `retrieval/retriever.py` |
| Prompt Builder | 已实现 | `retrieval/prompt.py` |
| Generator | 已实现（多 provider） | `retrieval/generator.py` |
| Formatter | 已实现 | `retrieval/formatter.py` |
| Evaluation | 已实现 | `evaluation.py` |
| Config | 已实现 | `config/` |
| Pipeline | 已实现 | `pipeline/` |
| CLI (统一入口) | 已实现（typer） | `cli.py` |
| App (旧 CLI UI) | 已实现 | `app.py` |
| App (Web Chat UI) | 已实现（Streamlit） | `web_app.py` |
| Testing | 已实现（Phase 1 ~ Phase 6） | `tests/` |

## 快速定位（按问题类型）

- **数据读取问题**：先看 `Tutorial_loader.md`、`Tutorial_chunking.md`
- **检索/召回质量问题**：看 `Tutorial_embedding.md`、`Tutorial_retriever.md`
- **回答质量与幻觉问题**：看 `Tutorial_prompt.md`、`Tutorial_generator.md`
- **UI/联调问题**：看 `Tutorial_app.md`
- **配置与环境问题**：看 `Tutorial_config.md`
- **管线架构与分层问题**：看 `Tutorial_pipeline.md`
- **CLI 命令与用法问题**：看 `Tutorial_cli.md`
- **回归与验收问题**：看 `Tutorial_testing.md`

## 建议阅读顺序

1. `Tutorial_loader.md`
2. `Tutorial_chunking.md`
3. `Tutorial_main.md`
4. `Tutorial_testing.md`
5. `Tutorial_embedding.md` → `Tutorial_retriever.md` → `Tutorial_prompt.md` → `Tutorial_generator.md`
6. `Tutorial_config.md` → `Tutorial_pipeline.md` → `Tutorial_cli.md`
7. `Tutorial_evaluation.md`
