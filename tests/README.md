# Tests 使用说明

本目录包含项目的单元测试：

- `test_loader.py`：`loader.py` 的测试
- `test_chunking.py`：`chunking.py` 的测试
- `test_storage_chunks.py`：`ts20260301_storage_chunks.py` 的测试
- `conftest.py`：测试共用的 fixtures

---

## 1. 在终端运行测试（最常用）

在项目根目录执行：

```bash
pytest tests/ -v
```

或：

```bash
python -m pytest tests/ -v
```

测试结果会直接输出在终端中。

---

## 2. 在 Cursor / VS Code 里运行

1. 打开 `tests/test_loader.py` 或 `tests/test_chunking.py`
2. 在测试函数旁点击 `Run Test` / `Debug Test`
3. 在 `Test Explorer` 或 `Output` 面板查看结果

---

## 3. 常用输出参数

更简短的错误栈：

```bash
pytest tests/ -v --tb=short
```

显示 `print` 输出（含中英双语测试说明，便于学习与调试）：

```bash
pytest tests/ -v -s
```

每条测试会按 [TEST START]、[INPUT]、[ACTION]、[EXPECTED]、[PASS] 格式输出中英文说明。

---

## 4. 生成 HTML 测试报告（可选）

先安装插件：

```bash
pip install pytest-html
```

再生成报告：

```bash
pytest tests/ -v --html=report.html
```

然后用浏览器打开 `report.html` 查看结果。

---

## 5. 当前项目建议

每完成一个模块后，执行：

```bash
pytest tests/ -v
```

全部通过后再继续推进下一步开发。

---

## 6. 当前测试覆盖清单（通过后可作为“验证说明”）

### `test_loader.py`

- `load_pdf` 正常输入：返回 `List[Document]`，且字段类型正确
- `source` 字段：应与输入文件名一致
- 输入兼容性：支持 `Path` 对象
- 异常处理：
  - 文件不存在 -> `FileNotFoundError`
  - 非 PDF 扩展名 -> `ValueError`
- `load_pdfs_from_dir`：
  - 非目录输入 -> `NotADirectoryError`
  - 正常目录 -> 返回 `List[Document]`
  - 集成场景（`data/` 有 PDF）-> 至少解析出 1 页，且第一页 `page=1`

### `test_chunking.py`

- `chunk_document`：
  - 空文本 -> `[]`
  - 短文本 -> 1 个 chunk，内容/元数据一致
  - 长文本 -> 多 chunk
  - 每个 chunk 字段完整且类型正确
  - `source/page` 在切分后不变
  - 边界校验：`overlap >= chunk_size` 抛 `ValueError`
  - 长度约束：chunk 长度不显著超过阈值（考虑断句余量）
  - 质量约束：不产出空 chunk
- `chunk_documents`：
  - 空输入 -> 空输出
  - 多文档输入 -> 合并输出并保留来源
  - 顺序约束：输出顺序与输入文档顺序一致
- 序列化辅助：
  - `chunks_to_dicts` 与 `dicts_to_chunks` 可往返保持一致

### `test_storage_chunks.py`

- `save_chunks` + `load_chunks`：保存/加载后数据结构完全一致
- 目录自动创建：保存时自动创建父目录
- 异常处理：
  - 文件不存在 -> `FileNotFoundError`
  - JSON 根结构不是 list -> `ValueError`
