# RAG-Demo

基于课程资料（PDF）的 RAG 问答 Demo：输入 PDF + 问题，输出答案 + 来源。

## 文档与进度

- [Outline.md](./Outline.md) — 设计大纲与模块划分
- [Memory.md](./Memory.md) — 项目记忆与实现记录（续接进度用）
- [Todolist.md](./Todolist.md) — 待办与阶段任务
- [tests/README.md](./tests/README.md) — 单元测试说明与覆盖清单

## 当前进度（Phase 1 已完成）

- **数据**：PDF 放在 `data/`，chunk 缓存放在 `artifacts/chunks/chunks.json`
- **运行**：`pip install -r requirements.txt`，然后 `python chunking.py`（有缓存则加载，无则从 data/ 解析并保存）
- **测试**：`pytest tests/ -v`（加 `-s` 可看中英双语输出）

---

```text
# 常用 git
git add .
git commit -m "写一句你这次改了什么"
git push
```
