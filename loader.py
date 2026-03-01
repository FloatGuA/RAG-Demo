"""
模块1：Document Loader
读取 PDF 课程资料，输出 List[Document]
"""

from pathlib import Path
from dataclasses import dataclass

from pypdf import PdfReader


@dataclass
class Document:
    """单个文档单元，对应 PDF 的一页"""
    content: str
    source: str   # 文件名
    page: int     # 页码（从 1 开始）


def load_pdf(file_path: str | Path) -> list[Document]:
    """
    加载单个 PDF 文件，按页拆分为 Document 列表。

    Args:
        file_path: PDF 文件路径

    Returns:
        List[Document]，每页一个 Document
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF 不存在: {path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"非 PDF 文件: {path}")

    reader = PdfReader(path)
    documents = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        documents.append(Document(
            content=text.strip(),
            source=path.name,
            page=i,
        ))
    return documents


def load_pdfs_from_dir(dir_path: str | Path) -> list[Document]:
    """
    加载目录下所有 PDF 文件。

    Args:
        dir_path: 目录路径（如 data/）

    Returns:
        合并后的 List[Document]
    """
    dir_path = Path(dir_path)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"目录不存在: {dir_path}")

    all_docs = []
    for pdf_path in sorted(dir_path.glob("*.pdf")):
        all_docs.extend(load_pdf(pdf_path))
    return all_docs


if __name__ == "__main__":
    # 简单测试：加载 data/ 下的 PDF
    docs = load_pdfs_from_dir("data")
    print(f"共加载 {len(docs)} 页")
    for d in docs[:3]:
        print(f"  [{d.source} p.{d.page}] {d.content[:80]}...")
