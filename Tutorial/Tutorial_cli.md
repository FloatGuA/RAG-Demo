# Tutorial_cli

## 1. 模块作用（What）

`cli.py` 是项目的**统一命令行入口**，基于 typer 框架将 `build / query / chat / eval / web` 五个操作整合到一个命令下。

## 2. 设计思路（Why）

- 重构前项目有 4 个分散入口（`main.py`、`app.py`、`evaluation.py`、`streamlit run web_app.py`），新用户难以判断该用哪个。
- LLM 相关参数（provider / model / timeout / retries 等）在三个文件各定义一遍，维护成本高。
- 统一为 `python cli.py <子命令>` 后，所有操作一目了然；旧入口保留向后兼容。

## 3. 核心实现（How）

### 子命令总览

| 子命令 | 用途 | 对应旧入口 |
|--------|------|------------|
| `build` | 离线构建 chunks / vectors / FAISS | `python main.py`（无 `--query`） |
| `query` | 单次问答 | `python app.py --query "..."` |
| `chat` | 交互式 REPL | `python app.py`（无 `--query`） |
| `eval` | 批量评估 | `python evaluation.py` |
| `web` | 启动 Streamlit | `streamlit run web_app.py` |

### 参数设计

- 共享 LLM 参数（provider / model / base_url / timeout / retries / no-fallback）在每个需要的子命令中通过 `typer.Option()` 定义。
- 默认值从 `config.env.load_env_defaults()` + `config.env.get_llm_default()` 动态获取，支持 `.env` 文件覆盖。
- `build` 子命令不需要 LLM 参数；`web` 子命令通过 subprocess 启动 Streamlit，参数由 Web UI 侧边栏控制。

### 关键实现细节

- `chat` 的交互循环（`while True: input() → answer → print`）留在 `cli.py` 而非 `pipeline/`，因为它涉及 IO 操作。
- `web` 子命令通过 `subprocess.run([sys.executable, "-m", "streamlit", "run", "web_app.py"])` 启动，不直接 import streamlit。
- `eval` 子命令内部 import `evaluation.load_eval_cases` 和 `evaluation.evaluate_cases`（指标计算逻辑），管线调用走 `pipeline.answer_with_store`。

## 4. 数据流（Data Flow）

```
用户 → python cli.py <子命令> [参数]
                ↓
    cli.py 解析参数（typer）
                ↓
    调用 pipeline/ 核心函数
                ↓
    结果输出到终端 / 文件 / Streamlit
```

## 5. 模块关系（上下游）

- **依赖**：`pipeline`（核心逻辑）、`config`（配置）、`evaluation`（评估指标）
- **不依赖**：`app.py`、`main.py`、`web_app.py`（这些是旧入口，与 `cli.py` 平级）
- `web` 子命令通过 subprocess 调用 `web_app.py`，不存在 import 依赖

## 6. 使用示例

```bash
# 离线构建（首次）
python cli.py build --force-rebuild

# 单次提问
python cli.py query "What is dynamic programming?" --top-k 3 --debug

# 交互模式
python cli.py chat --llm-provider openai_compatible --llm-model qwen-plus

# 批量评估
python cli.py eval --eval-set eval/eval_set.example.json --llm-provider local

# 启动 Web UI
python cli.py web

# 查看帮助
python cli.py --help
python cli.py query --help
```

## 7. 与旧入口的关系

| 旧命令 | 等价新命令 | 是否仍可用 |
|--------|-----------|-----------|
| `python main.py` | `python cli.py build` | 是 |
| `python main.py --query "..."` | `python cli.py query "..."` | 是 |
| `python app.py` | `python cli.py chat` | 是 |
| `python app.py --query "..."` | `python cli.py query "..."` | 是 |
| `python evaluation.py` | `python cli.py eval` | 是 |
| `streamlit run web_app.py` | `python cli.py web` | 是 |

旧入口内部已重构为从 `pipeline` / `config` 导入，行为不变。

## 8. 测试映射

- `cli.py` 本身是 UI 层薄壳，核心逻辑测试在 `tests/test_app.py`（测试 `pipeline.answer_with_store` / `pipeline.render_response`）。
- 可通过命令行手动验证：`python cli.py build`、`python cli.py query "test" --debug`。

## 9. 技术栈

- `typer`：基于 click 的现代 CLI 框架，自动生成帮助文档、参数类型校验、彩色输出
- `subprocess`：`web` 子命令启动 Streamlit 进程
- `config/`：共享配置
- `pipeline/`：核心管线

## 10. 端到端流程（这一部分如何工作）

1. 用户执行 `python cli.py <子命令> [参数]`
2. typer 解析参数并路由到对应函数
3. 函数内部从 `pipeline` 获取运行时（`build_runtime()`）
4. 调用 `pipeline.answer_with_store()` 或 `pipeline.build_or_load_*()` 执行业务逻辑
5. 将结果通过 `typer.echo()` 输出到终端

## 11. 核心函数在做什么，为什么这样做

- `build()`：
  - **做什么**：调用 pipeline 三步构建，输出构建状态与预览
  - **为什么**：让用户可以在提问前先验证离线构建是否正常
- `query()`：
  - **做什么**：接收问题，调用 pipeline 完整问答链路，输出答案
  - **为什么**：最常用操作，单命令即可得到结果
- `chat()`：
  - **做什么**：构建运行时后进入 while 循环，持续接收问题
  - **为什么**：交互式探索更适合调试和演示；IO 循环留在 UI 层保持 pipeline 零 IO
- `evaluate()`：
  - **做什么**：加载评测集、批量执行、汇总指标、写入报告
  - **为什么**：评估是验收和回归的核心环节，统一入口便于 CI 集成
- `web()`：
  - **做什么**：通过 subprocess 启动 Streamlit
  - **为什么**：Streamlit 有自己的进程模型，subprocess 是最简洁的集成方式
