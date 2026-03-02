# Tutorial_main

## 1. 模块作用（What）

`main.py` 是当前项目 Phase 1 的统一入口，用于串联 loader + chunking + 持久化。

## 2. 设计思路（Why）

- 提供单一可执行入口，便于演示与后续扩展。
- 采用 cache-first，避免重复处理 PDF，提升迭代效率。
- 提供参数化能力（chunk size / overlap / preview / force rebuild）。

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
- `main()`：
  - 执行流程并打印来源（cache/migrated/rebuild）和预览
  - 对控制台编码做安全输出处理，避免 Windows 终端异常字符报错

## 4. 数据流（Data Flow）

`CLI args -> build_or_load_chunks -> List[Chunk] -> console preview`

内部调用链：

`main.py -> loader.py + chunking.py -> artifacts/chunks/chunks.json`

## 5. 模块关系（上下游）

- 上游：命令行参数、`data/`、已有缓存文件
- 下游：
  - 当前：控制台输出与本地缓存
  - 后续：可扩展为 embedding/retrieval 的统一 pipeline 入口
