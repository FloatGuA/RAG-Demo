# RAG-Demo 待办清单

基于 [Outline.md](./Outline.md) 的设计大纲整理，按最小实现路径分阶段执行。

---

## Phase 1：Day 1 — Loader + Chunking

- [x] **1.1 项目结构**：创建 `data/` 目录和基础代码文件
- [x] **1.2 模块1 Document Loader**：实现 PDF 加载
  - 输入：PDF 文件路径
  - 输出：`List[Document]`
  - 文件：`loader.py`
- [x] **1.3 模块2 Chunking**：实现文档切分
  - 分段、控制 chunk size + overlap
  - 输出：`List[Chunk]`，每项含 `text`, `source`, `page`
  - 文件：`chunking.py`
- [x] **1.4**：用示例 PDF 跑通 Loader → Chunking 流程
- [x] **1.5 Chunk 持久化**：实现并接入 `save_chunks/load_chunks`
  - 文件：`ts20260301_storage_chunks.py`
  - 主流程：有 `artifacts/chunks/chunks.json` 则加载，否则生成并保存（兼容旧 `storage/chunks.json`）
- [x] **1.6 单元测试与测试说明**：Phase 1 全模块单元测试 + 测试文档
  - 文件：`tests/test_loader.py`、`tests/test_chunking.py`、`tests/test_storage_chunks.py`、`tests/conftest.py`、`tests/README.md`
  - 约 30 个用例；`pytest tests/ -v`；加 `-s` 可看中英双语 [TEST START]/[INPUT]/[ACTION]/[EXPECTED]/[PASS]

---

## Phase 2：Day 2 — Embedding + Vector Store

- [ ] **2.1 模块3 Embedding & Index**：实现向量化与索引
  - 输入：`List[Chunk]`
  - 文本 → 向量，写入 VectorStore
  - 文件：`embedding.py`
- [ ] **2.2**：集成 FAISS 作为向量存储
- [ ] **2.2.1 Vector 持久化规范**：实现 `save_vectors/load_vectors`（与 chunk 持久化同标准）
- [ ] **2.3**：实现 offline pipeline：PDF → Chunk → Embedding → 持久化
- [ ] **2.4 单元测试**：为 embedding / 向量存储 / 持久化 编写测试，补入 `tests/`，跑通 `pytest tests/ -v`

---

## Phase 3：Day 3 — Retrieval + LLM

- [ ] **3.1 模块4 Retriever**：实现检索
  - 输入：query + VectorStore
  - Top-k 相似度检索
  - 文件：`retriever.py`
- [ ] **3.2 模块5 Prompt Builder**：构建 RAG prompt
  - 输入：query + chunks
  - 输出：prompt string
  - 文件：`prompt.py`
- [ ] **3.3 模块6 LLM Generator**：调用 LLM 生成回答
  - 输入：prompt
  - 输出：answer
  - 文件：`generator.py`
- [ ] **3.4 模块7 Response Formatter**：整合答案与来源
  - 输出：`{ answer, sources }`
- [ ] **3.5**：跑通完整 online pipeline：Query → Retrieve → LLM → Answer
- [ ] **3.6 单元测试**：为 retriever、prompt、generator、formatter 编写测试，补入 `tests/`，跑通 `pytest tests/ -v`

---

## Phase 4：Day 4 — UI + 加分项

- [ ] **4.1**：实现简单 UI（Web 或 CLI）
- [ ] **4.2**：展示 Source Attribution（来源标注）
  - 格式：Answer + Sources（如 Lecture X, Page Y）
- [ ] **4.3**：Grounded Generation 约束
  - 仅基于 context 回答
  - 超出 context → 输出 "I don't know"
- [ ] **4.4**：主入口与流程串联
  - 文件：`app.py`
- [ ] **4.5 单元测试**：为 app / UI 流程编写测试（含必要 mock），补入 `tests/`，跑通 `pytest tests/ -v`

---

## 工作规范

- **每完成一个模块，必须跑 `pytest tests/ -v` 自测，全部通过后再推进。**
- **每个 Phase 结束时都要为该阶段新增模块编写单元测试**（如 Phase 2 测 embedding/向量持久化，Phase 3 测 retriever/prompt/generator/formatter，Phase 4 测 app），并更新 `tests/` 与 `tests/README.md`。
- **中间结果统一存放到 `artifacts/` 下对应子目录（如 `artifacts/chunks/`、`artifacts/vectors/`）。**

## 设计要点（实现时需遵守）

| 要点 | 说明 |
|------|------|
| 模块解耦 | retrieval / embedding / LLM 均可替换 |
| Chunk 质量 | 合理设置 chunk size、overlap、top-k |
| Source 标注 | 答案必须附带来源（lecture + page） |
| 防幻觉 | 仅使用 context，未知则如实回答 |

---

## 代码结构（目标）

```
rag-demo/
├── data/                    # 课程 PDF
├── artifacts/               # 中间结果（Phase 1 已有 chunks/）
│   └── chunks/
├── loader.py
├── chunking.py
├── ts20260301_storage_chunks.py
├── embedding.py
├── retriever.py
├── prompt.py
├── generator.py
├── app.py
├── tests/
│   ├── conftest.py
│   ├── test_loader.py
│   ├── test_chunking.py
│   ├── test_storage_chunks.py
│   └── README.md
└── requirements.txt
```
