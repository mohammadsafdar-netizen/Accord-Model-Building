"""Unit tests for utils module."""

from __future__ import annotations

import pytest

from utils import clean_json_text, prune_empty_fields, save_json, load_json


class TestCleanJsonText:
    def test_strips_markdown_fence(self):
        text = "```json\n{\"a\": 1}\n```"
        assert "```" not in clean_json_text(text)
        assert "a" in clean_json_text(text)

    def test_plain_json_unchanged(self):
        text = '{"x": 1}'
        assert clean_json_text(text) == text


class TestPruneEmptyFields:
    def test_removes_none(self):
        assert prune_empty_fields({"a": None, "b": 1}) == {"b": 1}

    def test_removes_empty_string(self):
        assert prune_empty_fields({"a": "", "b": "x"}) == {"b": "x"}

    def test_nested_empty_dict_removed(self):
        out = prune_empty_fields({"a": {}, "b": {"c": 1}})
        assert "a" not in out
        assert out["b"] == {"c": 1}

    def test_empty_list_removed(self):
        out = prune_empty_fields({"a": [], "b": [1]})
        assert "a" not in out
        assert out["b"] == [1]


class TestSaveLoadJson:
    def test_roundtrip(self, tmp_path):
        data = {"form": "125", "count": 1}
        path = tmp_path / "out.json"
        save_json(data, path)
        assert path.exists()
        loaded = load_json(path)
        assert loaded == data
