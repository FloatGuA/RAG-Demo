# Tutorial_loader

## 1. 模块作用（What）

`loader.py` 负责读取课程 PDF，并将每一页转换为结构化 `Document`：

- `content`: 页文本
- `source`: 文件名
- `page`: 页码（从 1 开始）

## 2. 设计思路（Why）

- 后续 chunk/retrieval 都依赖统一输入结构，先标准化文档对象。
- 按页拆分可天然保留来源页码，便于后续来源标注。
- 入口分单文件与目录两种，方便开发与批量处理。

## 3. 核心实现（How）

- `load_pdf(file_path)`：
  - 校验路径存在、扩展名为 `.pdf`
  - 用 `pypdf.PdfReader` 读取页面
  - 每页生成一个 `Document`
- `load_pdfs_from_dir(dir_path)`：
  - 校验目录存在
  - 遍历目录下所有 `*.pdf`
  - 汇总为一个 `List[Document]`

## 4. 数据流（Data Flow）

`PDF 文件路径 / data 目录 -> load_pdf/load_pdfs_from_dir -> List[Document]`

## 5. 模块关系（上下游）

- 上游：`data/` 中的课程 PDF
- 下游：`chunking.py` 的 `chunk_document()` / `chunk_documents()`
