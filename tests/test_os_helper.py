"""Tests for podcaster.src.os_helper — file I/O and environment utilities."""

import os
from podcaster.src import os_helper


class TestJoin:
    def test_join_two_parts(self):
        assert os_helper.join("a", "b") == os.path.join("a", "b")

    def test_join_multiple_parts(self):
        assert os_helper.join("a", "b", "c") == os.path.join("a", "b", "c")

    def test_join_with_absolute_path(self):
        assert os_helper.join("/root", "sub") == "/root/sub"


class TestReadFile:
    def test_read_existing_file(self, tmp_path):
        filepath = tmp_path / "test.txt"
        filepath.write_text("hello world", encoding="utf-8")
        content = os_helper.read_file(str(tmp_path), "test.txt")
        assert content == "hello world"

    def test_read_nonexistent_file_returns_none(self, tmp_path):
        content = os_helper.read_file(str(tmp_path), "nonexistent.txt")
        assert content is None

    def test_read_file_single_arg(self, tmp_path):
        filepath = tmp_path / "test.txt"
        filepath.write_text("content", encoding="utf-8")
        content = os_helper.read_file(str(filepath))
        assert content == "content"

    def test_read_file_preserves_encoding(self, tmp_path):
        filepath = tmp_path / "unicode.txt"
        filepath.write_text("héllo wörld", encoding="utf-8")
        content = os_helper.read_file(str(filepath))
        assert content == "héllo wörld"


class TestWriteFile:
    def test_write_creates_file(self, tmp_path):
        os_helper.write_file("test content", str(tmp_path), "output.txt")
        result = (tmp_path / "output.txt").read_text(encoding="utf-8")
        assert result == "test content"

    def test_write_overwrites_existing(self, tmp_path):
        filepath = tmp_path / "output.txt"
        filepath.write_text("old content", encoding="utf-8")
        os_helper.write_file("new content", str(tmp_path), "output.txt")
        assert filepath.read_text(encoding="utf-8") == "new content"

    def test_write_single_path_arg(self, tmp_path):
        filepath = str(tmp_path / "direct.txt")
        os_helper.write_file("direct write", filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            assert f.read() == "direct write"


class TestMakeDir:
    def test_creates_directory(self, tmp_path):
        new_dir = str(tmp_path / "new_dir")
        os_helper.make_dir(new_dir)
        assert os.path.isdir(new_dir)

    def test_creates_nested_directory(self, tmp_path):
        new_dir = str(tmp_path / "a" / "b" / "c")
        os_helper.make_dir(new_dir)
        assert os.path.isdir(new_dir)

    def test_existing_directory_no_error(self, tmp_path):
        existing = str(tmp_path / "existing")
        os.makedirs(existing)
        os_helper.make_dir(existing)  # should not raise
        assert os.path.isdir(existing)

    def test_clean_removes_contents(self, tmp_path):
        target = str(tmp_path / "clean_me")
        os.makedirs(target)

        # Create some files and a subdirectory
        with open(os.path.join(target, "file.txt"), "w") as f:
            f.write("data")
        os.makedirs(os.path.join(target, "subdir"))
        with open(os.path.join(target, "subdir", "nested.txt"), "w") as f:
            f.write("nested data")

        os_helper.make_dir(target, clean=True)

        assert os.path.isdir(target)
        assert os.listdir(target) == []

    def test_clean_false_preserves_contents(self, tmp_path):
        target = str(tmp_path / "keep_me")
        os.makedirs(target)
        with open(os.path.join(target, "file.txt"), "w") as f:
            f.write("data")

        os_helper.make_dir(target, clean=False)

        assert "file.txt" in os.listdir(target)


class TestGetenv:
    def test_returns_env_variable(self, monkeypatch):
        monkeypatch.setenv("TEST_VAR_12345", "test_value")
        assert os_helper.getenv("TEST_VAR_12345") == "test_value"

    def test_returns_none_for_missing(self):
        result = os_helper.getenv("DEFINITELY_NOT_SET_VAR_XYZ")
        assert result is None
