# 项目记忆 (Project Memory)

本文件用于记录项目上下文、决策与重要信息。**每次打开 Cursor 时，说「检查 Memory.md」即可让 AI 续接上次进度。**

> **【工作规范】每完成一个模块/任务后，必须跑单元测试确认通过，再更新本节进度。**

---

## Todolist 进度快照

> 与 [Todolist.md](./Todolist.md) 联动。任务完成后请更新本节，便于下次会话快速续接。

| 字段 | 内容 |
|------|------|
| **当前阶段** | Phase 4：Day 4 — UI + 加分项 |
| **上次完成** | Phase 3 全部完成（3.1/3.2/3.3/3.4/3.5/3.6） |
| **下一步任务** | 4.1 实现简单 UI（先 CLI 或 Web） |
| **最后更新** | 2026-03-01 |

### 阶段完成情况

- Phase 1（Loader + Chunking）：已完成
- Phase 2（Embedding + FAISS）：已完成
- Phase 3（Retrieval + LLM）：已完成
- Phase 4（UI + 加分项）：未开始

---

## Todolist 实现记录

> 每完成一个模块，在此记录实现方式。AI 检查 Memory 时可直接理解代码结构，无需反复读源码。
>
> **⚠️ 每部分写完后都要自测**：实现完成 → 运行 `pytest tests/ -v` → 全部通过后再更新进度。

### Phase 1：Loader + Chunking

| 任务 | 实现文件 | 实现方式 | 接口说明 |
|------|----------|----------|----------|
| 1.1 项目结构 | `data/`, `requirements.txt` | data 放 PDF，requirements 含 pypdf、pytest | - |
| 1.2 Document Loader | `loader.py` | pypdf，`load_pdf(path)` / `load_pdfs_from_dir(dir)`，按页拆为 Document | 输入路径 → `List[Document]` |
| 1.3 Chunking | `chunking.py` | `chunk_document()` / `chunk_documents()`，chunk_size=500，overlap=50，优先在句末切断 | 输入 Document → `List[Chunk]` |
| 1.4 Chunk 持久化 | `chunking.py` | 已内联 `save_chunks(List[dict], path)` / `load_chunks(path)`，JSON 可读存储，文件不存在报错 | `List[dict]` ↔ JSON |
| 1.5 联调 | `chunking.py` | 主流程支持缓存：`artifacts/chunks/chunks.json` 存在则 load，不存在则 chunk 后保存；兼容旧路径 `storage/chunks.json` 自动迁移 | - |
| 1.6 Tutorial 文档体系 | `Tutorial/` | 为 loader/chunking/main/embedding/retriever/prompt/generator/testing 建立结构化教程；每篇含 What/Why/How/Data Flow/上下游关系 | `Tutorial/*.md` |

**Chunk 结构**：`{ text, source, page }`

**Phase 1 单元测试**：`tests/test_loader.py`、`tests/test_chunking.py`、`tests/test_storage_chunks.py`，运行 `pytest tests/ -v`（当前 30 passed）

**持久化规范（后续必须沿用）**：
- 中间结果（chunks/vector 等）都要提供 `save_xxx` / `load_xxx`
- 默认优先 JSON（可读性高）；若向量体积大可用二进制但需补元数据说明
- 主流程采用“有缓存先加载、无缓存再计算并保存”
- 中间结果统一放在 `artifacts/` 目录下，按类型分子目录（如 `artifacts/chunks/`、`artifacts/vectors/`）

### Phase 2：Embedding + Vector Store

| 任务 | 实现文件 | 实现方式 | 接口说明 |
|------|----------|----------|----------|
| 2.1 Embedding | `embedding.py` | 轻量哈希 BoW（可复现）+ L2 归一化，`embed_text()` / `build_vector_store()` | Chunks → VectorStore |
| 2.2 FAISS | `embedding.py` / `main.py` | 已实现 `build_faiss_index()` / `search_faiss()` / `save_faiss_index()` / `load_faiss_index()`；环境无 faiss 时可优雅降级 | `artifacts/index/faiss.index` |
| 2.2.1 向量持久化 | `embedding.py` | 已实现 `save_vectors()` / `load_vectors()`，JSON 可读存储、缺失文件报错 | VectorStore ↔ JSON |
| 2.3 Offline pipeline | `main.py` / `embedding.py` | 已接入：chunk 后自动 build/load vectors（`artifacts/vectors/vectors.json`）并尝试 FAISS 索引（`artifacts/index/faiss.index`）；cache-first | - |
| 2.4 单元测试 | `tests/test_embedding.py` | 覆盖向量化、向量持久化、FAISS 可用/不可用路径；当前全量测试通过 | 49 passed |

### Phase 3：Retrieval + LLM

| 任务 | 实现文件 | 实现方式 | 接口说明 |
|------|----------|----------|----------|
| 3.1 Retriever | `retriever.py` | `retrieve_top_k()`：默认使用向量内积排序；可选接入 FAISS 索引检索；返回 text/source/page/score | query + VectorStore → Top-k Chunks |
| 3.2 Prompt Builder | `prompt.py` | `build_prompt()`：拼接 query + contexts，内置 grounded 约束与 `I don't know` 回退规则 | query + chunks → prompt |
| 3.3 LLM Generator | `generator.py` | `generate_answer()` 支持 `local/openai/openai_compatible`，支持 `.env`、重试、超时、失败回退本地 | prompt (+contexts) → answer |
| 3.4 Response Formatter | `formatter.py` | `format_response()`：输出 `{answer, sources}`，并按 source/page 去重 | answer + chunks → `{ answer, sources }` |
| 3.5 Online pipeline | `main.py` | 支持 `--llm-provider`、`--llm-base-url`、`--llm-model`、`--no-llm-fallback-local`；串联在线流程 | query → answer + sources |
| 3.6 单元测试 | `tests/test_retriever.py` / `tests/test_prompt.py` / `tests/test_generator.py` | 覆盖检索、prompt 组装、provider 校验、无 key 回退与来源格式化；全量通过 | 49 passed |

### Phase 4：UI + 加分项

| 任务 | 实现文件 | 实现方式 | 接口说明 |
|------|----------|----------|----------|
| 4.1 UI | `app.py` | （待填：Streamlit/Gradio/CLI） | - |
| 4.2 Source 展示 | - | （待填） | - |
| 4.3 Grounded 约束 | `prompt.py` | （待填：prompt 中的约束语句） | - |
| 4.4 主入口 | `app.py` | （待填：流程串联方式） | - |

---

## 项目概况

- **项目名称**: RAG-Demo
- **描述**: 基于课程资料的 RAG 问答系统，输入 PDF + 问题，输出答案 + 来源
- **创建时间**: 2025-03-01

---

## 技术栈与架构

- **Phase 1**：pypdf（PDF 解析）、Python dataclass（Document / Chunk）、pytest（单元测试）
- **主流程入口**：`main.py`（缓存优先，调用 loader + chunking + 持久化）
- **教程体系**：`Tutorial/README.md` + `Tutorial/Tutorial_*.md`
- 其余见 [Outline.md](./Outline.md)

---

## 重要决策

| 日期 | 决策 | 原因 |
|------|------|------|
|      |      |      |

---

## 已知问题与注意事项

- 

---

## 笔记与备忘

- 
