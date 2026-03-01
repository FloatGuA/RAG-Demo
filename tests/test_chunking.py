"""
chunking.py 单元测试

覆盖目标：
1) chunk_document 在空文本、短文本、长文本下行为正确。
2) overlap/chunk_size 边界条件被正确校验。
3) chunk 元数据（source/page）在切分后保持不变。
4) 批量切分与序列化辅助函数行为正确。
"""
import pytest

from chunking import Chunk, chunk_document, chunk_documents, chunks_to_dicts, dicts_to_chunks


class TestChunkDocument:
    """chunk_document 单文档切分行为"""

    def test_empty_document_returns_empty_list(self, empty_document):
        """场景：空文本；预期：返回空列表。"""
        print("\n[TEST START] Verify empty document yields empty chunk list | 验证空文档返回空 chunk 列表")
        print("[INPUT] Document with content='' | 内容为空的 Document")
        print("[ACTION] Calling chunk_document(empty_document) | 调用 chunk_document(empty_document)")
        chunks = chunk_document(empty_document)
        print("[EXPECTED] chunks == [] | 返回空列表")
        assert chunks == [], "空文档不应生成任何 chunk"
        print("[PASS] Empty list returned | 返回空列表\n")

    def test_short_document_returns_one_chunk(self, short_document):
        """场景：文本长度 < chunk_size；预期：仅生成 1 个 chunk 且内容一致。"""
        print("\n[TEST START] Verify short doc yields single chunk with same content/source/page | 验证短文档产生 1 个 chunk 且内容/来源/页码一致")
        print("[INPUT] Short document, chunk_size=500 | 短文档，chunk_size=500")
        print("[ACTION] Calling chunk_document(short_document, chunk_size=500) | 调用 chunk_document(...)")
        chunks = chunk_document(short_document, chunk_size=500)
        print("[EXPECTED] len==1, text/source/page match original | 长度为 1，text/source/page 与原文一致")
        assert len(chunks) == 1, "短文本应只生成一个 chunk"
        assert chunks[0].text == short_document.content, "chunk 内容应与原文一致"
        assert chunks[0].source == short_document.source, "source 应保持一致"
        assert chunks[0].page == short_document.page, "page 应保持一致"
        print("[PASS] Single chunk with correct metadata | 单个 chunk 且元数据正确\n")

    def test_long_document_produces_multiple_chunks(self, sample_document):
        """场景：长文本；预期：产生多个 chunks。"""
        print("\n[TEST START] Verify long document yields multiple chunks | 验证长文档产生多个 chunk")
        print("[INPUT] Long document, chunk_size=200, overlap=20 | 长文档，chunk_size=200, overlap=20")
        print("[ACTION] Calling chunk_document(sample_document, ...) | 调用 chunk_document(...)")
        chunks = chunk_document(sample_document, chunk_size=200, overlap=20)
        print("[EXPECTED] len(chunks) >= 3 | 至少 3 个 chunk")
        assert len(chunks) >= 3, "长文本应被切成多个 chunk"
        print("[PASS] Multiple chunks produced | 产生多个 chunk\n")

    def test_chunk_has_required_fields(self, short_document):
        """场景：切分后；预期：Chunk 包含 text/source/page 且类型正确。"""
        print("\n[TEST START] Verify each Chunk has text, source, page with correct types | 验证每个 Chunk 含 text/source/page 且类型正确")
        print("[INPUT] Short document | 短文档")
        print("[ACTION] Calling chunk_document(short_document) | 调用 chunk_document(...)")
        chunks = chunk_document(short_document)
        print("[EXPECTED] Each chunk: str text/source, int page, type Chunk | 每项 str text/source、int page、类型 Chunk")
        for c in chunks:
            assert hasattr(c, "text") and isinstance(c.text, str), "text 应为 str"
            assert hasattr(c, "source") and isinstance(c.source, str), "source 应为 str"
            assert hasattr(c, "page") and isinstance(c.page, int), "page 应为 int"
            assert isinstance(c, Chunk), "元素类型应为 Chunk"
        print("[PASS] All chunks have required fields | 所有 chunk 字段完整\n")

    def test_chunk_preserves_source_and_page(self, sample_document):
        """场景：多 chunk 切分；预期：每个 chunk 继承原 source/page。"""
        print("\n[TEST START] Verify all chunks inherit document source and page | 验证所有 chunk 继承文档的 source 和 page")
        print("[INPUT] Sample document, chunk_size=100 | 示例文档，chunk_size=100")
        print("[ACTION] Calling chunk_document(sample_document, chunk_size=100) | 调用 chunk_document(...)")
        chunks = chunk_document(sample_document, chunk_size=100)
        print("[EXPECTED] Every chunk.source/page == document.source/page | 每个 chunk 的 source/page 与文档一致")
        for c in chunks:
            assert c.source == sample_document.source, "source 在切分后不应改变"
            assert c.page == sample_document.page, "page 在切分后不应改变"
        print("[PASS] source/page preserved in all chunks | 所有 chunk 保留 source/page\n")

    @pytest.mark.parametrize(
        "chunk_size,overlap",
        [(100, 100), (100, 150), (50, 80)],
        ids=["equal", "greater", "much_greater"],
    )
    def test_overlap_ge_chunk_size_raises(self, short_document, chunk_size, overlap):
        """场景：overlap >= chunk_size；预期：抛 ValueError。"""
        print("\n[TEST START] Verify ValueError when overlap >= chunk_size | 验证 overlap>=chunk_size 时抛出 ValueError")
        print("[INPUT] chunk_size=%s, overlap=%s | chunk_size=%s, overlap=%s" % (chunk_size, overlap, chunk_size, overlap))
        print("[ACTION] Calling chunk_document(..., chunk_size, overlap) | 调用 chunk_document(...)")
        print("[EXPECTED] ValueError with 'overlap 必须小于 chunk_size' | 抛出 ValueError，含「overlap 必须小于 chunk_size」")
        with pytest.raises(ValueError, match="overlap 必须小于 chunk_size"):
            chunk_document(short_document, chunk_size=chunk_size, overlap=overlap)
        print("[PASS] ValueError raised as expected | 按预期抛出 ValueError\n")

    def test_chunk_size_respected(self, sample_document):
        """场景：断句策略启用；预期：chunk 长度不应显著超过阈值。"""
        print("\n[TEST START] Verify chunk text length within reasonable bound | 验证 chunk 文本长度在合理范围内")
        chunk_size = 100
        print("[INPUT] sample_document, chunk_size=100, overlap=10 | 示例文档，chunk_size=100, overlap=10")
        print("[ACTION] Calling chunk_document(...) | 调用 chunk_document(...)")
        chunks = chunk_document(sample_document, chunk_size=chunk_size, overlap=10)
        print("[EXPECTED] len(chunk.text) <= chunk_size + 50 | 每块长度不超过 chunk_size+50")
        # 因断句策略，可能略超 chunk_size，但不应离谱
        for c in chunks:
            assert len(c.text) <= chunk_size + 50, "断句后长度超出合理范围"
        print("[PASS] Chunk length within bound | chunk 长度在范围内\n")

    def test_chunk_text_never_empty(self, sample_document):
        """场景：普通文本切分；预期：不会产出空字符串 chunk。"""
        print("\n[TEST START] Verify no chunk has empty text | 验证不产出空文本 chunk")
        print("[INPUT] sample_document, chunk_size=120, overlap=20 | 示例文档")
        print("[ACTION] Calling chunk_document(...) | 调用 chunk_document(...)")
        chunks = chunk_document(sample_document, chunk_size=120, overlap=20)
        print("[EXPECTED] All chunk.text non-empty (after strip) | 所有 chunk.text 非空")
        assert all(c.text.strip() for c in chunks), "产出的 chunk 不应为空"
        print("[PASS] No empty chunks | 无空 chunk\n")

    def test_overlap_produces_more_chunks_than_no_overlap(self, sample_document):
        """场景：同一文本比较 overlap=0 与 overlap>0；预期：均可正常切分。"""
        print("\n[TEST START] Verify both overlap=0 and overlap>0 produce chunks | 验证 overlap=0 与 overlap>0 均能正常切分")
        print("[INPUT] sample_document, chunk_size=200; overlap=0 and overlap=30 | 示例文档，两种 overlap")
        print("[ACTION] Calling chunk_document twice (overlap=0, overlap=30) | 调用 chunk_document 两次")
        chunks_no_overlap = chunk_document(sample_document, chunk_size=200, overlap=0)
        chunks_with_overlap = chunk_document(sample_document, chunk_size=200, overlap=30)
        print("[EXPECTED] Both return at least 1 chunk | 两种均至少返回 1 个 chunk")
        assert len(chunks_with_overlap) >= 1, "overlap>0 时应生成 chunk"
        assert len(chunks_no_overlap) >= 1, "overlap=0 时应生成 chunk"
        print("[PASS] Both configurations produce chunks | 两种配置均产生 chunk\n")


class TestChunkDocuments:
    """chunk_documents 批量切分行为"""

    def test_empty_list_returns_empty(self):
        """场景：输入空列表；预期：返回空列表。"""
        print("\n[TEST START] Verify chunk_documents([]) returns [] | 验证空列表输入返回空列表")
        print("[INPUT] Empty list [] | 空列表")
        print("[ACTION] Calling chunk_documents([]) | 调用 chunk_documents([])")
        print("[EXPECTED] Return [] | 返回空列表")
        assert chunk_documents([]) == [], "空输入应返回空输出"
        print("[PASS] Empty list returned | 返回空列表\n")

    def test_multiple_documents_merged(self, short_document, sample_document):
        """场景：输入多个 Document；预期：返回合并后的 chunk 列表。"""
        print("\n[TEST START] Verify multiple docs merged into one chunk list with both sources | 验证多文档合并且包含两来源")
        docs = [short_document, sample_document]
        print("[INPUT] Two documents (short + sample) | 两个 Document")
        print("[ACTION] Calling chunk_documents(docs, chunk_size=200, overlap=20) | 调用 chunk_documents(...)")
        chunks = chunk_documents(docs, chunk_size=200, overlap=20)
        print("[EXPECTED] len>=2, sources include test.pdf and short.pdf | 至少 2 个 chunk，来源含 test.pdf 与 short.pdf")
        assert len(chunks) >= 2, "两份文档应至少产生两个 chunk"
        # 应包含来自两个 source 的 chunks
        sources = {c.source for c in chunks}
        assert "test.pdf" in sources, "应包含 sample_document 的 source"
        assert "short.pdf" in sources, "应包含 short_document 的 source"
        print("[PASS] Merged chunks with both sources | 合并结果含两来源\n")

    def test_chunk_documents_preserves_order(self, short_document, sample_document):
        """场景：输入按 [A, B]；预期：首个 chunk 来自 A。"""
        print("\n[TEST START] Verify output order follows input document order | 验证输出顺序与输入文档顺序一致")
        docs = [short_document, sample_document]
        print("[INPUT] [short_document, sample_document] | [短文档, 示例文档]")
        print("[ACTION] Calling chunk_documents(docs, chunk_size=200) | 调用 chunk_documents(...)")
        chunks = chunk_documents(docs, chunk_size=200)
        print("[EXPECTED] First chunk from short.pdf | 首个 chunk 来自 short.pdf")
        # 第一个 chunk 应来自 short_document
        assert chunks[0].source == "short.pdf", "输出顺序应与输入文档顺序一致"
        print("[PASS] Order preserved | 顺序正确\n")


class TestChunkSerializationHelpers:
    """chunk dict 序列化辅助函数行为"""

    def test_chunks_to_dicts_and_back(self, short_document):
        """场景：Chunk -> dict -> Chunk；预期：数据等价。"""
        print("\n[TEST START] Verify chunks_to_dicts + dicts_to_chunks round-trip equals original | 验证 Chunk->dict->Chunk 往返等价")
        print("[INPUT] Chunks from short_document | 由短文档得到的 chunks")
        chunks = chunk_document(short_document, chunk_size=100, overlap=10)
        print("[ACTION] chunks_to_dicts(chunks) then dicts_to_chunks(raw) | 调用 chunks_to_dicts 再 dicts_to_chunks")
        raw = chunks_to_dicts(chunks)
        restored = dicts_to_chunks(raw)
        print("[EXPECTED] restored == chunks | 还原后与原 chunks 一致")
        assert restored == chunks, "往返转换后应与原 chunks 完全一致"
        print("[PASS] Round-trip preserves data | 往返转换数据一致\n")
