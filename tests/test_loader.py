"""
loader.py 单元测试

覆盖目标：
1) 输入合法 PDF 时，返回的 Document 结构正确。
2) 输入非法路径/非法类型时，抛出预期异常。
3) 目录加载函数在空目录、非目录、正常目录下行为正确。
"""
from pathlib import Path

import pytest

from loader import Document, load_document, load_documents_from_dir, load_pdf, load_pdfs_from_dir


class TestLoadPdf:
    """load_pdf 单 PDF 加载行为"""

    def test_load_pdf_returns_list_of_documents(self, temp_pdf):
        """场景：传入有效 PDF；预期：返回 List[Document] 且至少 1 页。"""
        print("\n[TEST START] Verify load_pdf returns List[Document] with at least one page | 验证 load_pdf 返回至少一页的 Document 列表")
        print("[INPUT] Valid PDF path (temp file) | 有效 PDF 路径（临时文件）")
        print("[ACTION] Calling load_pdf(path) | 调用 load_pdf(path)")
        docs = load_pdf(temp_pdf)
        print("[EXPECTED] Return type list, len>=1, all elements are Document | 返回 list、至少 1 项、元素均为 Document")
        assert isinstance(docs, list), "load_pdf 应返回 list"
        assert len(docs) >= 1, "临时 PDF 至少应解析出 1 页"
        assert all(isinstance(d, Document) for d in docs), "列表元素应全部为 Document"
        print("[PASS] load_pdf returns valid List[Document] | load_pdf 返回合法 List[Document]\n")

    def test_load_pdf_document_has_required_fields(self, temp_pdf):
        """场景：解析成功；预期：Document 包含 content/source/page 且类型正确。"""
        print("\n[TEST START] Verify each Document has content, source, page with correct types | 验证每个 Document 含 content/source/page 且类型正确")
        print("[INPUT] Valid PDF path | 有效 PDF 路径")
        print("[ACTION] Calling load_pdf(path) | 调用 load_pdf(path)")
        docs = load_pdf(temp_pdf)
        print("[EXPECTED] Each doc has str content/source, int page>=1 | 每项含 str 的 content/source、int 的 page>=1")
        for d in docs:
            assert hasattr(d, "content") and isinstance(d.content, str), "content 应为 str"
            assert hasattr(d, "source") and isinstance(d.source, str), "source 应为 str"
            assert hasattr(d, "page") and isinstance(d.page, int), "page 应为 int"
            assert d.page >= 1, "page 应从 1 开始"
        print("[PASS] All Document fields valid | 所有 Document 字段合法\n")

    def test_load_pdf_source_is_filename(self, temp_pdf):
        """场景：读取单个文件；预期：source 字段仅为文件名。"""
        print("\n[TEST START] Verify source field equals input filename | 验证 source 字段等于输入文件名")
        print("[INPUT] PDF path:", temp_pdf, "| PDF 路径")
        print("[ACTION] Calling load_pdf(path) | 调用 load_pdf(path)")
        docs = load_pdf(temp_pdf)
        print("[EXPECTED] docs[0].source == temp_pdf.name | docs[0].source 等于文件名")
        assert docs[0].source == temp_pdf.name, "source 应与输入文件名一致"
        print("[PASS] source is filename | source 为文件名\n")

    def test_load_pdf_accepts_path_object(self, temp_pdf):
        """场景：传入 Path；预期：函数可正常工作。"""
        print("\n[TEST START] Verify load_pdf accepts Path object (not only str) | 验证 load_pdf 接受 Path 对象")
        print("[INPUT] Path(temp_pdf) | Path 对象包装的路径")
        print("[ACTION] Calling load_pdf(Path(temp_pdf)) | 调用 load_pdf(Path(...))")
        docs = load_pdf(Path(temp_pdf))
        print("[EXPECTED] Parse successfully, len(docs)>=1 | 解析成功且至少 1 页")
        assert len(docs) >= 1, "Path 输入应能正常解析 PDF"
        print("[PASS] Path input works | Path 输入正常\n")

    def test_load_pdf_file_not_found(self):
        """场景：文件不存在；预期：抛 FileNotFoundError。"""
        print("\n[TEST START] Verify FileNotFoundError when file does not exist | 验证文件不存在时抛出 FileNotFoundError")
        print("[INPUT] Non-existent path: nonexistent_file.pdf | 不存在的路径")
        print("[ACTION] Calling load_pdf('nonexistent_file.pdf') | 调用 load_pdf(...)")
        print("[EXPECTED] FileNotFoundError with message containing 'PDF 不存在' | 抛出 FileNotFoundError，消息含「PDF 不存在」")
        with pytest.raises(FileNotFoundError, match="PDF 不存在"):
            load_pdf("nonexistent_file.pdf")
        print("[PASS] FileNotFoundError raised as expected | 按预期抛出 FileNotFoundError\n")

    @pytest.mark.parametrize("filename", ["test.txt", "test.md", "test.json"])
    def test_load_pdf_non_pdf_raises(self, tmp_path, filename):
        """场景：扩展名非 .pdf；预期：抛 ValueError。"""
        print("\n[TEST START] Verify ValueError for non-PDF file extension | 验证非 .pdf 扩展名时抛出 ValueError")
        txt_file = tmp_path / filename
        txt_file.write_text("hello", encoding="utf-8")
        print("[INPUT] Non-PDF file:", filename, "| 非 PDF 文件:", filename)
        print("[ACTION] Calling load_pdf(non_pdf_path) | 调用 load_pdf(非PDF路径)")
        print("[EXPECTED] ValueError with '非 PDF 文件' | 抛出 ValueError，含「非 PDF 文件」")
        with pytest.raises(ValueError, match="非 PDF 文件"):
            load_pdf(txt_file)
        print("[PASS] ValueError raised as expected | 按预期抛出 ValueError\n")


class TestLoadPdfsFromDir:
    """load_pdfs_from_dir 目录加载行为"""

    def test_load_from_nonexistent_dir_raises(self):
        """场景：目录不存在；预期：抛 NotADirectoryError。"""
        print("\n[TEST START] Verify NotADirectoryError when directory does not exist | 验证目录不存在时抛出 NotADirectoryError")
        print("[INPUT] Non-existent dir: nonexistent_dir_xyz | 不存在的目录")
        print("[ACTION] Calling load_pdfs_from_dir(...) | 调用 load_pdfs_from_dir(...)")
        print("[EXPECTED] NotADirectoryError with '目录不存在' | 抛出 NotADirectoryError，含「目录不存在」")
        with pytest.raises(NotADirectoryError, match="目录不存在"):
            load_pdfs_from_dir("nonexistent_dir_xyz")
        print("[PASS] NotADirectoryError raised as expected | 按预期抛出 NotADirectoryError\n")

    def test_load_from_dir_returns_list(self):
        """场景：传入 data 目录；预期：返回 List[Document]。"""
        print("\n[TEST START] Verify load_pdfs_from_dir returns List[Document] | 验证 load_pdfs_from_dir 返回 List[Document]")
        print("[INPUT] Directory: data | 目录 data")
        print("[ACTION] Calling load_pdfs_from_dir('data') | 调用 load_pdfs_from_dir('data')")
        docs = load_pdfs_from_dir("data")
        print("[EXPECTED] Return list of Document (may be empty) | 返回 Document 列表（可能为空）")
        assert isinstance(docs, list), "返回值应为 list"
        # data 可能为空（无 PDF）或有多页
        assert all(isinstance(d, Document) for d in docs), "列表元素应为 Document"
        print("[PASS] Return type and element type correct | 返回类型与元素类型正确\n")

    @pytest.mark.skipif(
        not Path("data").exists() or not list(Path("data").glob("*.pdf")),
        reason="需要 data/ 下存在 PDF 文件",
    )
    def test_load_from_data_dir_integration(self):
        """场景：真实数据目录；预期：成功加载并验证第一页关键字段。"""
        print("\n[TEST START] Integration: load from real data/ dir and check first page | 集成：从 data/ 加载并校验第一页")
        print("[INPUT] Directory: data (with PDFs) | 目录 data（含 PDF）")
        print("[ACTION] Calling load_pdfs_from_dir('data') | 调用 load_pdfs_from_dir('data')")
        docs = load_pdfs_from_dir("data")
        print("[EXPECTED] len(docs)>0, first doc source ends with .pdf, page==1 | 至少 1 页，首项 source 以 .pdf 结尾、page 为 1")
        assert len(docs) > 0, "data 下存在 PDF 时应解析出至少 1 页"
        # 校验第一页结构
        d = docs[0]
        assert d.source.endswith(".pdf"), "source 应包含 .pdf 后缀"
        assert d.page == 1, "第一页 page 应为 1"
        print("[PASS] Integration test passed | 集成测试通过\n")


class TestMultiFormatLoader:
    """多格式文档加载行为"""

    def test_load_document_markdown(self, tmp_path):
        print("\n[TEST START] Load markdown as document | 加载 Markdown 文档")
        md = tmp_path / "note.md"
        md.write_text("# Title\n\nThis is markdown content.", encoding="utf-8")
        print("[ACTION] call load_document(.md) | 调用 load_document(.md)")
        docs = load_document(md)
        print("[EXPECTED] one Document with page=1 | 返回 1 条 Document，page=1")
        assert len(docs) == 1
        assert docs[0].source == "note.md"
        assert docs[0].page == 1
        assert "markdown content" in docs[0].content
        print("[PASS] markdown loader ok | Markdown 加载正确\n")

    def test_load_documents_from_dir_mixed_pdf_and_md(self, tmp_path, temp_pdf):
        print("\n[TEST START] Load mixed pdf+md from dir | 从目录加载 PDF+MD 混合文档")
        target_pdf = tmp_path / "sample.pdf"
        target_pdf.write_bytes(Path(temp_pdf).read_bytes())
        (tmp_path / "readme.md").write_text("hello md", encoding="utf-8")
        print("[ACTION] call load_documents_from_dir(tmp_path) | 调用 load_documents_from_dir(tmp_path)")
        docs = load_documents_from_dir(tmp_path)
        print("[EXPECTED] docs include .pdf and .md sources | 结果包含 .pdf 与 .md 来源")
        sources = {d.source for d in docs}
        assert "sample.pdf" in sources
        assert "readme.md" in sources
        assert all(isinstance(d, Document) for d in docs)
        print("[PASS] mixed format dir loader ok | 混合格式目录加载正确\n")

    def test_load_document_unsupported_suffix_raises(self, tmp_path):
        print("\n[TEST START] Unsupported suffix raises | 不支持扩展名抛错")
        p = tmp_path / "raw.txt"
        p.write_text("x", encoding="utf-8")
        print("[ACTION] call load_document(.txt) | 调用 load_document(.txt)")
        print("[EXPECTED] ValueError with unsupported type | 抛出 ValueError")
        with pytest.raises(ValueError, match="不支持的文件类型"):
            load_document(p)
        print("[PASS] unsupported suffix validation ok | 不支持扩展名校验正确\n")
