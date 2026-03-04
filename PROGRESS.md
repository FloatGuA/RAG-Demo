# RAG-Demo 项目进度

本文件合并原 `Todolist.md` 与 `Memory.md`，统一记录任务清单、实现记录与项目状态。**每次打开 Cursor 时，说「检查 PROGRESS.md」即可让 AI 续接上次进度。**

---

## 进度快照

| 字段 | 内容 |
|------|------|
| **当前阶段** | Phase 6 完成（统一 CLI 入口重构） |
| **上次完成** | 统一 CLI 入口（typer）+ config/ 包 + pipeline/ 包 + 旧入口解耦 + TECHNICAL.md + Tutorial 补全 |
| **下一步任务** | 报告对比（baseline vs candidate）、阈值自动寻优（网格搜索）、评测集扩充 |
| **测试状态** | `python -m pytest tests/ -v` — 71 passed |
| **最后更新** | 2026-03-04 |

---

## Phase 1：Loader + Chunking

- [x] **1.1** 项目结构：`data/` + `requirements.txt`
- [x] **1.2** Document Loader（`loader.py`）：PDF 加载 → `List[Document]`
- [x] **1.3** Chunking（`chunking.py`）：`chunk_document()` / `chunk_documents()`，chunk_size=500，overlap=50，句末切断
- [x] **1.4** Loader → Chunking 联调
- [x] **1.5** Chunk 持久化：`save_chunks` / `load_chunks`，缓存 `artifacts/chunks/chunks.json`，兼容旧 `storage/` 迁移
- [x] **1.6** Tutorial 文档体系：`Tutorial/` 目录，统一模板（What/Why/How/Data Flow/上下游/接口/参数/测试映射/技术栈/函数职责）
- [x] **1.7** Loader 多格式扩展：`pdf/pptx/docx/md`，新接口 `load_document()` / `load_documents_from_dir()`，兼容 `load_pdf()`

| 模块 | 文件 | 实现方式 | 接口 |
|------|------|----------|------|
| Loader | `loader.py` | 按后缀分发解析（pypdf / python-pptx / python-docx / 原生 MD） | path → `List[Document]` |
| Chunking | `chunking.py` | 滑动窗口 + 句末切断 + JSON 持久化 | Document → `List[Chunk]` |

---

## Phase 2：Embedding + Vector Store

- [x] **2.1** Embedding（`embedding.py`）：哈希 BoW + L2 归一化，`embed_text()` / `build_vector_store()`
- [x] **2.2** FAISS 集成（可选依赖）：`build_faiss_index()` / `search_faiss()` / `save_faiss_index()` / `load_faiss_index()`
- [x] **2.2.1** Vector 持久化：`save_vectors()` / `load_vectors()`，`artifacts/vectors/vectors.json`
- [x] **2.3** Offline pipeline：`main.py` 串联 chunk → embed → FAISS，cache-first
- [x] **2.4** 单元测试：`tests/test_embedding.py`

| 模块 | 文件 | 实现方式 | 接口 |
|------|------|----------|------|
| Embedding | `embedding.py` | `zlib.crc32` 哈希到 dim 维桶 + numpy L2 norm | Chunks → VectorStore |
| FAISS | `embedding.py` | `faiss.IndexFlatIP`，无 faiss 时优雅降级 | VectorStore → Index |

---

## Phase 3：Retrieval + LLM

- [x] **3.1** Retriever（`retriever.py`）：Top-k 检索，支持 FAISS 与纯 Python 内积双路径
- [x] **3.2** Prompt Builder（`prompt.py`）：Grounded 约束模板，`max_context_chars` 截断
- [x] **3.3** LLM Generator（`generator.py`）：`local` / `openai` / `openai_compatible`，`.env`、重试、超时、回退
- [x] **3.4** Response Formatter（`formatter.py`）：`{answer, sources}` + 来源去重
- [x] **3.5** Online pipeline：`main.py` 支持 `--query` / `--llm-*` 系列参数
- [x] **3.6** 单元测试：`test_retriever.py` / `test_prompt.py` / `test_generator.py`

| 模块 | 文件 | 实现方式 | 接口 |
|------|------|----------|------|
| Retriever | `retriever.py` | 向量内积 / FAISS 检索 | query + VectorStore → Top-k |
| Prompt | `prompt.py` | 模板拼接 + grounded 约束 | query + contexts → prompt |
| Generator | `generator.py` | OpenAI SDK + 超时预算 + 指数退避重试 + 回退 | prompt → answer + meta |
| Formatter | `formatter.py` | 来源按 (source, page) 去重 | answer + contexts → response |

---

## Phase 4：UI + 加分项

- [x] **4.1** CLI UI（`app.py`）：单次查询 + 交互 REPL
- [x] **4.2** Source Attribution：Answer + Sources 展示
- [x] **4.3** Grounded Generation：超出 context → "I don't know"
- [x] **4.4~4.5** 主入口串联 + 单元测试（`tests/test_app.py`）
- [x] **4.6~4.9** Streamlit Web UI（`web_app.py`）：对话气泡、侧边配置面板、会话状态管理
- [x] **4.10~4.11** Web UI 测试 + 文档同步
- [x] **4.12~4.16** UI 体验优化：Provider→Model→Base URL 选项卡联动、`llm_presets.json` 预置、Debug 面板、时间戳、超时/重试鲁棒性

| 模块 | 文件 | 实现方式 |
|------|------|----------|
| CLI UI | `app.py` | argparse + 交互 REPL |
| Web UI | `web_app.py` | Streamlit chat_input/chat_message + session_state |
| LLM 预置 | `llm_presets.json` | provider→models→base_url 映射 |

---

## Phase 5：评估与验收

- [x] **5.1** 评估模块（`evaluation.py`）：批量执行 + 指标汇总 + JSON 报告
- [x] **5.2** 评测集：`eval/eval_set.example.json` + `eval/eval_set.20_questions.json`（30 题混合，含 IDK 对照）
- [x] **5.3** 指标体系：EM / Token F1 / Keyword Recall / Source Recall / Source Hit Rate
- [x] **5.4~5.6** 单元测试 + 文档同步 + 全量回归
- [x] **5.7** 低相关拒答：`min_relevance_score` 阈值过滤，CLI / Web / Eval 参数统一
- [x] **5.8** Tutorial 详细化重构：统一 12 节模板
- [x] **5.9** Loader 多格式扩展 + 文档同步

| 模块 | 文件 | 实现方式 | 接口 |
|------|------|----------|------|
| Evaluation | `evaluation.py` | `token_f1` / `keyword_recall` / `source_metrics` + `evaluate_cases` 主循环 | eval_set → report JSON |

---

## Phase 6：统一 CLI 入口重构

- [x] **6.1** `config/` 包：`defaults.py`（默认值）、`paths.py`（路径）、`env.py`（.env 加载）
- [x] **6.2** `pipeline/` 包：`build.py`（离线构建）、`query.py`（在线问答），零 IO 绑定
- [x] **6.3** `cli.py`：typer 统一入口，子命令 `build` / `query` / `chat` / `eval` / `web`
- [x] **6.4** 旧入口解耦：`main.py` / `app.py` / `evaluation.py` / `web_app.py` 改为从 `pipeline` / `config` 导入，向后兼容
- [x] **6.5** 测试更新：导入路径修正，71 passed
- [x] **6.6** 文档补全：`TECHNICAL.md`（技术说明）+ `Tutorial/Tutorial_config.md` / `Tutorial_pipeline.md` / `Tutorial_cli.md`

| 模块 | 文件 | 实现方式 | 接口 |
|------|------|----------|------|
| config/ | `config/defaults.py` / `paths.py` / `env.py` | 默认值常量 + 路径常量 + `.env` 解析 | `from config import ...` |
| pipeline/ | `pipeline/build.py` / `query.py` | 从 main/app 提取核心逻辑，零 IO | `from pipeline import ...` |
| CLI | `cli.py` | typer 子命令 | `python cli.py <cmd>` |

---

## 已知问题与注意事项

- `llm_presets.json` 预置配置与实际账号权限可能不一致（模型可选但无订阅权限）
- 评估模块为最小可用版，缺少基线报告自动对比与可视化看板
- 评测集质量决定评估价值，建议补充人工标注样本（20~100 条）
- `min_relevance_score` 阈值需按数据集调参
- `.docx/.pptx` 解析依赖 `python-docx/python-pptx`，未安装时对应格式会报错提示
- `eval/eval_set.20_questions.json` 实际含 30 题，文件名待更正

---

## 工作规范

- 每完成一个模块，必须跑 `python -m pytest tests/ -v` 自测，全部通过后再推进
- 每个 Phase 结束时补齐单元测试并同步 `tests/README.md`
- 中间结果统一存放 `artifacts/` 下对应子目录
- 持久化规范：`save_xxx` / `load_xxx`，默认 JSON，cache-first

---

## 代码结构

```
rag-demo/
├── config/               # 共享配置包
│   ├── __init__.py
│   ├── defaults.py       # 默认值常量
│   ├── paths.py          # 路径常量
│   └── env.py            # .env 加载
├── pipeline/             # 核心管线包（零 IO）
│   ├── __init__.py
│   ├── build.py          # 离线构建
│   └── query.py          # 在线问答
├── cli.py                # 统一 CLI 入口（typer）
├── main.py               # 旧 CLI 入口（离线 + 查询）
├── app.py                # 旧 CLI 入口（交互问答）
├── web_app.py            # Streamlit Web UI
├── evaluation.py         # 离线评估
├── loader.py             # 文档加载（PDF/PPTX/DOCX/MD）
├── chunking.py           # 分段切片
├── embedding.py          # 向量化 + FAISS
├── retriever.py          # 检索
├── prompt.py             # Prompt 构建
├── generator.py          # LLM 生成
├── formatter.py          # 答案格式化
├── data/                 # 源文档
├── eval/                 # 评测集
├── artifacts/            # 缓存（chunks/vectors/index/eval）
├── tests/                # 单元测试（71 passed）
└── Tutorial/             # 模块教程（13 篇）
```
