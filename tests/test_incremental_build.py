"""
pipeline/build.py 增量索引功能单元测试
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from pipeline.build import (
    _load_manifest,
    _save_manifest,
    _scan_data_dir,
    build_or_load_chunks,
    build_or_load_vectors,
)


# ── Manifest helpers ─────────────────────────────────────────────────────────

class TestManifest:
    def test_load_manifest_missing_returns_empty(self, tmp_path, monkeypatch):
        print("\n[TEST START] load_manifest with missing file returns empty dict | 清单缺失返回空字典")
        monkeypatch.chdir(tmp_path)
        result = _load_manifest()
        assert result == {}
        print("[PASS] missing manifest ok\n")

    def test_save_and_load_manifest_roundtrip(self, tmp_path, monkeypatch):
        print("\n[TEST START] save/load manifest roundtrip | 清单保存读取往返")
        monkeypatch.chdir(tmp_path)
        data = {"data/a.pdf": 1234567890.0, "data/b.pptx": 9876543210.0}
        _save_manifest(data)
        loaded = _load_manifest()
        assert loaded == data
        print("[PASS] manifest roundtrip ok\n")

    def test_save_manifest_creates_parent_dirs(self, tmp_path, monkeypatch):
        print("\n[TEST START] save_manifest creates parent dirs | 保存清单自动创建目录")
        monkeypatch.chdir(tmp_path)
        _save_manifest({"x": 1.0})
        assert (tmp_path / "artifacts" / "chunks" / "manifest.json").exists()
        print("[PASS] parent dir creation ok\n")


# ── _scan_data_dir ────────────────────────────────────────────────────────────

class TestScanDataDir:
    def test_scan_empty_dir_returns_empty(self, tmp_path, monkeypatch):
        print("\n[TEST START] scan empty data dir returns empty dict | 空目录返回空字典")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        result = _scan_data_dir("data")
        assert result == {}
        print("[PASS] empty dir scan ok\n")

    def test_scan_detects_files_with_mtime(self, tmp_path, monkeypatch):
        print("\n[TEST START] scan detects files with mtime | 扫描能检测文件和修改时间")
        monkeypatch.chdir(tmp_path)
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        (data_dir / "a.txt").write_text("hello")
        result = _scan_data_dir("data")
        assert len(result) == 1
        key = list(result.keys())[0]
        assert "a.txt" in key
        assert isinstance(result[key], float)
        print("[PASS] file detection ok\n")

    def test_scan_missing_dir_returns_empty(self, tmp_path, monkeypatch):
        print("\n[TEST START] scan non-existent dir returns empty | 不存在目录返回空字典")
        monkeypatch.chdir(tmp_path)
        result = _scan_data_dir("data")
        assert result == {}
        print("[PASS] missing dir scan ok\n")


# ── build_or_load_chunks incremental ─────────────────────────────────────────

class TestBuildOrLoadChunksIncremental:
    def _write_text_doc(self, path: Path, text: str) -> None:
        """写一个简单的 .md 文件作为测试文档。"""
        path.write_text(text, encoding="utf-8")

    def test_first_build_returns_rebuild_source(self, tmp_path, monkeypatch):
        print("\n[TEST START] first build returns 'rebuild' source | 首次构建返回 rebuild")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "artifacts" / "chunks").mkdir(parents=True)
        self._write_text_doc(tmp_path / "data" / "a.md", "# Title\n\nSome content about trees.")
        chunks, src, new_chunks = build_or_load_chunks()
        assert src == "rebuild"
        assert len(chunks) > 0
        assert len(new_chunks) == len(chunks)
        print("[PASS] first build source ok\n")

    def test_second_build_no_new_files_returns_cache(self, tmp_path, monkeypatch):
        print("\n[TEST START] second build with no new files returns 'cache' | 无新文件返回 cache")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "artifacts" / "chunks").mkdir(parents=True)
        self._write_text_doc(tmp_path / "data" / "a.md", "# Title\n\nSome content about trees.")
        build_or_load_chunks()  # first build
        chunks, src, new_chunks = build_or_load_chunks()  # second build
        assert src == "cache"
        assert new_chunks == []
        print("[PASS] cache hit ok\n")

    def test_new_file_triggers_incremental(self, tmp_path, monkeypatch):
        print("\n[TEST START] adding new file triggers incremental | 新文件触发增量构建")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "artifacts" / "chunks").mkdir(parents=True)
        self._write_text_doc(tmp_path / "data" / "a.md", "# Title\n\nContent about graphs.")
        chunks_first, _, _ = build_or_load_chunks()

        # Add a new file
        self._write_text_doc(tmp_path / "data" / "b.md", "# Second\n\nContent about trees.")
        chunks_second, src, new_chunks = build_or_load_chunks()

        assert src == "incremental"
        assert len(chunks_second) > len(chunks_first)
        assert len(new_chunks) > 0
        # new_chunks should only contain chunks from b.md
        for c in new_chunks:
            assert c.source.endswith("b.md")
        print("[PASS] incremental trigger ok\n")

    def test_incremental_chunks_persisted(self, tmp_path, monkeypatch):
        print("\n[TEST START] incremental chunks are persisted to disk | 增量 chunks 持久化到磁盘")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "artifacts" / "chunks").mkdir(parents=True)
        self._write_text_doc(tmp_path / "data" / "a.md", "# Title\n\nContent about graphs.")
        build_or_load_chunks()  # first build

        self._write_text_doc(tmp_path / "data" / "b.md", "# Second\n\nContent about trees.")
        chunks_incr, _, _ = build_or_load_chunks()  # incremental

        # Third load should be a pure cache hit with all chunks
        chunks_cache, src, _ = build_or_load_chunks()
        assert src == "cache"
        assert len(chunks_cache) == len(chunks_incr)
        print("[PASS] incremental persistence ok\n")

    def test_force_rebuild_ignores_manifest(self, tmp_path, monkeypatch):
        print("\n[TEST START] force_rebuild ignores manifest and rebuilds all | force-rebuild 忽略清单全量重建")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "artifacts" / "chunks").mkdir(parents=True)
        self._write_text_doc(tmp_path / "data" / "a.md", "# Title\n\nContent about graphs.")
        build_or_load_chunks()  # seed cache

        self._write_text_doc(tmp_path / "data" / "b.md", "# Second\n\nContent about trees.")
        chunks, src, new_chunks = build_or_load_chunks(force_rebuild=True)
        assert src == "rebuild"
        assert len(new_chunks) == len(chunks)  # all chunks are "new" on rebuild
        print("[PASS] force rebuild ok\n")

    def test_changed_file_emits_warning(self, tmp_path, monkeypatch):
        print("\n[TEST START] changed file emits UserWarning | 文件修改触发 UserWarning")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "data").mkdir()
        (tmp_path / "artifacts" / "chunks").mkdir(parents=True)
        self._write_text_doc(tmp_path / "data" / "a.md", "# Title\n\nContent about graphs.")
        build_or_load_chunks()  # first build - establishes manifest with current mtime

        # Modify the file's mtime by rewriting it slightly later
        time.sleep(0.05)
        (tmp_path / "data" / "a.md").write_text("# Title\n\nModified content.", encoding="utf-8")

        with pytest.warns(UserWarning, match="已修改"):
            build_or_load_chunks()
        print("[PASS] changed file warning ok\n")
