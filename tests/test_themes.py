"""Tests for the theme system."""

from graphtty import RenderOptions, get_theme, list_themes, render
from graphtty.themes import (
    DEFAULT,
    DRACULA,
    FOREST,
    MONOKAI,
    OCEAN,
    RESET,
)
from graphtty.types import AsciiEdge, AsciiGraph, AsciiNode


def _node(id: str, name: str, type: str = "action", **kwargs) -> AsciiNode:
    return AsciiNode(id=id, name=name, type=type, **kwargs)


def _edge(src: str, tgt: str, label: str | None = None) -> AsciiEdge:
    return AsciiEdge(source=src, target=tgt, label=label)


class TestThemeRegistry:
    def test_list_themes(self):
        names = list_themes()
        assert "default" in names
        assert "monokai" in names
        assert "ocean" in names
        assert "forest" in names
        assert "dracula" in names
        assert "solarized" in names
        assert "nord" in names
        assert "catppuccin" in names
        assert "gruvbox" in names
        assert "tokyo-night" in names

    def test_get_theme(self):
        theme = get_theme("monokai")
        assert theme.name == "monokai"

    def test_get_default(self):
        theme = get_theme("default")
        assert theme is DEFAULT

    def test_unknown_theme_raises(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown theme"):
            get_theme("nonexistent")


class TestNodeStyle:
    def test_empty_type_uses_default(self):
        theme = get_theme("monokai")
        style = theme.get_style("")
        assert style == theme.default_style

    def test_nonempty_type_uses_palette(self):
        theme = get_theme("monokai")
        style = theme.get_style("anything")
        assert style in theme.palette
        assert style.border != ""

    def test_different_types_can_differ(self):
        theme = get_theme("monokai")
        style_a = theme.get_style("hub")
        style_b = theme.get_style("country")
        # With 7 palette entries these two should hash differently
        assert style_a != style_b

    def test_same_type_is_deterministic(self):
        theme = get_theme("monokai")
        assert theme.get_style("foo") is theme.get_style("foo")

    def test_default_theme_no_colors(self):
        style = DEFAULT.get_style("anything")
        assert style.border == ""
        assert style.text == ""


class TestColoredRendering:
    def test_default_theme_no_ansi(self):
        g = AsciiGraph(nodes=[_node("a", "Hello", "tool")])
        result = render(g)
        assert "\033[" not in result

    def test_monokai_has_ansi(self):
        g = AsciiGraph(nodes=[_node("a", "Hello", "tool")])
        result = render(g, RenderOptions(theme=MONOKAI))
        assert "\033[" in result
        assert RESET in result

    def test_theme_includes_reset(self):
        g = AsciiGraph(
            nodes=[_node("a", "Start", "entry"), _node("b", "End", "exit")],
            edges=[_edge("a", "b")],
        )
        result = render(g, RenderOptions(theme=OCEAN))
        # Every color start should be balanced by a RESET
        assert result.count(RESET) > 0

    def test_all_themes_produce_output(self):
        g = AsciiGraph(
            nodes=[_node("a", "Hello", "tool"), _node("b", "World", "model")],
            edges=[_edge("a", "b")],
        )
        for name in list_themes():
            theme = get_theme(name)
            result = render(g, RenderOptions(theme=theme))
            assert "Hello" in result
            assert "World" in result

    def test_colored_box_content(self):
        """Node content should still be readable through ANSI codes."""
        g = AsciiGraph(nodes=[_node("a", "MyNode", "model")])
        result = render(g, RenderOptions(theme=DRACULA))
        # Strip ANSI codes and check content
        import re

        plain = re.sub(r"\033\[[0-9;]*m", "", result)
        assert "MyNode" in plain
        assert "model" in plain  # type in border

    def test_backward_edge_colored(self):
        """Backward edges should include color when themed."""
        g = AsciiGraph(
            nodes=[_node("a", "Model", "model"), _node("b", "Tools", "tool")],
            edges=[_edge("a", "b"), _edge("b", "a")],
        )
        result = render(g, RenderOptions(theme=FOREST))
        assert "\033[" in result
