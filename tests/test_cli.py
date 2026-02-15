"""Tests for the CLI entry-point."""

import json
import os
import tempfile

import pytest

from graphtty.__main__ import main


def _tmp_graph(nodes, edges=None):
    """Write a graph JSON to a temp file and return the path."""
    data = {"nodes": nodes, "edges": edges or []}
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


class TestCLIBasic:
    def test_render_simple_graph(self, capsys):
        path = _tmp_graph(
            [
                {
                    "id": "a",
                    "name": "Hello",
                    "type": "tool",
                },
            ]
        )
        try:
            main([path])
            out = capsys.readouterr().out
            assert "Hello" in out
        finally:
            os.unlink(path)

    def test_list_themes(self, capsys):
        main(["--list-themes"])
        out = capsys.readouterr().out
        assert "default" in out
        assert "monokai" in out

    def test_ascii_flag(self, capsys):
        path = _tmp_graph(
            [
                {
                    "id": "a",
                    "name": "Box",
                    "type": "tool",
                },
            ]
        )
        try:
            main([path, "--ascii"])
            out = capsys.readouterr().out
            assert "+" in out
            assert "\u250c" not in out  # no unicode
        finally:
            os.unlink(path)

    def test_no_types_flag(self, capsys):
        path = _tmp_graph(
            [
                {
                    "id": "a",
                    "name": "Box",
                    "type": "tool",
                },
            ]
        )
        try:
            main([path, "--no-types"])
            out = capsys.readouterr().out
            assert "Box" in out
            assert "[tool]" not in out
        finally:
            os.unlink(path)

    def test_theme_flag(self, capsys):
        path = _tmp_graph(
            [
                {
                    "id": "a",
                    "name": "Box",
                    "type": "tool",
                },
            ]
        )
        try:
            main([path, "--theme", "monokai"])
            out = capsys.readouterr().out
            assert "Box" in out
            assert "\033[" in out  # ANSI codes present
        finally:
            os.unlink(path)

    def test_legacy_metadata_mapping(self, capsys):
        """Legacy metadata fields should be mapped to description by CLI."""
        path = _tmp_graph(
            [
                {
                    "id": "a",
                    "name": "model",
                    "type": "model",
                    "subgraph": None,
                    "metadata": {"model_name": "gpt-4", "max_tokens": 1000},
                },
            ]
        )
        try:
            main([path])
            out = capsys.readouterr().out
            assert "gpt-4" in out
        finally:
            os.unlink(path)


class TestCLIErrors:
    def test_missing_file_arg(self):
        with pytest.raises(SystemExit):
            main([])

    def test_invalid_theme(self):
        path = _tmp_graph(
            [
                {
                    "id": "a",
                    "name": "Box",
                    "type": "tool",
                },
            ]
        )
        try:
            with pytest.raises(SystemExit):
                main([path, "--theme", "nonexistent"])
        finally:
            os.unlink(path)

    def test_nonexistent_file(self):
        with pytest.raises(SystemExit):
            main(["nonexistent_file_12345.json"])


class TestCLISamples:
    """Smoke-test against the real sample files."""

    @pytest.fixture(
        params=[
            "samples/react-agent/graph.json",
            "samples/workflow-agent/graph.json",
            "samples/deep-agent/graph.json",
            "samples/supervisor-agent/graph.json",
            "samples/world-map/graph.json",
            "samples/call-graph/graph.json",
        ]
    )
    def sample_path(self, request):
        path = request.param
        if not os.path.exists(path):
            pytest.skip(f"Sample not found: {path}")
        return path

    def test_sample_renders(self, sample_path, capsys):
        main([sample_path])
        out = capsys.readouterr().out
        assert len(out.strip()) > 0

    def test_sample_with_theme(self, sample_path, capsys):
        main([sample_path, "--theme", "dracula"])
        out = capsys.readouterr().out
        assert len(out.strip()) > 0
        assert "\033[" in out
