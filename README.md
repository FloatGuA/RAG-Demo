# RAG-Demo

基于课程资料（PDF）的 RAG 问答 Demo：输入 PDF + 问题，输出答案 + 来源。

## 文档与进度

- [Outline.md](./Outline.md) — 设计大纲与模块划分
- [Memory.md](./Memory.md) — 项目记忆与实现记录（续接进度用）
- [Todolist.md](./Todolist.md) — 待办与阶段任务
- [tests/README.md](./tests/README.md) — 单元测试说明与覆盖清单

## 当前进度（Phase 4 已完成）

- **数据**：PDF 放在 `data/`，chunk 缓存在 `artifacts/chunks/chunks.json`，vectors 缓存在 `artifacts/vectors/vectors.json`
- **离线构建**：`pip install -r requirements.txt`，然后 `python main.py`（cache-first，自动处理 chunk + vectors；FAISS 可用时会生成 `artifacts/index/faiss.index`）
- **在线查询**：`python main.py --query "your question" --top-k 3`
- **应用入口（CLI UI）**：`python app.py --query "your question"`（不传 `--query` 进入交互模式）
- **对话框 Web UI**：`streamlit run web_app.py`
- **测试**：`python -m pytest tests/ -v`（当前 56 passed；加 `-s` 可看中英双语输出）

## LLM 配置（支持多 Provider）

- 项目支持 `local` / `openai` / `openai_compatible` 三种 provider（默认可在 `.env` 中设置）
- 推荐在项目根目录使用 `.env`（可参考 `.env.example`）：
  - `OPENAI_API_KEY=...`
  - `LLM_PROVIDER=openai_compatible`
  - `LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`
  - `LLM_MODEL=qwen3.5-plus`
- 示例（强制真实调用，不回退本地）：
  - `python main.py --query "What is dynamic programming?" --top-k 3 --no-llm-fallback-local`

## 30 秒快速上手

1) 在项目根目录创建 `.env`（可直接复制 `.env.example`）并至少配置：

```env
OPENAI_API_KEY=你的key
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-plus
```

2) 执行一次在线问答：

```bash
python main.py --query "What is A/B testing?" --top-k 3 --no-llm-fallback-local
```

3) 结果判定：
- 若成功输出 `Answer` 与 `Sources`，说明已完成真实 API 调用。
- 若报错（如 `model_not_found` / `AccessDenied.Unpurchased`），按报错修正模型名或权限后重试。

## 编码规范

- 文档和代码统一使用 `UTF-8` 编码保存，避免中文乱码。

---

```text
# 常用 git
git add .
git commit -m "写一句你这次改了什么"
git push




git log --oneline 看版本记录
git restore --source abc1234 文件1 文件2
```
