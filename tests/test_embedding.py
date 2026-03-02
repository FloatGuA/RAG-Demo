"""
embedding.py 单元测试
"""

import importlib.util

import pytest

from embedding import (
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


class TestEmbedding:
    def test_embed_text_has_fixed_dim(self):
        print("\n[TEST START] Embedding dimension fixed | 向量维度固定")
        print("[INPUT] text='hello world', dim=64 | 文本与维度")
        print("[ACTION] call embed_text | 调用 embed_text")
        vec = embed_text("hello world", dim=64)
        print("[EXPECTED] len(vec)==64 | 向量长度为 64")
        assert len(vec) == 64
        print("[PASS] fixed dimension ok | 固定维度正确\n")

    def test_embed_text_is_deterministic(self):
        print("\n[TEST START] Embedding deterministic | 向量可复现")
        print("[INPUT] same text twice | 同一文本两次")
        print("[ACTION] call embed_text twice | 调用两次 embed_text")
        v1 = embed_text("Deterministic test", dim=128)
        v2 = embed_text("Deterministic test", dim=128)
        print("[EXPECTED] v1 == v2 | 两次结果一致")
        assert v1 == v2
        print("[PASS] deterministic behavior ok | 可复现行为正确\n")

    def test_build_vector_store_structure(self):
        print("\n[TEST START] Build vector store structure | 构建向量存储结构")
        chunks = [
            {"text": "A text", "source": "a.pdf", "page": 1},
            {"text": "B text", "source": "b.pdf", "page": 2},
        ]
        print("[INPUT] 2 chunks dicts | 两个 chunk 字典")
        print("[ACTION] call build_vector_store | 调用 build_vector_store")
        store = build_vector_store(chunks, dim=32)
        print("[EXPECTED] store dim=32 and length=2 | dim=32 且长度为 2")
        assert isinstance(store, VectorStore)
        assert store.dim == 32
        assert len(store.vectors) == 2
        assert len(store.metadata) == 2
        print("[PASS] vector store structure ok | 向量存储结构正确\n")


class TestVectorPersistence:
    def test_save_then_load_vectors_roundtrip(self, tmp_path):
        print("\n[TEST START] Save/load vectors roundtrip | 向量保存加载往返一致")
        store = VectorStore(
            dim=8,
            vectors=[[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
            metadata=[{"text": "x", "source": "x.pdf", "page": 1}],
        )
        file_path = tmp_path / "vectors.json"
        print("[INPUT] VectorStore + file path | 向量存储与文件路径")
        print("[ACTION] save_vectors then load_vectors | 先保存再加载")
        save_vectors(store, str(file_path))
        loaded = load_vectors(str(file_path))
        print("[EXPECTED] loaded equals original store | 加载后与原始一致")
        assert loaded.dim == store.dim
        assert loaded.vectors == store.vectors
        assert loaded.metadata == store.metadata
        print("[PASS] vector roundtrip ok | 向量往返一致\n")

    def test_load_vectors_missing_file_raises(self, tmp_path):
        print("\n[TEST START] Missing vectors file raises | 缺失向量文件报错")
        missing = tmp_path / "not_exists.json"
        print("[INPUT] missing file path | 不存在的文件路径")
        print("[ACTION] call load_vectors | 调用 load_vectors")
        print("[EXPECTED] FileNotFoundError | 抛出 FileNotFoundError")
        with pytest.raises(FileNotFoundError, match="vectors 文件不存在"):
            load_vectors(str(missing))
        print("[PASS] missing file handling ok | 缺失文件处理正确\n")


class TestFaissIntegration:
    def test_build_faiss_index_without_faiss_raises_or_skips(self):
        print("\n[TEST START] FAISS availability check | FAISS 可用性检查")
        store = VectorStore(dim=8, vectors=[[0.0] * 8], metadata=[{"text": "x"}])
        print("[INPUT] minimal VectorStore | 最小向量存储")
        print("[ACTION] call build_faiss_index | 调用 build_faiss_index")
        if not has_faiss():
            print("[EXPECTED] raise RuntimeError when faiss unavailable | faiss 不可用时抛 RuntimeError")
            with pytest.raises(RuntimeError, match="faiss"):
                build_faiss_index(store)
            print("[PASS] unavailable faiss handled | faiss 不可用处理正确\n")
            return
        print("[EXPECTED] index object created | 成功创建索引对象")
        idx = build_faiss_index(store)
        assert idx is not None
        print("[PASS] faiss index built | faiss 索引构建成功\n")

    @pytest.mark.skipif(importlib.util.find_spec("faiss") is None, reason="需要 faiss 环境")
    def test_faiss_index_roundtrip_and_search(self, tmp_path):
        print("\n[TEST START] FAISS roundtrip and search | FAISS 索引往返与检索")
        chunks = [
            {"text": "apple banana", "source": "a.pdf", "page": 1},
            {"text": "orange pear", "source": "b.pdf", "page": 2},
        ]
        print("[INPUT] 2 chunks + tmp index path | 两个 chunk 与临时索引路径")
        print("[ACTION] build index -> save -> load -> search | 构建索引并保存加载后检索")
        store = build_vector_store(chunks, dim=64)
        index = build_faiss_index(store)
        index_path = tmp_path / "faiss.index"
        save_faiss_index(index, str(index_path))
        loaded_index = load_faiss_index(str(index_path))
        query_vec = embed_text("apple", dim=64)
        results = search_faiss(loaded_index, query_vec, top_k=2)
        print("[EXPECTED] results list with at least 1 item | 返回至少 1 条检索结果")
        assert isinstance(results, list)
        assert len(results) >= 1
        assert isinstance(results[0][0], int)
        assert isinstance(results[0][1], float)
        print("[PASS] FAISS roundtrip/search ok | FAISS 往返与检索正确\n")
