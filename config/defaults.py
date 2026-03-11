"""项目级默认值常量，供 pipeline / CLI / UI 层统一引用。"""

DEFAULT_CHUNK_SIZE = 500
DEFAULT_OVERLAP = 50
DEFAULT_EMBED_DIM = 384        # sentence-transformers (all-MiniLM-L6-v2) 输出维度；hash 后端下此值有效
DEFAULT_EMBED_BACKEND = "auto"  # 优先 sentence-transformers，不可用时自动降级 hash；可选 "hash" / "sentence_transformers"
DEFAULT_TOP_K = 3
DEFAULT_USE_HYBRID = False
DEFAULT_USE_RERANK = False
DEFAULT_RERANK_INITIAL_K = 20
DEFAULT_RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_PREVIEW = 3
DEFAULT_TEMPERATURE = 0.2
DEFAULT_LLM_TIMEOUT = 120.0
DEFAULT_LLM_MAX_RETRIES = 1
DEFAULT_LLM_PROVIDER = "local"
DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_API_KEY_ENV = "OPENAI_API_KEY"
