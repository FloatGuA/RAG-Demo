"""pipeline 包 — 重导出核心 API，方便外部 from pipeline import ... 使用。"""

from pipeline.build import (  # noqa: F401
    build_or_load_chunks,
    build_or_load_faiss_index,
    build_or_load_vectors,
    build_runtime,
)
from pipeline.query import answer_with_store, answer_with_store_stream, render_response  # noqa: F401
