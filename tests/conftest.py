"""
测试 fixtures：创建临时 PDF、Document 等
"""
import tempfile
from pathlib import Path

import pytest
from pypdf import PdfWriter

from loader import Document


@pytest.fixture
def temp_pdf():
    """创建临时单页 PDF（空白页），用于 loader 测试"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        path = Path(f.name)
    try:
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        writer.write(path)
        yield path
    finally:
        path.unlink(missing_ok=True)


@pytest.fixture
def sample_document():
    """用于 chunking 测试的示例 Document"""
    long_text = "This is sentence one. This is sentence two. " * 30  # ~900 chars
    return Document(content=long_text, source="test.pdf", page=1)


@pytest.fixture
def empty_document():
    """空内容 Document"""
    return Document(content="", source="empty.pdf", page=1)


@pytest.fixture
def short_document():
    """短内容 Document（不足一个 chunk）"""
    return Document(content="Short text.", source="short.pdf", page=1)
