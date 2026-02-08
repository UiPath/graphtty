"""Tests for the Canvas and box-drawing primitives."""

from graphtty.canvas import (
    ASCII_CHARS,
    UNICODE_CHARS,
    Box,
    Canvas,
    chars,
    draw_box,
    draw_hline,
    draw_vline,
)


class TestCanvas:
    def test_create_empty(self):
        c = Canvas(5, 3)
        assert c.width == 5
        assert c.height == 3
        assert c.to_string() == ""

    def test_put_and_get(self):
        c = Canvas(5, 3)
        c.put(2, 1, "X")
        assert c.get(2, 1) == "X"
        assert c.get(0, 0) == " "

    def test_put_out_of_bounds(self):
        c = Canvas(3, 3)
        c.put(-1, 0, "X")  # no crash
        c.put(0, -1, "X")
        c.put(3, 0, "X")
        c.put(0, 3, "X")
        assert c.to_string() == ""

    def test_get_out_of_bounds(self):
        c = Canvas(3, 3)
        assert c.get(-1, 0) == " "
        assert c.get(3, 0) == " "

    def test_puts(self):
        c = Canvas(10, 1)
        c.puts(2, 0, "hello")
        assert c.to_string() == "  hello"

    def test_blit(self):
        c = Canvas(10, 5)
        c.blit(1, 1, "AB\nCD")
        assert c.get(1, 1) == "A"
        assert c.get(2, 1) == "B"
        assert c.get(1, 2) == "C"
        assert c.get(2, 2) == "D"

    def test_to_string_trims(self):
        c = Canvas(10, 5)
        c.put(0, 0, "X")
        c.put(5, 0, "Y")
        result = c.to_string()
        assert result == "X    Y"


class TestBox:
    def test_properties(self):
        b = Box(x=2, y=3, w=10, h=5)
        assert b.cx == 7  # 2 + 10 // 2
        assert b.top == 3
        assert b.bottom == 7  # 3 + 5 - 1


class TestDrawBox:
    def test_simple_unicode(self):
        c = Canvas(20, 5)
        box = Box(x=0, y=0, w=10, h=3)
        draw_box(c, box, ["Hello"], use_unicode=True)
        result = c.to_string()
        assert "\u250c" in result
        assert "Hello" in result
        assert "\u2514" in result

    def test_simple_ascii(self):
        c = Canvas(20, 5)
        box = Box(x=0, y=0, w=10, h=3)
        draw_box(c, box, ["Hello"], use_unicode=False)
        result = c.to_string()
        assert "+" in result
        assert "Hello" in result
        assert "-" in result

    def test_type_label_in_border(self):
        c = Canvas(20, 5)
        box = Box(x=0, y=0, w=14, h=3)
        draw_box(c, box, ["my node"], use_unicode=True, type_label="tool")
        result = c.to_string()
        lines = result.split("\n")
        assert "tool" in lines[0]
        assert "\u250c" in lines[0]
        assert "\u2510" in lines[0]

    def test_multiline_content(self):
        c = Canvas(20, 6)
        box = Box(x=0, y=0, w=12, h=4)
        draw_box(c, box, ["Line 1", "Line 2"], use_unicode=True)
        result = c.to_string()
        assert "Line 1" in result
        assert "Line 2" in result


class TestDrawLines:
    def test_hline(self):
        c = Canvas(10, 3)
        draw_hline(c, 1, 5, 1, use_unicode=True)
        for x in range(1, 6):
            assert c.get(x, 1) == "\u2500"

    def test_vline(self):
        c = Canvas(3, 10)
        draw_vline(c, 1, 2, 6, use_unicode=True)
        for y in range(2, 7):
            assert c.get(1, y) == "\u2502"

    def test_hline_ascii(self):
        c = Canvas(10, 3)
        draw_hline(c, 1, 5, 1, use_unicode=False)
        for x in range(1, 6):
            assert c.get(x, 1) == "-"


class TestChars:
    def test_unicode(self):
        ch = chars(True)
        assert ch is UNICODE_CHARS
        assert ch["tl"] == "\u250c"

    def test_ascii(self):
        ch = chars(False)
        assert ch is ASCII_CHARS
        assert ch["tl"] == "+"
