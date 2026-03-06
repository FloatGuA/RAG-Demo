"""离线构建链路：loader → chunking → embedding"""

from ingestion.loader import (
    Document,
    load_document,
    load_documents_from_dir,
    load_pdf,
    load_pdfs_from_dir,
)
from ingestion.chunking import (
    Chunk,
    chunk_document,
    chunk_documents,
    chunks_to_dicts,
    dicts_to_chunks,
    load_chunks,
    save_chunks,
)
from ingestion.embedding import (
    VectorStore,
    build_faiss_index,
    build_vector_store,
    embed_text,
    has_faiss,
    load_faiss_index,
    load_vectors,
    save_faiss_index,
    save_vectors,
    search_faiss,
)

__all__ = [
    "Document",
    "load_document",
    "load_documents_from_dir",
    "load_pdf",
    "load_pdfs_from_dir",
    "Chunk",
    "chunk_document",
    "chunk_documents",
    "chunks_to_dicts",
    "dicts_to_chunks",
    "load_chunks",
    "save_chunks",
    "VectorStore",
    "build_faiss_index",
    "build_vector_store",
    "embed_text",
    "has_faiss",
    "load_faiss_index",
    "load_vectors",
    "save_faiss_index",
    "save_vectors",
    "search_faiss",
]
