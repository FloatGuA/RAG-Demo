# RAG-Demo

基于课程资料（PDF）的 RAG 问答 Demo：输入 PDF + 问题，输出答案 + 来源。

## 文档与进度

- [Outline.md](./Outline.md) — 设计大纲与模块划分
- [Memory.md](./Memory.md) — 项目记忆与实现记录（续接进度用）
- [Todolist.md](./Todolist.md) — 待办与阶段任务
- [tests/README.md](./tests/README.md) — 单元测试说明与覆盖清单

## 当前进度（Phase 2 已完成）

- **数据**：PDF 放在 `data/`，chunk 缓存在 `artifacts/chunks/chunks.json`，vectors 缓存在 `artifacts/vectors/vectors.json`
- **运行**：`pip install -r requirements.txt`，然后 `python main.py`（cache-first，自动处理 chunk + vectors；FAISS 可用时会生成 `artifacts/index/faiss.index`）
- **测试**：`python -m pytest tests/ -v`（当前 37 passed；加 `-s` 可看中英双语输出）

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
