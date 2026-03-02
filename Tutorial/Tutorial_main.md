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
  - 否则从 `data/` 重新构建并保存
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
