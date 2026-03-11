---

## 2026-03-11 17:30 — Phase 10：Eval Dashboard + Streaming + 多轮上下文 + 增量索引等

**触发原因**：用户要求

### 概述
本次会话在 Phase 9 基础上实现了六项功能：① Web UI 新增 Evaluation Dashboard tab；② LLM 流式输出（`st.write_stream`）；③ BM25 索引模块级缓存；④ 多轮对话历史传入 LLM；⑤ 检索/生成延迟分解 debug 面板；⑥ 增量索引（manifest 追踪新文件，只 embed 新 chunks）。全量测试从 90 passed 升至 114 passed，新增 `tests/test_incremental_build.py`。

### 改动清单

**Web UI / 生成层**
- `web_app.py`：新增 Evaluation Dashboard tab（历史报告查看 + 在线触发评估）；流式输出开关（`st.write_stream`）；`build_chat_history()` 提取多轮历史；debug 面板新增延迟分解行
- `retrieval/generator.py`：新增 `_build_messages()`、`_call_openai_chat_stream()`、`generate_answer_stream()`；所有公开函数新增 `chat_history` 参数
- `retrieval/__init__.py`：导出 `generate_answer_stream`
- `pipeline/query.py`：新增 `answer_with_store_stream()`；`answer_with_store` 新增 `chat_history` 参数 + 延迟计时（`latency_retrieval_ms` / `latency_generation_ms` / `latency_total_ms`）
- `pipeline/__init__.py`：导出 `answer_with_store_stream`

**检索层**
- `retrieval/retriever.py`：新增 `_bm25_cache` + `_get_bm25(store)` 模块级缓存，`_bm25_retrieve` 改用缓存

**增量索引**
- `config/paths.py`：新增 `MANIFEST_PATH`
- `pipeline/build.py`：新增 `_load_manifest` / `_save_manifest` / `_scan_data_dir`；`build_or_load_chunks` 返回三元组 `(chunks, source, new_chunks)`，支持 `"incremental"` source；`build_or_load_vectors` 新增 `new_chunks` 参数，增量 embed + append；`build_runtime` 透传增量信息
- `cli.py`：build 命令解包三元组，显示新增 chunk 数

**测试**
- `tests/test_incremental_build.py`：新建，12 个测试（manifest、目录扫描、增量触发、持久化、force-rebuild、变更警告）
- `tests/test_generator.py`：新增 `TestBuildMessages`（2）+ `TestGenerateAnswerStream`（3）
- `tests/test_retriever.py`：新增 BM25 缓存测试（2）
- `tests/test_web_app.py`：新增 `build_chat_history` 测试（4）+ 延迟 debug 测试（1）

**文档**
- `PROGRESS.md`：进度快照更新至 Phase 10，添加 10.1–10.7 任务清单
- `README.md`：Key Features 新增 Streaming / 增量索引；测试数更新至 114；Roadmap P0 标记已完成项
- `TECHNICAL.md`：pipeline/build 节更新；Section 9 新增增量索引策略、多轮上下文、BM25 缓存、流式输出架构四个设计决策

### 决策与背景
- **增量索引 add-only**：只处理新文件，不自动处理修改/删除（触发 warning 建议 force-rebuild）。FAISS 对删除/重排不友好，add-only 实现简单可靠，覆盖 90% 使用场景。
- **多轮历史传入方式**：session_state 中 assistant 消息额外存 `answer` 字段（原始答案，不含 Sources 格式），`build_chat_history` 优先读此字段，避免 Sources 格式字符串污染 LLM 记忆。
- **BM25 缓存键用 `id(store)`**：Streamlit `@st.cache_resource` 保证同进程内 store 对象身份稳定，`id()` 简单可靠，无需引入额外哈希逻辑。
- **流式模式 partial_debug**：流式版本无法在流完成前获知 `used_remote_llm`/`fallback_triggered` 等 LLM meta，这些字段在 partial_debug 中为 None，调试面板用文字说明"生成耗时含在网络中"。

### 未完成 / 待跟进
- 增量索引目前只支持 add-only；已修改/删除文件需手动 `--force-rebuild`，未来可做 diff 更新
- 会话持久化（跨 session 的对话历史 JSON/SQLite）尚未实现
- 查询改写（HyDE / query expansion）尚未实现

---

## 2026-03-10 — Phase 9：Hybrid Retrieval + Cross-Encoder Reranking + 安全修复

**触发原因**：用户要求记录

### 概述
本次会话在 Phase 8 基础上实现了两项检索增强功能：BM25 + Dense 混合检索（RRF 融合）和 Cross-Encoder 重排。同时修复了 `.env` 未被 `.gitignore` 屏蔽、API Key 泄露的安全问题，并补全了 `.env` 和 `.env.example` 的注释说明。全量测试从 82 passed 升至 90 passed。

### 改动清单

**检索增强（Phase 9）**
- `retrieval/retriever.py`：新增 `_bm25_retrieve`、`_rrf_fusion`、`rerank_results`、`hybrid_retrieve`，以及 `has_rank_bm25`、`has_cross_encoder` 可用性检测；原 `retrieve_top_k` 保持不变
- `retrieval/__init__.py`：导出新增的 5 个函数
- `pipeline/query.py`：`answer_with_store` 新增 `use_hybrid`、`use_rerank`、`rerank_initial_k`、`rerank_model` 参数；debug info 补充 hybrid/rerank 状态字段
- `config/defaults.py`：新增 `DEFAULT_USE_HYBRID`、`DEFAULT_USE_RERANK`、`DEFAULT_RERANK_INITIAL_K`、`DEFAULT_RERANK_MODEL` 四个常量
- `cli.py`：`query`/`chat`/`eval` 三个子命令均新增 `--hybrid/--no-hybrid`、`--rerank/--no-rerank`、`--rerank-initial-k` 选项
- `web_app.py`：侧边栏新增"检索增强"区块（hybrid checkbox、rerank checkbox、rerank_initial_k 输入框）；debug 面板补充对应字段
- `requirements.txt`：新增 `rank-bm25`
- `tests/test_retriever.py`：新增 8 个测试（TestBM25 / TestRRFFusion / TestHybridRetrieve）

**安全修复**
- `.gitignore`：新增 `.env` 屏蔽规则
- `.env`：补充详细注释（各 provider 含义、key 用途说明）；执行 `git rm --cached .env` 移出追踪
- `.env.example`：新建，含占位符和完整注释，供协作者参考

### 决策与背景
- Hybrid 和 Rerank 默认均关闭（`False`），向后完全兼容，用户按需在 CLI/Web 启用
- BM25 使用 `rank-bm25` 库，不可用时 `hybrid_retrieve` 自动降级为纯 Dense
- Cross-Encoder 模型实例做了模块级缓存（`_ce_cache`），避免同一进程内重复加载
- `.env` 历史 commit 中存有旧 key（已由用户撤销轮换），用户明确不清理 git 历史，仅做后续屏蔽

### 未完成 / 待跟进
- Evaluation Dashboard（Web UI 里加 Chat / Evaluation 两个 tab）：用户确认方向后尚未实现
- 文档更新 skill（保证每次改完代码自动同步 PROGRESS / README / TECHNICAL）：用户提出需求，待用 skill-creator 创建

---

## 2026-03-10 16:30 — 文档补全：TECHNICAL.md 同步 Phase 9 + work-logger skill 修复

**触发原因**：用户要求

### 概述
将 TECHNICAL.md 全面同步 Phase 9 内容（Hybrid Retrieval / BM25 / RRF / Cross-Encoder Rerank），更新了系统总览数据流图、4.1 Retriever 章节、pipeline/query.py 说明、Web UI 说明、关键设计决策和 debug 结构示例。同时修复了 work-logger skill 的执行顺序问题（强制要求 work-logger 为最后一步），并修正了上一条 worklog 中"PROGRESS.md 未同步"的错误记录（实际已同步）。

### 改动清单
- `TECHNICAL.md`：同步 Phase 9 全部内容（数据流图、Retriever 章节重写、pipeline 说明、Web UI、设计决策、debug 结构）
- `PROGRESS.md`：进度快照更新至 Phase 9，新增 Phase 9 完整任务清单（上一轮已完成，此处修正记录）
- `worklog.md`：新增本条记录；修正上条"未完成"中的错误项
- `C:\Users\86579\.claude\skills\work-logger\skill.md`：新增"执行顺序"规则，强制 work-logger 为最后操作

### 决策与背景
- work-logger 顺序问题根因：skill 被调用时其他操作（PROGRESS.md 更新）尚未完成，导致记录不完整。修复方式是在 skill 说明中加硬性规则，而非依赖 Claude 自觉判断。

### 未完成 / 待跟进
- Evaluation Dashboard（Web UI 加 Chat / Eval 两 tab）：待实现
- 文档更新 skill：待用 skill-creator 创建
