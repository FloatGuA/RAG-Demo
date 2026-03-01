"""
模块2：Chunking
将 Document 切成可检索的 Chunk 单位，支持 overlap
"""

from dataclasses import asdict, dataclass
from pathlib import Path

from loader import Document
from ts20260301_storage_chunks import load_chunks, save_chunks


@dataclass
class Chunk:
    """可检索的文本块"""
    text: str
    source: str   # 来源文件
    page: int     # 页码


def chunk_document(
    doc: Document,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """
    将单个 Document 切分为 Chunks。

    Args:
        doc: 输入的 Document
        chunk_size: 每块最大字符数
        overlap: 块间重叠字符数

    Returns:
        List[Chunk]
    """
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    text = doc.content
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk_text = text[start:end]

        # 尽量在句末、换行处切断，避免 mid-word
        if end < len(text):
            break_at = max(
                chunk_text.rfind("。"),
                chunk_text.rfind("\n"),
                chunk_text.rfind("."),
                chunk_text.rfind(" "),
            )
            if break_at > chunk_size // 2:  # 至少保留一半内容
                chunk_text = chunk_text[: break_at + 1]
                end = start + break_at + 1

        chunks.append(Chunk(
            text=chunk_text.strip(),
            source=doc.source,
            page=doc.page,
        ))
        start = end - overlap

    return [c for c in chunks if c.text]


def chunk_documents(
    documents: list[Document],
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """
    批量将 Documents 切分为 Chunks。

    Args:
        documents: Document 列表
        chunk_size: 每块最大字符数
        overlap: 块间重叠字符数

    Returns:
        List[Chunk]
    """
    all_chunks = []
    for doc in documents:
        all_chunks.extend(chunk_document(doc, chunk_size=chunk_size, overlap=overlap))
    return all_chunks


def chunks_to_dicts(chunks: list[Chunk]) -> list[dict]:
    """将 Chunk 对象列表转为可序列化 dict 列表。"""
    return [asdict(c) for c in chunks]


def dicts_to_chunks(raw_chunks: list[dict]) -> list[Chunk]:
    """将 dict 列表还原为 Chunk 对象列表。"""
    return [
        Chunk(
            text=item["text"],
            source=item["source"],
            page=item["page"],
        )
        for item in raw_chunks
    ]


if __name__ == "__main__":
    from loader import load_pdfs_from_dir

    chunks_path = Path("artifacts/chunks/chunks.json")
    legacy_chunks_path = Path("storage/chunks.json")

    if chunks_path.exists():
        raw_chunks = load_chunks(str(chunks_path))
        chunks = dicts_to_chunks(raw_chunks)
        docs = []
        print(f"检测到缓存，已从 {chunks_path} 加载 {len(chunks)} 个 chunks")
    elif legacy_chunks_path.exists():
        raw_chunks = load_chunks(str(legacy_chunks_path))
        chunks = dicts_to_chunks(raw_chunks)
        save_chunks(raw_chunks, str(chunks_path))
        docs = []
        print(
            f"检测到旧缓存 {legacy_chunks_path}，已迁移到 {chunks_path}，"
            f"共加载 {len(chunks)} 个 chunks"
        )
    else:
        docs = load_pdfs_from_dir("data")
        chunks = chunk_documents(docs, chunk_size=500, overlap=50)
        save_chunks(chunks_to_dicts(chunks), str(chunks_path))
        print(f"未检测到缓存，已新生成并保存到 {chunks_path}")

    if docs:
        print(f"共 {len(docs)} 页 → {len(chunks)} 个 chunks")
    else:
        print(f"共加载 {len(chunks)} 个 chunks（来自缓存）")
    for c in chunks[:3]:
        print(f"  [{c.source} p.{c.page}] {c.text[:60]}...")
