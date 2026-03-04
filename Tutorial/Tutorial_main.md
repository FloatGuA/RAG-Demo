# Tutorial_main

## 1. 模块作用（What）

`main.py` 是当前项目统一入口，用于串联 offline pipeline（loader/chunking/embedding/index）和 online pipeline（retrieval/prompt/generator/formatter）。

## 2. 设计思路（Why）

- 提供单一可执行入口，便于演示与后续扩展。
- 采用 cache-first，避免重复处理 PDF，提升迭代效率。
- 提供参数化能力（chunk 参数 + query 参数 + LLM provider 参数）。

## 3. 核心实现（How）

- `build_or_load_chunks(...)`：
  - 优先加载 `artifacts/chunks/chunks.json`
  - 若有旧缓存 `storage/chunks.json` 则迁移
  - 否则从 `data/`（支持 `pdf/pptx/docx/md`）重新构建并保存
- `parse_args()`：
  - `--force-rebuild`
  - `--chunk-size`
  - `--overlap`
  - `--preview`
  - `--query` / `--top-k`
  - `--llm-provider` / `--llm-model` / `--llm-base-url`
  - `--llm-timeout` / `--llm-max-retries` / `--no-llm-fallback-local`
- `main()`：
  - 执行离线流程并打印来源（cache/migrated/rebuild）和预览
  - 若传入 query，则执行在线问答并输出 answer + sources
  - 对控制台编码做安全输出处理，避免 Windows 终端异常字符报错

## 4. 数据流（Data Flow）

`CLI args -> offline build/load -> (optional) online query -> answer + sources`

内部调用链：

`main.py -> loader/chunking/embedding/retriever/prompt/generator/formatter -> artifacts/*`

## 5. 模块关系（上下游）

- 上游：命令行参数、`.env` 配置、`data/`、已有缓存文件
- 下游：控制台输出、本地缓存、在线问答结果

## 6. 常用运行方式

- 仅离线构建：
  - `python main.py --preview 3`
- 强制重建：
  - `python main.py --force-rebuild`
- 在线问答（默认读取 `.env`）：
  - `python main.py --query "什么是 RAG？" --top-k 3`

## 7. 参数优先级

- 参数优先级：`CLI 显式参数 > 系统环境变量 > .env > 代码默认值`
- 推荐做法：固定基础配置在 `.env`，实验参数用 CLI 覆盖

## 8. 异常与边界行为

- `data/` 无 PDF：离线构建会失败并提示路径问题
- `top_k <= 0`：由检索层抛参数异常
- 终端编码异常字符：`main.py` 已做安全打印保护

## 9. 测试与验证建议

- 主流程回归：`python -m pytest tests/ -v`
- 只验证在线路径：重点跑 `tests/test_retriever.py`、`tests/test_prompt.py`、`tests/test_generator.py`

## 10. 技术栈

- `argparse`：CLI 参数管理
- `pathlib`：缓存目录与文件路径管理
- `loader/chunking/embedding/retriever/prompt/generator/formatter`：流水线模块编排
- `.env` 读取：默认参数注入

## 11. 端到端流程（这一部分如何工作）

1. 解析 CLI 参数（含 `.env` 默认值）  
2. 执行离线阶段：
   - `build_or_load_chunks()`
   - `build_or_load_vectors()`
   - `build_or_load_faiss_index()`  
3. 若带 `--query`，执行在线问答：
   - `retrieve_top_k()`
   - （可选）低相关度过滤
   - `build_prompt()`
   - `generate_answer()`
   - `format_response()`  
4. 输出 Answer 与 Sources 到终端

## 12. 核心函数在做什么，为什么这样做

- `build_or_load_chunks()/vectors()/faiss_index()`：
  - **做什么**：统一缓存优先策略
  - **为什么**：保证同一入口能稳定复用中间产物，减少重复计算
- `parse_args()`：
  - **做什么**：集中管理所有运行参数
  - **为什么**：便于实验复现（参数即实验配置）
- `main()`：
  - **做什么**：编排 offline + online 全流程
  - **为什么**：项目需要一个单命令可运行入口
