"""
ts20260301_storage_chunks.py 单元测试

覆盖目标：
1) save_chunks/load_chunks 的数据一致性。
2) 存储目录自动创建。
3) 缺失文件、错误 JSON 结构的异常处理。
"""

import pytest

from ts20260301_storage_chunks import load_chunks, save_chunks


class TestStorageChunks:
    def test_save_then_load_keep_exact_structure(self, tmp_path):
        """场景：正常保存后再加载；预期：结构与内容完全一致。"""
        print("\n[TEST START] Verify save_chunks then load_chunks preserves exact structure | 验证保存后加载数据结构完全一致")
        chunks = [
            {"text": "A", "source": "a.pdf", "page": 1},
            {"text": "B", "source": "b.pdf", "page": 2},
        ]
        file_path = tmp_path / "chunks.json"
        print("[INPUT] Two chunks (dicts), path:", file_path, "| 两个 chunk 字典，路径")
        print("[ACTION] save_chunks(chunks, path) then load_chunks(path) | 先 save_chunks 再 load_chunks")
        save_chunks(chunks, str(file_path))
        loaded = load_chunks(str(file_path))
        print("[EXPECTED] loaded == chunks | 加载结果与保存前一致")
        assert loaded == chunks, "load 后数据应与 save 前完全一致"
        print("[PASS] Save/load round-trip preserves data | 保存/加载往返数据一致\n")

    def test_save_creates_parent_directory(self, tmp_path):
        """场景：目标目录不存在；预期：save 自动创建父目录。"""
        print("\n[TEST START] Verify save_chunks creates parent directory if missing | 验证 save_chunks 自动创建父目录")
        chunks = [{"text": "X", "source": "x.pdf", "page": 3}]
        file_path = tmp_path / "nested" / "chunks.json"
        print("[INPUT] One chunk, path with non-existent parent (nested/) | 一个 chunk，路径父目录不存在")
        print("[ACTION] Calling save_chunks(chunks, path) | 调用 save_chunks(...)")
        save_chunks(chunks, str(file_path))
        print("[EXPECTED] file_path.exists() | 目标文件被创建")
        assert file_path.exists(), "save_chunks 应自动创建并写入目标文件"
        print("[PASS] Parent dir created and file written | 父目录已创建且文件已写入\n")

    def test_load_missing_file_raises_file_not_found(self, tmp_path):
        """场景：文件不存在；预期：抛 FileNotFoundError。"""
        print("\n[TEST START] Verify load_chunks raises FileNotFoundError when file missing | 验证文件不存在时抛出 FileNotFoundError")
        missing = tmp_path / "not_exists.json"
        print("[INPUT] Non-existent path: not_exists.json | 不存在的路径")
        print("[ACTION] Calling load_chunks(path) | 调用 load_chunks(...)")
        print("[EXPECTED] FileNotFoundError with 'chunks 文件不存在' | 抛出 FileNotFoundError，含「chunks 文件不存在」")
        with pytest.raises(FileNotFoundError, match="chunks 文件不存在"):
            load_chunks(str(missing))
        print("[PASS] FileNotFoundError raised as expected | 按预期抛出 FileNotFoundError\n")

    def test_load_non_list_json_raises_value_error(self, tmp_path):
        """场景：JSON 根对象不是 list；预期：抛 ValueError。"""
        print("\n[TEST START] Verify load_chunks raises ValueError when JSON root is not list | 验证 JSON 根非 list 时抛出 ValueError")
        file_path = tmp_path / "bad.json"
        file_path.write_text('{"a": 1}', encoding="utf-8")
        print("[INPUT] JSON file with root object (not array) | JSON 根为对象而非数组")
        print("[ACTION] Calling load_chunks(path) | 调用 load_chunks(...)")
        print("[EXPECTED] ValueError with '期望 list' | 抛出 ValueError，含「期望 list」")
        with pytest.raises(ValueError, match="期望 list"):
            load_chunks(str(file_path))
        print("[PASS] ValueError raised as expected | 按预期抛出 ValueError\n")
