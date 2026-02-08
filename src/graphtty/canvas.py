"""2D character canvas for ASCII/Unicode rendering."""

from __future__ import annotations

from dataclasses import dataclass

from .themes import RESET

# Unicode box-drawing character set
UNICODE_CHARS = {
    "tl": "\u250c",  # ┌
    "tr": "\u2510",  # ┐
    "bl": "\u2514",  # └
    "br": "\u2518",  # ┘
    "h": "\u2500",  # ─
    "v": "\u2502",  # │
    "jt": "\u252c",  # ┬
    "jb": "\u2534",  # ┴
    "jl": "\u251c",  # ├
    "jr": "\u2524",  # ┤
    "jx": "\u253c",  # ┼
    "arrow_down": "\u25bc",  # ▼
    "arrow_up": "\u25b2",  # ▲
    "arrow_right": "\u25b6",  # ▶
    "arrow_left": "\u25c0",  # ◀
}

# Plain ASCII fallback
ASCII_CHARS = {
    "tl": "+",
    "tr": "+",
    "bl": "+",
    "br": "+",
    "h": "-",
    "v": "|",
    "jt": "+",
    "jb": "+",
    "jl": "+",
    "jr": "+",
    "jx": "+",
    "arrow_down": "v",
    "arrow_up": "^",
    "arrow_right": ">",
    "arrow_left": "<",
}


def chars(use_unicode: bool = True) -> dict[str, str]:
    """Return the appropriate character set."""
    return UNICODE_CHARS if use_unicode else ASCII_CHARS


class Canvas:
    """Row-major 2D character grid with optional per-cell color.

    Coordinate system: (x, y) where x is column and y is row.
    Origin is top-left.
    """

    def __init__(self, width: int, height: int) -> None:
        """Create a blank canvas of the given dimensions."""
        self.width = width
        self.height = height
        self._rows: list[list[str]] = [[" "] * width for _ in range(height)]
        self._colors: list[list[str | None]] = [[None] * width for _ in range(height)]

    def put(self, x: int, y: int, ch: str, color: str | None = None) -> None:
        """Place a single character at (x, y) with optional ANSI *color*."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._rows[y][x] = ch
            if color is not None:
                self._colors[y][x] = color

    def get(self, x: int, y: int) -> str:
        """Read a single character at (x, y)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._rows[y][x]
        return " "

    def puts(self, x: int, y: int, text: str, color: str | None = None) -> None:
        """Write a string horizontally starting at (x, y)."""
        for i, ch in enumerate(text):
            self.put(x + i, y, ch, color)

    def blit(self, x: int, y: int, block: str, color: str | None = None) -> None:
        """Paste a multi-line block of text onto the canvas."""
        for row_idx, line in enumerate(block.split("\n")):
            for col_idx, ch in enumerate(line):
                if ch != " ":
                    self.put(x + col_idx, y + row_idx, ch, color)

    def blit_canvas(self, src: Canvas, x: int, y: int) -> None:
        """Copy non-space cells (and their colors) from *src* onto this canvas."""
        for sy in range(src.height):
            for sx in range(src.width):
                ch = src._rows[sy][sx]
                if ch != " ":
                    dx, dy = x + sx, y + sy
                    if 0 <= dx < self.width and 0 <= dy < self.height:
                        self._rows[dy][dx] = ch
                        self._colors[dy][dx] = src._colors[sy][sx]

    def to_string(self, *, use_color: bool = False) -> str:
        """Convert canvas to a string, trimming trailing whitespace.

        When *use_color* is ``True``, per-cell ANSI color codes are emitted.
        """
        lines: list[str] = []
        for y in range(self.height):
            row = self._rows[y]

            # Find last non-space character (for trimming)
            last = len(row) - 1
            while last >= 0 and row[last] == " ":
                last -= 1

            if last < 0:
                lines.append("")
                continue

            if not use_color:
                lines.append("".join(row[: last + 1]))
            else:
                parts: list[str] = []
                current_color: str | None = None
                for x in range(last + 1):
                    cell_color = self._colors[y][x]
                    if cell_color != current_color:
                        if current_color is not None:
                            parts.append(RESET)
                        if cell_color is not None:
                            parts.append(cell_color)
                        current_color = cell_color
                    parts.append(row[x])
                if current_color is not None:
                    parts.append(RESET)
                lines.append("".join(parts))

        while lines and not lines[-1]:
            lines.pop()
        while lines and not lines[0]:
            lines.pop(0)
        return "\n".join(lines)


@dataclass
class Box:
    """A positioned rectangle on the canvas."""

    x: int
    y: int
    w: int
    h: int

    @property
    def cx(self) -> int:
        """Center x-coordinate."""
        return self.x + self.w // 2

    @property
    def top(self) -> int:
        """Top y-coordinate."""
        return self.y

    @property
    def bottom(self) -> int:
        """Bottom y-coordinate."""
        return self.y + self.h - 1


def draw_box(
    canvas: Canvas,
    box: Box,
    lines: list[str],
    *,
    use_unicode: bool = True,
    type_label: str | None = None,
    border_color: str | None = None,
    text_color: str | None = None,
    type_color: str | None = None,
) -> None:
    """Draw a bordered box with centered text lines.

    If *type_label* is provided, it is embedded in the top border.
    Optional ANSI colors: *border_color* for the frame, *text_color* for
    content, *type_color* for the embedded type label.
    """
    ch = chars(use_unicode)
    x, y, w, h = box.x, box.y, box.w, box.h
    inner = w - 2  # width between borders

    # Top border
    if type_label and len(type_label) + 2 <= inner:
        # Embed type label: ┌ type ──┐
        fill = inner - len(type_label) - 2
        top_str = ch["tl"] + " "
        canvas.puts(x, y, top_str, border_color)
        canvas.puts(x + len(top_str), y, type_label, type_color or border_color)
        rest = " " + ch["h"] * fill + ch["tr"]
        canvas.puts(x + len(top_str) + len(type_label), y, rest, border_color)
    else:
        top = ch["tl"] + ch["h"] * inner + ch["tr"]
        canvas.puts(x, y, top, border_color)

    # Content rows
    for i, text in enumerate(lines):
        row_y = y + 1 + i
        pad_total = inner - len(text)
        pad_l = pad_total // 2
        # Left border
        canvas.put(x, row_y, ch["v"], border_color)
        # Content
        canvas.puts(x + 1 + pad_l, row_y, text, text_color)
        # Right border
        canvas.put(x + w - 1, row_y, ch["v"], border_color)

    # Fill any remaining inner rows (between content and bottom border)
    for ry in range(y + 1 + len(lines), y + h - 1):
        canvas.put(x, ry, ch["v"], border_color)
        canvas.put(x + w - 1, ry, ch["v"], border_color)

    # Bottom border
    bot = ch["bl"] + ch["h"] * inner + ch["br"]
    canvas.puts(x, y + h - 1, bot, border_color)


def draw_hline(
    canvas: Canvas,
    x1: int,
    x2: int,
    y: int,
    *,
    use_unicode: bool = True,
    color: str | None = None,
) -> None:
    """Draw a horizontal line from x1 to x2 at row y."""
    ch = chars(use_unicode)
    start = min(x1, x2)
    end = max(x1, x2)
    for x in range(start, end + 1):
        canvas.put(x, y, ch["h"], color)


def draw_vline(
    canvas: Canvas,
    x: int,
    y1: int,
    y2: int,
    *,
    use_unicode: bool = True,
    color: str | None = None,
) -> None:
    """Draw a vertical line from y1 to y2 at column x."""
    ch = chars(use_unicode)
    start = min(y1, y2)
    end = max(y1, y2)
    for y in range(start, end + 1):
        canvas.put(x, y, ch["v"], color)
