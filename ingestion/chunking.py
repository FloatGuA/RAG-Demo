"""
模块2：Chunking
将 Document 切成可检索的 Chunk 单位，支持 overlap
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re

from ingestion.loader import Document

_PARA_RE = re.compile(r"\n{2,}")


@dataclass
class Chunk:
    """可检索的文本块"""
    text: str
    source: str   # 来源文件
    page: int     # 页码


def _sliding_window(text: str, chunk_size: int, overlap: int) -> list[str]:
    """对单段过长文本做滑动窗口切分（内部辅助函数）。"""
    segments: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        seg = text[start:end]
        if end < len(text):
            break_at = max(
                seg.rfind("。"),
                seg.rfind("\n"),
                seg.rfind("."),
                seg.rfind(" "),
            )
            if break_at > chunk_size // 2:
                seg = seg[: break_at + 1]
                end = start + break_at + 1
        segments.append(seg.strip())
        start = end - overlap
    return [s for s in segments if s]


def chunk_document(
    doc: Document,
    chunk_size: int = 500,
    overlap: int = 50,
) -> list[Chunk]:
    """
    将单个 Document 切分为 Chunks。

    策略（paragraph-first）：
    1. 先按空行（\\n\\n+）切成自然段落，保证语义完整性。
    2. 段落长度 <= chunk_size：整段作为一个 chunk。
    3. 段落过长：对该段做滑动窗口细切（overlap 在此生效）。

    Args:
        doc: 输入的 Document
        chunk_size: 每块最大字符数
        overlap: 长段滑动窗口的块间重叠字符数

    Returns:
        List[Chunk]
    """
    if overlap >= chunk_size:
        raise ValueError("overlap 必须小于 chunk_size")

    text = doc.content
    if not text:
        return []

    paragraphs = [p.strip() for p in _PARA_RE.split(text) if p.strip()]
    if not paragraphs:
        return []

    segments: list[str] = []
    for para in paragraphs:
        if len(para) <= chunk_size:
            segments.append(para)
        else:
            segments.extend(_sliding_window(para, chunk_size, overlap))

    return [Chunk(text=s, source=doc.source, page=doc.page) for s in segments]


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


def save_chunks(chunks: list[dict], path: str) -> None:
    """
    将 chunks 保存到 JSON 文件（可读性优先）。
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)


def load_chunks(path: str) -> list[dict]:
    """
    从 JSON 文件加载 chunks。
    """
    target = Path(path)
    if not target.exists():
        raise FileNotFoundError(f"chunks 文件不存在: {target}")

    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"chunks 文件格式错误，期望 list，实际: {type(data).__name__}")
    return data


if __name__ == "__main__":
    from ingestion.loader import load_pdfs_from_dir

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
