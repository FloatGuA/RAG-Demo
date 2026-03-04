# Tutorial_config

## 1. 模块作用（What）

`config/` 包是项目的**共享配置层**，集中管理默认值常量、路径常量和 `.env` 文件加载逻辑，消除多个入口文件中的重复定义。

## 2. 设计思路（Why）

- 重构前，`_load_env_defaults()` 在 `main.py` 和 `app.py` 中各定义一份，默认值常量（chunk size、LLM timeout 等）在三个 CLI 入口中各写一遍。
- 任何默认值的修改都需要同步多处，容易遗漏导致行为不一致。
- 拆为独立包后，所有入口（`cli.py` / `main.py` / `app.py` / `evaluation.py` / `web_app.py`）统一 `from config import ...`，单点修改即全局生效。

## 3. 包结构

```
config/
├── __init__.py      # 便捷重导出所有公开符号
├── defaults.py      # 项目级默认值常量
├── paths.py         # artifacts / 缓存文件路径常量
└── env.py           # .env 文件加载与 LLM 默认值解析
```

## 4. 核心实现（How）

### `config/defaults.py`

定义所有可调参数的默认值，例如：

- `DEFAULT_CHUNK_SIZE = 500`
- `DEFAULT_OVERLAP = 50`
- `DEFAULT_LLM_TIMEOUT = 120.0`
- `DEFAULT_LLM_PROVIDER = "local"`

这些常量被 `pipeline/`、`cli.py`、旧入口文件的 `argparse` 共同引用。

### `config/paths.py`

集中定义 artifacts 路径：

- `CHUNKS_PATH = Path("artifacts/chunks/chunks.json")`
- `VECTORS_PATH = Path("artifacts/vectors/vectors.json")`
- `FAISS_INDEX_PATH = Path("artifacts/index/faiss.index")`
- `LEGACY_CHUNKS_PATH = Path("storage/chunks.json")`

### `config/env.py`

- `load_env_defaults(path=".env")`：解析 `.env` 文件，返回 `dict[str, str]`。支持注释行（`#`）和引号剥离。
- `get_llm_default(key, fallback, *, env_defaults)`：依次从 `os.environ` → `env_defaults` → `fallback` 取值，封装了旧代码中 `os.getenv(...) or env_defaults.get(...)` 的重复模式。

## 5. 数据流（Data Flow）

```
.env 文件 → load_env_defaults() → dict
                                    ↓
os.environ + dict → get_llm_default() → 各入口 argparse / typer Option 的 default 值
```

## 6. 模块关系（上下游）

- **被谁依赖**：`pipeline/build.py`、`pipeline/query.py`、`cli.py`、`main.py`、`app.py`、`web_app.py`
- **依赖谁**：仅依赖 Python 标准库（`pathlib`、`os`）

## 7. 参数建议与边界行为

- `.env` 文件不存在时 `load_env_defaults()` 返回空 dict，不报错。
- `get_llm_default()` 优先级：环境变量 > `.env` > fallback，确保 CI/CD 环境中环境变量可覆盖本地配置。

## 8. 测试映射

- `config/env.py` 的 `load_env_defaults` 被 `tests/test_web_app.py::test_load_env_file_reads_key_values` 间接覆盖。
- 路径常量和默认值常量为纯声明，不需独立测试。

## 9. 技术栈

- `pathlib.Path`：跨平台路径处理
- `os.getenv`：环境变量读取
- 手动 `.env` 解析（不依赖 `python-dotenv`，减少外部依赖）

## 10. 端到端流程（这一部分如何工作）

1. 项目启动时（`cli.py` / `main.py` / `app.py`），调用 `load_env_defaults(".env")` 一次性加载本地配置
2. 各 CLI 参数的 `default` 值通过 `get_llm_default()` 从环境变量和 `.env` 动态获取
3. `pipeline/build.py` 中的 `build_or_load_*` 函数引用 `config.paths` 中的路径常量来定位缓存文件
4. 默认值常量被 `pipeline/` 的函数签名直接引用，保证即使不传参也有合理行为

## 11. 核心函数在做什么，为什么这样做

- `load_env_defaults()`：
  - **做什么**：逐行解析 `.env` 文件为 key-value 字典
  - **为什么**：不引入 `python-dotenv` 依赖，保持项目轻量；同时支持注释和引号
- `get_llm_default()`：
  - **做什么**：三级回退取值（环境变量 → .env → fallback）
  - **为什么**：重构前这个逻辑在每个 `parse_args()` 中内联写了一遍，提取后消除重复且语义更清晰
