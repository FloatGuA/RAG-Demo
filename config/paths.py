"""项目中所有 artifacts / 缓存文件的路径常量。"""

from pathlib import Path

CHUNKS_PATH = Path("artifacts/chunks/chunks.json")
MANIFEST_PATH = Path("artifacts/chunks/manifest.json")
LEGACY_CHUNKS_PATH = Path("storage/chunks.json")
VECTORS_PATH = Path("artifacts/vectors/vectors.npz")
LEGACY_VECTORS_PATH = Path("artifacts/vectors/vectors.json")
FAISS_INDEX_PATH = Path("artifacts/index/faiss.index")
