# RAG-Demo 技术说明文档

本文档从工程视角详细说明项目的每个技术环节：做了什么、怎么做的、为什么这样做、数据长什么样。适合代码审查、答辩讲解或新成员快速上手。

---

## 目录

1. [系统总览](#1-系统总览)
2. [分层架构](#2-分层架构)
3. [离线构建链路](#3-离线构建链路)
   - 3.1 Document Loader
   - 3.2 Chunking
   - 3.3 Embedding & Vector Store
   - 3.4 FAISS Index
4. [在线问答链路](#4-在线问答链路)
   - 4.1 Retriever
   - 4.2 Prompt Builder
   - 4.3 LLM Generator
   - 4.4 Response Formatter
5. [核心管线层 pipeline/](#5-核心管线层-pipeline)
6. [共享配置层 config/](#6-共享配置层-config)
7. [应用层入口](#7-应用层入口)
8. [评估体系](#8-评估体系)
9. [关键设计决策](#9-关键设计决策)
10. [数据结构参考](#10-数据结构参考)

---

## 1. 系统总览

本项目是一个完整的 **Retrieval-Augmented Generation (RAG)** 问答系统，核心流程分两阶段：

**离线阶段**：将课程文档（PDF / PPTX / DOCX / MD）解析、切片、向量化后存入向量库。

**在线阶段**：用户提问后，从向量库中检索最相关的文档片段，拼成 Prompt 交给 LLM 生成答案，同时返回来源信息。

端到端数据流：

```
文档 → Loader → Chunking → Embedding → VectorStore
                                             ↓
用户提问 → Retriever → Prompt Builder → LLM Generator → Formatter → Answer + Sources
```

---

## 2. 分层架构

项目采用严格的三层架构，依赖方向单向，不存在循环引用：

```
┌─────────────────────────────────────────────┐
│  UI 层（含 IO 绑定）                         │
│  cli.py · main.py · app.py · web_app.py     │
│  evaluation.py                               │
└──────────────────┬──────────────────────────┘
                   │ import
┌──────────────────▼──────────────────────────┐
│  核心管线层（零 IO）                          │
│  pipeline/build.py · pipeline/query.py       │
└──────────────────┬──────────────────────────┘
                   │ import
┌──────────────────▼──────────────────────────┐
│  功能模块 + 配置                              │
│  loader · chunking · embedding · retriever   │
│  prompt · generator · formatter              │
│  config/defaults · config/paths · config/env │
└─────────────────────────────────────────────┘
```

**为什么这样分**：重构前，`evaluation.py` 和 `web_app.py` 从 `app.py` 导入 `answer_with_store`，形成 UI 层之间的反向依赖。提取 `pipeline/` 后，所有 UI 入口只依赖核心管线层。

---

## 3. 离线构建链路

### 3.1 Document Loader（`loader.py`）

**职责**：读取源文档，输出标准化的 `List[Document]`。

**支持格式**：

| 格式 | 解析方式 | 依赖库 |
|------|----------|--------|
| PDF | 逐页提取文本 | `pypdf` |
| PPTX | 逐幻灯片提取文本框内容 | `python-pptx` |
| DOCX | 逐段落提取文本，每 5 段合并为一页 | `python-docx` |
| Markdown | 按 `## ` 标题分段 | 无（标准库） |

**数据结构**：

```python
@dataclass
class Document:
    content: str   # 文本内容
    source: str    # 文件名（如 "lecture1.pdf"）
    page: int      # 页码/序号（从 1 开始）
```

**关键设计**：
- 统一入口 `load_document(path)` 按文件后缀自动分发到对应解析函数。
- 批量入口 `load_documents_from_dir(dir)` 遍历目录，跳过不支持的文件类型。
- 旧接口 `load_pdf()` / `load_pdfs_from_dir()` 保留向后兼容。
- 空页/空幻灯片会被自动跳过，不会产生空 `Document`。

**输入输出示例**：

```
输入：data/lecture1.pdf（3 页 PDF）
输出：[Document(content="...", source="lecture1.pdf", page=1),
       Document(content="...", source="lecture1.pdf", page=2),
       Document(content="...", source="lecture1.pdf", page=3)]
```

---

### 3.2 Chunking（`chunking.py`）

**职责**：将 `Document` 切成固定大小的 `Chunk`，为后续向量化做准备。

**为什么要切片**：LLM 的 context window 有限，且检索粒度需要足够细才能定位到具体段落。太长的文本会稀释检索信号，太短则缺少语义完整性。

**算法**：
1. 从 `Document.content` 的起始位置开始，取 `chunk_size` 个字符。
2. 在取到的文本末尾向前搜索句号（`. `）作为切断点，避免把句子切断。
3. 下一个 chunk 的起始位置 = 上一个切断点 - `overlap`，形成重叠以保留上下文衔接。
4. 重复直到文本耗尽。

**参数**：
- `chunk_size=500`：每个 chunk 最大字符数
- `overlap=50`：相邻 chunk 重叠字符数

**数据结构**：

```python
@dataclass
class Chunk:
    text: str      # 文本片段
    source: str    # 来源文件名
    page: int      # 页码
```

**持久化**：chunk 列表序列化为 JSON 存储到 `artifacts/chunks/chunks.json`，采用 cache-first 策略——文件存在直接加载，不存在才重新切片。

**输入输出示例**：

```
输入：Document(content="A 500-char text...", source="l1.pdf", page=1)
参数：chunk_size=200, overlap=30
输出：[Chunk(text="A 200-char...", source="l1.pdf", page=1),
       Chunk(text="...overlap 30 chars + next 170 chars...", source="l1.pdf", page=1),
       ...]
```

---

### 3.3 Embedding & Vector Store（`embedding.py`）

**职责**：将每个 chunk 的文本映射为固定维度的浮点向量，并存入向量库。

**嵌入算法**（Hashing Bag-of-Words）：

```
文本 → 分词（正则 \w+） → 每个 token 用 zlib.crc32 哈希到 [0, dim) 区间 → 累加到 dim 维向量 → L2 归一化
```

**为什么用这个算法**：
- **可复现**：纯确定性计算，不依赖外部模型或随机种子。
- **轻量**：不需要下载预训练模型，零额外依赖。
- **教学目的**：演示 RAG 流程而非追求生产级检索质量。

**向量存储结构**：

```python
@dataclass
class VectorStore:
    dim: int                        # 向量维度（默认 256）
    vectors: list[list[float]]      # 每个 chunk 的向量
    metadata: list[dict]            # 每个 chunk 的元数据（text/source/page）
```

**持久化**：序列化为 JSON 存储到 `artifacts/vectors/vectors.json`。同样采用 cache-first 策略。

**输入输出示例**：

```
输入：[{"text": "Dynamic programming...", "source": "l1.pdf", "page": 10}, ...]
输出：VectorStore(dim=256, vectors=[[0.03, -0.01, ...], ...], metadata=[...])
```

---

### 3.4 FAISS Index（`embedding.py` 的可选功能）

**职责**：用 Facebook AI Similarity Search (FAISS) 构建高效的近似最近邻索引，加速大规模向量检索。

**为什么是可选的**：
- `faiss-cpu` 在某些环境下安装困难（尤其是 Windows + 特定 Python 版本）。
- 项目设计为无 FAISS 时自动降级到纯 Python 内积检索，功能完全可用。

**工作流**：

```
if faiss 已安装:
    VectorStore → build_faiss_index() → faiss.IndexFlatIP → 保存到 artifacts/index/faiss.index
else:
    跳过，检索时用纯 Python 内积排序
```

---

## 4. 在线问答链路

### 4.1 Retriever（`retriever.py`）

**职责**：给定用户问题，从向量库中找到最相关的 Top-k 个 chunk。

**算法**：
1. 将 query 文本用同一个嵌入函数（Hashing BoW）转为向量。
2. 如果有 FAISS 索引：调用 `search_faiss()` 做近似最近邻搜索。
3. 否则：逐一计算 query 向量与所有 chunk 向量的内积（dot product），取最高的 k 个。

**为什么用内积而不是余弦相似度**：向量已经过 L2 归一化，归一化后的内积等价于余弦相似度。

**返回格式**：

```python
[
    {"index": 42, "score": 0.87, "text": "...", "source": "l1.pdf", "page": 10},
    {"index": 15, "score": 0.73, "text": "...", "source": "l2.pdf", "page": 3},
    ...
]
```

**低相关过滤**（可选）：在 `pipeline/query.py` 的 `answer_with_store()` 中，可通过 `min_relevance_score` 参数过滤低分结果。全部被过滤后，模型会收到空上下文，更容易触发 "I don't know" 回答。

---

### 4.2 Prompt Builder（`prompt.py`）

**职责**：将用户问题 + 检索到的上下文拼成结构化的 LLM 输入。

**Prompt 模板**：

```
You are a course assistant.
Answer the question ONLY based on the provided context.
If the context is insufficient, reply exactly: I don't know.

Question:
{用户问题}

Context:
[Context 1] source=l1.pdf, page=10
{chunk 文本}

[Context 2] source=l2.pdf, page=3
{chunk 文本}

Return a concise answer.
```

**关键设计**：
- **Grounded Generation 约束**："ONLY based on the provided context" 防止 LLM 凭空编造。
- **拒答机制**："reply exactly: I don't know" 在上下文不足时触发。
- **长度控制**：`max_context_chars=4000` 限制上下文总长度，防止超出 LLM 的 token 限制。超过时在 chunk 边界截断。

**输入输出示例**：

```
输入：query="What is DP?", contexts=[{text: "Dynamic programming...", source: "l1.pdf", page: 10}]
输出：（上述格式的完整 prompt 字符串）
```

---

### 4.3 LLM Generator（`generator.py`）

**职责**：接收 prompt，调用 LLM 生成答案。

**支持的 Provider**：

| Provider | 说明 | 何时使用 |
|----------|------|----------|
| `local` | 本地占位实现：取第一个 context 的第一句话作为答案 | 无网络/无 API Key/快速测试 |
| `openai` | OpenAI 官方 API | 有 OpenAI Key |
| `openai_compatible` | 兼容 OpenAI 协议的第三方 API（如阿里 DashScope） | 国内用户/自部署模型 |

**调用流程**（非 local provider）：

```
1. 解析 .env 获取 API Key
2. 创建 OpenAI 客户端（设置 base_url, timeout, max_retries=0）
3. 发起 chat.completions.create 请求
4. 若成功 → 返回答案 + 元数据
5. 若失败 → 重试（指数退避，0.5s → 1s → 2s）
6. 所有重试耗尽 → 如果允许回退，返回 local fallback 答案；否则抛出 RuntimeError
```

**超时预算机制**：设定一个总超时（如 120s），每次重试前检查剩余时间。`remaining = deadline - now`，若 `remaining <= 0` 则不再尝试。SDK 的 `max_retries` 设为 0，由我们自己控制重试逻辑，避免 SDK 内部重试和我们的重试叠加导致实际超时远超预期。

**元数据返回**（`generate_answer_with_meta`）：

```python
meta = {
    "requested_provider": "openai_compatible",
    "used_provider": "openai_compatible",  # 可能是 "local_fallback"
    "used_remote_llm": True,
    "fallback_triggered": False,
    "attempts": 1,
    "error": None,
}
```

这些元数据会被 `answer_with_store()` 合并到 debug 信息中，用于 UI 展示和问题排查。

---

### 4.4 Response Formatter（`formatter.py`）

**职责**：将答案和检索上下文整合为最终输出结构。

**核心逻辑**：
1. 从 contexts 中提取 `(source, page)` 对。
2. 按出现顺序去重（相同 source + page 只保留第一次出现）。
3. 返回 `{"answer": "...", "sources": [{"source": "l1.pdf", "page": 10}, ...]}`。

**为什么要去重**：同一个 source+page 可能产生多个 chunk（因为 overlap），用户不需要看到重复的来源。

---

## 5. 核心管线层 pipeline/

### `pipeline/build.py` — 离线构建

封装了三个 cache-first 函数，依次处理 chunks → vectors → FAISS：

| 函数 | 缓存路径 | 返回值 |
|------|----------|--------|
| `build_or_load_chunks()` | `artifacts/chunks/chunks.json` | `(chunks, "cache"\|"rebuild"\|"migrated")` |
| `build_or_load_vectors()` | `artifacts/vectors/vectors.json` | `(vector_store, "cache"\|"rebuild")` |
| `build_or_load_faiss_index()` | `artifacts/index/faiss.index` | `(index\|None, "cache"\|"rebuild"\|"unavailable")` |

`build_runtime()` 是三步合一的便捷入口，返回 `(vector_store, faiss_index)`。

### `pipeline/query.py` — 在线问答

`answer_with_store()` 是完整问答链路的单一入口：

```
query → retrieve_top_k() → [min_relevance_score 过滤] → build_prompt() → generate_answer_with_meta() → format_response() → 附加 debug 元数据 → 返回 dict
```

**零 IO 原则**：`pipeline/` 不包含任何 `print`、`input`、`argparse`、`streamlit` 调用。它只接收参数、返回数据，UI 层负责 IO。

---

## 6. 共享配置层 config/

| 文件 | 内容 |
|------|------|
| `config/defaults.py` | 默认值常量：chunk_size、overlap、embed_dim、top_k、temperature、LLM timeout 等 |
| `config/paths.py` | 路径常量：`CHUNKS_PATH`、`VECTORS_PATH`、`FAISS_INDEX_PATH` |
| `config/env.py` | `load_env_defaults()` 解析 `.env` 文件；`get_llm_default()` 三级回退取值 |

**为什么不用 python-dotenv**：减少外部依赖，手动解析仅 ~15 行代码。

---

## 7. 应用层入口

### 统一 CLI（推荐）

```bash
python cli.py build                           # 离线构建
python cli.py query "What is A/B testing?"    # 单次问答
python cli.py chat                            # 交互式 REPL
python cli.py eval --eval-set eval/xxx.json   # 批量评估
python cli.py web                             # 启动 Streamlit
```

基于 typer 框架，自动生成帮助文档和参数校验。

### 旧入口（向后兼容）

| 命令 | 等价新命令 |
|------|-----------|
| `python main.py` | `python cli.py build` |
| `python main.py --query "..."` | `python cli.py query "..."` |
| `python app.py` | `python cli.py chat` |
| `python evaluation.py` | `python cli.py eval` |
| `streamlit run web_app.py` | `python cli.py web` |

### Web UI（`web_app.py`）

Streamlit 构建的对话式界面，侧边栏提供：
- LLM Provider / Model / Endpoint 选项卡式配置（联动预置文件 `llm_presets.json`）
- Top-k、Temperature、Timeout、Min Relevance Score 滑动/输入控件
- Debug 信息折叠面板（provider、检索 chunk 数、FAISS 状态、回退状态等）
- 会话历史与清空按钮

---

## 8. 评估体系

### 评估流程

```
评测集 JSON → 逐条调用 answer_with_store() → 逐条计算指标 → 聚合 summary → 写入报告 JSON
```

### 指标说明

| 指标 | 计算方式 | 衡量什么 |
|------|----------|----------|
| `answer_exact_match` | 归一化后完全相同为 1，否则为 0 | 最严格的正确性基线 |
| `answer_token_f1` | 词粒度的 precision × recall 调和平均 | 比 EM 更宽容的答案质量 |
| `keyword_recall` | 答案中命中的关键词比例 | 是否覆盖领域核心术语 |
| `source_recall` | 命中的来源占期望来源的比例 | 检索链路质量 |
| `source_hit_rate` | 至少命中一个来源的样本比例 | 检索可用性底线 |

### 评测集格式

```json
[
  {
    "id": "dp_basic",
    "query": "What is dynamic programming?",
    "expected_answer": "Dynamic programming is a method for solving complex problems...",
    "expected_keywords": ["overlapping", "subproblems", "optimal"],
    "expected_sources": [{"source": "lecture1.pdf", "page": 10}],
    "top_k": 3
  }
]
```

项目内置 `eval/eval_set.20_questions.json`（30 题混合集，含 10 题 "I don't know" 对照样本），用于测试系统的拒答能力。

---

## 9. 关键设计决策

### Cache-First 策略

所有中间产物（chunks / vectors / FAISS index）优先从磁盘加载。只有首次运行或传入 `--force-rebuild` 时才重新构建。这大幅减少了重复启动时间。

### Grounded Generation

Prompt 模板中明确限定 "ONLY based on the provided context"，配合 `min_relevance_score` 过滤低相关检索结果，双重保障减少 LLM 幻觉。

### 多 Provider 回退

LLM 调用链支持三级回退：远程 API → 重试 → 本地占位回答。确保即使网络不通也能产出结果（尽管质量有限），适用于演示和开发阶段。

### 向量维度选择

默认 `dim=256`。哈希 BoW 方案下，维度越高碰撞越少但存储越大。256 在教学场景下是合理的平衡点。

### 句末切片

Chunking 时优先在句末（`. `）切断，避免破坏句意完整性。如果 chunk_size 范围内没有句号，退化为按字符数硬切。

---

## 10. 数据结构参考

### 核心 Dataclass

```python
# loader.py
@dataclass
class Document:
    content: str    # 单页/单段文本
    source: str     # 文件名
    page: int       # 页码（从 1 开始）

# chunking.py
@dataclass
class Chunk:
    text: str       # 文本片段
    source: str     # 来源文件名
    page: int       # 页码

# embedding.py
@dataclass
class VectorStore:
    dim: int                    # 向量维度
    vectors: list[list[float]]  # 向量列表
    metadata: list[dict]        # 元数据列表
```

### 问答返回结构

```python
{
    "answer": "Dynamic programming is a method for solving...",
    "sources": [
        {"source": "lecture1.pdf", "page": 10},
        {"source": "lecture2.pdf", "page": 3},
    ],
    "debug": {
        "generated_at": "2026-03-04 15:30:00",
        "used_remote_llm": True,
        "requested_provider": "openai_compatible",
        "used_provider": "openai_compatible",
        "llm_model": "qwen-plus",
        "llm_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "top_k_requested": 3,
        "retrieved_chunks": 3,
        "min_relevance_score": 0.15,
        "best_retrieval_score": 0.87,
        "relevance_filter_triggered": False,
        "faiss_enabled": True,
        "fallback_enabled": True,
        "fallback_triggered": False,
        "llm_attempts": 1,
        "llm_error": None,
        "sources_returned": 2,
    }
}
```

### 文件存储布局

```
artifacts/
├── chunks/
│   └── chunks.json           # List[{text, source, page}]
├── vectors/
│   └── vectors.json          # {dim, vectors, metadata}
├── index/
│   └── faiss.index           # FAISS 二进制索引（可选）
└── eval/
    └── latest_report.json    # 评估报告

eval/
├── eval_set.example.json     # 最小示例评测集
└── eval_set.20_questions.json  # 30 题混合评测集
```
