# Tutorial_pipeline

## 1. 模块作用（What）

`pipeline/` 包是项目的**核心管线层**，封装了离线构建和在线问答的全部业务逻辑。它是 UI 层与功能模块之间的桥梁。

## 2. 设计思路（Why）

- 重构前，离线构建逻辑（`build_or_load_*`）混在 `main.py`（CLI 入口），在线问答逻辑（`answer_with_store`）混在 `app.py`（CLI UI）。
- 这导致 `evaluation.py` 和 `web_app.py` 必须 `from app import ...`，形成 UI 层之间的反向依赖。
- 提取到 `pipeline/` 后，所有 UI 入口只依赖 `pipeline`，不互相依赖。
- **核心原则：零 IO 绑定**。`pipeline/` 不含 `argparse`、`input()`、`print()`、`streamlit` 等 IO 操作，只接收参数、返回数据。

## 3. 包结构

```
pipeline/
├── __init__.py      # 重导出核心 API
├── build.py         # 离线构建（chunks / vectors / FAISS）
└── query.py         # 在线问答（retrieve → prompt → generate → format）
```

## 4. 核心实现（How）

### `pipeline/build.py` — 离线构建

| 函数 | 输入 | 输出 | 职责 |
|------|------|------|------|
| `build_or_load_chunks()` | force_rebuild, chunk_size, overlap | `(chunks, source)` | cache-first 加载或构建 chunks |
| `build_or_load_vectors()` | chunks, force_rebuild, dim | `(vector_store, source)` | cache-first 加载或构建向量 |
| `build_or_load_faiss_index()` | vector_store, force_rebuild | `(index \| None, source)` | 可选 FAISS 索引 |
| `build_runtime()` | 同上三者 | `(vector_store, faiss_index)` | 一步到位的便捷封装 |

`source` 返回值为 `'cache'` / `'rebuild'` / `'migrated'` / `'unavailable'`，方便调用方输出日志。

### `pipeline/query.py` — 在线问答

| 函数 | 输入 | 输出 | 职责 |
|------|------|------|------|
| `answer_with_store()` | query, vector_store, 各种配置参数 | `dict {answer, sources, debug}` | 完整问答链路 |
| `render_response()` | response dict, include_debug | `str` | 结构化结果 → 可打印文本 |
| `_debug_to_lines()` | debug dict | `list[str]` | debug 信息格式化 |

`answer_with_store()` 内部串联：检索 → 低相关过滤（可选）→ Prompt 构建 → LLM 生成 → 格式化 → 附加 debug 元数据。

## 5. 数据流（Data Flow）

```
离线构建:
  data/*.pdf/docx/pptx/md
    → ingestion.loader.load_documents_from_dir()
    → ingestion.chunking.chunk_documents()
    → ingestion.embedding.build_vector_store()
    → [可选] ingestion.embedding.build_faiss_index()
    → artifacts/ 缓存

在线问答:
  query (str)
    → retrieval.retriever.retrieve_top_k()
    → [可选] min_relevance_score 过滤
    → retrieval.prompt.build_prompt()
    → retrieval.generator.generate_answer_with_meta()
    → retrieval.formatter.format_response()
    → {answer, sources, debug}
```

## 6. 模块关系（上下游）

- **被谁依赖**（UI 层）：`cli.py`、`main.py`、`app.py`、`evaluation.py`、`web_app.py`
- **依赖谁**（功能模块）：`ingestion`（loader/chunking/embedding）、`retrieval`（retriever/prompt/generator/formatter）
- **依赖谁**（配置）：`config.defaults`、`config.paths`

```
UI 入口 → pipeline/ → config/ + 功能模块
```

## 7. 参数建议与边界行为

- `build_or_load_chunks()`：`overlap >= chunk_size` 时抛出 `ValueError`
- `build_or_load_vectors()`：`dim <= 0` 时抛出 `ValueError`
- `answer_with_store()`：`top_k <= 0` 或 `min_relevance_score` 超出 `[0, 1]` 时抛出 `ValueError`
- `answer_with_store()` 中 `min_relevance_score=None` 表示关闭过滤

## 8. 测试映射

- `pipeline/query.py` 中的 `answer_with_store` 和 `render_response` 被 `tests/test_app.py` 覆盖
  - 测试导入路径：`from pipeline import answer_with_store, render_response`
- `pipeline/build.py` 的构建逻辑在集成测试中被间接覆盖

## 9. 技术栈

- Python 标准库：`datetime`、`pathlib`
- 项目内模块：`ingestion`、`retrieval`
- 配置层：`config.defaults`、`config.paths`

## 10. 端到端流程（这一部分如何工作）

1. UI 入口调用 `build_runtime()` 获取 `(vector_store, faiss_index)`
2. 用户提问后，UI 入口调用 `answer_with_store(query, vector_store, ...)` 获取结构化结果
3. UI 入口负责将结果呈现给用户（CLI 打印 / Web 渲染 / 评估报告写入）
4. `pipeline/` 始终不关心输出到哪里，只负责"给我参数，还你结果"

## 11. 核心函数在做什么，为什么这样做

- `build_or_load_chunks()`：
  - **做什么**：优先读缓存，缓存不存在则从源文档重建
  - **为什么**：避免每次启动都重新解析文档，大幅缩短启动时间
- `build_runtime()`：
  - **做什么**：封装 chunks → vectors → FAISS 三步构建
  - **为什么**：UI 层只关心"给我一个可用的运行时"，不需要了解构建细节
- `answer_with_store()`：
  - **做什么**：执行完整的 retrieve → prompt → generate → format 链路
  - **为什么**：统一问答入口，CLI / Web / Eval 共用同一套逻辑，行为不会漂移
- `render_response()`：
  - **做什么**：将 dict 结果格式化为可打印字符串
  - **为什么**：CLI 需要文本输出，但 pipeline 层不应包含 print 调用，所以提供一个"数据 → 文本"的纯函数
