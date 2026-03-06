"""
embedding.py 单元测试
"""

import importlib.util
import json

import numpy as np
import pytest

from ingestion.embedding import (
    VectorStore,
    build_faiss_index,
    build_vector_store,
    embed_text,
    has_faiss,
    has_sentence_transformers,
    load_faiss_index,
    load_vectors,
    save_faiss_index,
    save_vectors,
    search_faiss,
)


class TestEmbedding:
    def test_embed_text_hash_has_fixed_dim(self):
        print("\n[TEST START] Hash backend dimension fixed | hash 后端向量维度固定")
        vec = embed_text("hello world", dim=64, backend="hash")
        assert len(vec) == 64
        print("[PASS] fixed dimension ok\n")

    def test_embed_text_hash_is_deterministic(self):
        print("\n[TEST START] Hash backend deterministic | hash 后端可复现")
        v1 = embed_text("Deterministic test", dim=128, backend="hash")
        v2 = embed_text("Deterministic test", dim=128, backend="hash")
        assert v1 == v2
        print("[PASS] deterministic behavior ok\n")

    def test_embed_text_auto_returns_nonempty(self):
        print("\n[TEST START] Auto backend returns non-empty vector | auto 后端返回非空向量")
        vec = embed_text("hello world", dim=256)
        assert len(vec) > 0
        assert isinstance(vec[0], float)
        print("[PASS] auto backend ok\n")

    def test_embed_text_auto_is_deterministic(self):
        print("\n[TEST START] Auto backend deterministic | auto 后端可复现")
        v1 = embed_text("Deterministic test", dim=256)
        v2 = embed_text("Deterministic test", dim=256)
        assert v1 == v2
        print("[PASS] deterministic ok\n")

    @pytest.mark.skipif(not has_sentence_transformers(), reason="需要 sentence-transformers")
    def test_embed_text_st_backend_dim(self):
        print("\n[TEST START] ST backend returns 384-dim vector | ST 后端返回 384 维向量")
        vec = embed_text("hello world", backend="sentence_transformers")
        assert len(vec) == 384
        print("[PASS] ST dim ok\n")

    def test_build_vector_store_structure_hash(self):
        print("\n[TEST START] Build vector store (hash backend) | 构建向量存储（hash）")
        chunks = [
            {"text": "A text", "source": "a.pdf", "page": 1},
            {"text": "B text", "source": "b.pdf", "page": 2},
        ]
        store = build_vector_store(chunks, dim=32, backend="hash")
        assert isinstance(store, VectorStore)
        assert store.dim == 32
        assert len(store.vectors) == 2
        assert len(store.metadata) == 2
        print("[PASS] vector store structure ok\n")

    def test_build_vector_store_detects_actual_dim(self):
        print("\n[TEST START] build_vector_store detects actual dim | 自动检测实际维度")
        chunks = [{"text": "hello", "source": "a.pdf", "page": 1}]
        store = build_vector_store(chunks, dim=64, backend="hash")
        assert store.dim == 64
        assert len(store.vectors[0]) == 64
        print("[PASS] actual dim detection ok\n")

    def test_build_vector_store_records_backend(self):
        print("\n[TEST START] build_vector_store records resolved backend | 记录 resolved backend")
        chunks = [{"text": "hello", "source": "a.pdf", "page": 1}]
        store = build_vector_store(chunks, dim=32, backend="hash")
        assert store.backend == "hash"
        print("[PASS] backend recorded ok\n")


class TestVectorPersistence:
    def test_save_then_load_npz_roundtrip(self, tmp_path):
        print("\n[TEST START] Save/load vectors npz roundtrip | npz 格式往返一致")
        store = VectorStore(
            dim=8,
            vectors=[[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]],
            metadata=[{"text": "x", "source": "x.pdf", "page": 1}],
            backend="hash",
        )
        file_path = tmp_path / "vectors.npz"
        save_vectors(store, str(file_path))
        assert file_path.exists(), "npz file should exist"
        loaded = load_vectors(str(file_path))
        assert loaded.dim == store.dim
        assert loaded.backend == store.backend
        assert loaded.metadata == store.metadata
        # float32 precision: compare with tolerance
        orig = np.array(store.vectors, dtype=np.float32)
        result = np.array(loaded.vectors, dtype=np.float32)
        assert np.allclose(orig, result), "vectors should match within float32 precision"
        print("[PASS] npz roundtrip ok\n")

    def test_save_npz_creates_correct_file(self, tmp_path):
        print("\n[TEST START] save_vectors writes npz file at exact path | 文件落在指定路径")
        store = VectorStore(dim=4, vectors=[[0.5, 0.5, 0.0, 0.0]], metadata=[{}], backend="hash")
        path = tmp_path / "vecs.npz"
        save_vectors(store, str(path))
        assert path.exists()
        raw = np.load(str(path), allow_pickle=False)
        assert "vectors" in raw
        assert "metadata_json" in raw
        assert "dim" in raw
        assert "backend" in raw
        assert raw["vectors"].shape == (1, 4)
        print("[PASS] npz file structure ok\n")

    def test_load_vectors_json_backward_compat(self, tmp_path):
        print("\n[TEST START] load_vectors reads old JSON format | 向后兼容旧 JSON 格式")
        payload = {
            "dim": 4,
            "backend": "hash",
            "vectors": [[0.5, 0.5, 0.0, 0.0]],
            "metadata": [{"text": "old", "source": "f.pdf", "page": 1}],
        }
        json_path = tmp_path / "vectors.json"
        json_path.write_text(json.dumps(payload), encoding="utf-8")
        loaded = load_vectors(str(json_path))
        assert loaded.dim == 4
        assert loaded.backend == "hash"
        assert loaded.metadata == payload["metadata"]
        print("[PASS] JSON backward compat ok\n")

    def test_load_vectors_missing_file_raises(self, tmp_path):
        print("\n[TEST START] Missing vectors file raises | 缺失向量文件报错")
        missing = tmp_path / "not_exists.npz"
        with pytest.raises(FileNotFoundError, match="vectors 文件不存在"):
            load_vectors(str(missing))
        print("[PASS] missing file handling ok\n")

    def test_save_load_empty_vectors(self, tmp_path):
        print("\n[TEST START] Save/load empty VectorStore | 空向量存储往返")
        store = VectorStore(dim=8, vectors=[], metadata=[], backend="hash")
        path = tmp_path / "empty.npz"
        save_vectors(store, str(path))
        loaded = load_vectors(str(path))
        assert loaded.dim == 8
        assert loaded.vectors == []
        assert loaded.metadata == []
        print("[PASS] empty vectors ok\n")


class TestFaissIntegration:
    def test_build_faiss_index_without_faiss_raises_or_skips(self):
        print("\n[TEST START] FAISS availability check | FAISS 可用性检查")
        store = VectorStore(dim=8, vectors=[[0.0] * 8], metadata=[{"text": "x"}])
        if not has_faiss():
            with pytest.raises(RuntimeError, match="faiss"):
                build_faiss_index(store)
            print("[PASS] unavailable faiss handled\n")
            return
        idx = build_faiss_index(store)
        assert idx is not None
        print("[PASS] faiss index built\n")

    @pytest.mark.skipif(importlib.util.find_spec("faiss") is None, reason="需要 faiss 环境")
    def test_faiss_index_roundtrip_and_search(self, tmp_path):
        print("\n[TEST START] FAISS roundtrip and search | FAISS 索引往返与检索")
        chunks = [
            {"text": "apple banana", "source": "a.pdf", "page": 1},
            {"text": "orange pear", "source": "b.pdf", "page": 2},
        ]
        store = build_vector_store(chunks, dim=64, backend="hash")
        index = build_faiss_index(store)
        index_path = tmp_path / "faiss.index"
        save_faiss_index(index, str(index_path))
        loaded_index = load_faiss_index(str(index_path))
        query_vec = embed_text("apple", dim=64, backend="hash")
        results = search_faiss(loaded_index, query_vec, top_k=2)
        assert isinstance(results, list)
        assert len(results) >= 1
        assert isinstance(results[0][0], int)
        assert isinstance(results[0][1], float)
        print("[PASS] FAISS roundtrip/search ok\n")
