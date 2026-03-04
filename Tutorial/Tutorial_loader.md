# Tutorial_loader

## 1. 模块作用（What）

`loader.py` 负责读取多类型课程文档，并转换为结构化 `Document`：

- `content`: 页文本
- `source`: 文件名
- `page`: 页码（从 1 开始）

## 2. 设计思路（Why）

- 后续 chunk/retrieval 都依赖统一输入结构，先标准化文档对象。
- 对不同文档源（PDF/PPTX/DOCX/MD）统一成同一数据结构，减少下游复杂度。
- 按页/按幻灯片/按文件统一保留 `source + page`，便于来源追溯。
- 提供“统一入口 + 兼容旧接口”，平滑升级不破坏现有流程。

## 3. 核心实现（How）

- `load_document(file_path)`：统一单文件入口（按扩展名分发）
  - `.pdf` -> `load_pdf()`
  - `.pptx` -> `load_pptx()`
  - `.docx` -> `load_docx()`
  - `.md` -> `load_markdown()`
- `load_documents_from_dir(dir_path)`：
  - 校验目录存在
  - 扫描受支持格式文件
  - 汇总为一个 `List[Document]`
- `load_pdfs_from_dir(dir_path)`：
  - 兼容旧接口，仅加载 `*.pdf`

## 4. 数据流（Data Flow）

`多格式文件路径 / data 目录 -> load_document/load_documents_from_dir -> List[Document]`

## 5. 模块关系（上下游）

- 上游：`data/` 中的多类型文档（PDF/PPTX/DOCX/MD）
- 下游：`chunking.py` 的 `chunk_document()` / `chunk_documents()`

## 6. 接口细节（Inputs / Outputs）

- **数据结构**：`Document(content: str, source: str, page: int)`
- **函数 1**：`load_document(file_path: str | Path) -> list[Document]`
- **函数 2**：`load_documents_from_dir(dir_path: str | Path) -> list[Document]`
- **兼容函数**：`load_pdfs_from_dir(dir_path: str | Path) -> list[Document]`

## 7. 异常与边界行为

- 文件不存在：`FileNotFoundError`
- 扩展名不在支持列表：`ValueError`
- 目录路径无效：`NotADirectoryError`
- 第三方解析依赖缺失（docx/pptx）：`RuntimeError`（提示安装依赖）
- 文档文本为空：`content` 可能为空字符串（后续由 chunking 过滤）

## 8. 测试映射

- 对应：`tests/test_loader.py`
- 覆盖点：
  - 基础读取返回类型
  - `source/page` 字段正确性
  - 非法路径/非法扩展名异常
  - 多格式入口（md）与混合目录加载
  - `data/` 目录集成加载（pdf 兼容路径）

## 9. 快速验证

- 单文件：`load_document("data/xxx.pdf")` / `load_document("data/xxx.md")`
- 目录批量：`load_documents_from_dir("data")`
- 兼容旧调用：`load_pdfs_from_dir("data")`
- 自测：`python -m pytest tests/test_loader.py -v`

## 10. 技术栈

- `Python 3`：模块与数据结构实现
- `pypdf`：PDF 解析
- `python-pptx`：PPTX 幻灯片文本提取
- `python-docx`：DOCX 段落文本提取
- `dataclasses`：`Document` 结构化表示
- `pathlib`：跨平台路径处理

## 11. 端到端流程（这一部分如何工作）

1. 输入文件路径（或目录）  
2. 统一入口根据扩展名路由到对应解析器  
3. 解析文本并生成 `Document(content, source, page)`  
4. 汇总输出 `List[Document]`  
5. 交给 `chunking.py` 执行切块

## 12. 核心函数在做什么，为什么这样做

- `load_document()`：负责“单文件统一分发”
  - **做什么**：识别文件类型并调用对应 loader
  - **为什么**：避免下游感知多格式差异，统一入口最易维护
- `load_pdf()`：负责“PDF -> 多页 Document”
  - **做什么**：读取一份 PDF，逐页生成结构化对象
  - **为什么**：按页保留来源信息，便于后续 `source/page` 引用
- `load_pptx()/load_docx()/load_markdown()`：负责“各格式文本提取”
  - **做什么**：按格式提取文本并标准化到 `Document`
  - **为什么**：把格式差异封装在 loader 层，下游只处理统一结构
- `load_documents_from_dir()`：负责“目录多格式批量加载”
  - **做什么**：扫描并加载所有受支持文件
  - **为什么**：真实知识库通常是混合格式，不能只支持 PDF
