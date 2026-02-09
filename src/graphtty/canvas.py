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
        # Bounding box of non-space content (inclusive)
        self._bb_x0 = width
        self._bb_x1 = -1
        self._bb_y0 = height
        self._bb_y1 = -1

    @property
    def visual_size(self) -> tuple[int, int]:
        """Return (width, height) of the non-space bounding box — O(1)."""
        if self._bb_x1 < 0:
            return (0, 0)
        return (self._bb_x1 + 1, self._bb_y1 + 1)

    def put(self, x: int, y: int, ch: str, color: str | None = None) -> None:
        """Place a single character at (x, y) with optional ANSI *color*."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self._rows[y][x] = ch
            if color is not None:
                self._colors[y][x] = color
            if ch != " ":
                if x < self._bb_x0:
                    self._bb_x0 = x
                if x > self._bb_x1:
                    self._bb_x1 = x
                if y < self._bb_y0:
                    self._bb_y0 = y
                if y > self._bb_y1:
                    self._bb_y1 = y

    def get(self, x: int, y: int) -> str:
        """Read a single character at (x, y)."""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self._rows[y][x]
        return " "

    def puts(self, x: int, y: int, text: str, color: str | None = None) -> None:
        """Write a string horizontally starting at (x, y)."""
        if not text or y < 0 or y >= self.height:
            return
        # Clip to canvas bounds
        start = max(0, -x)
        end = min(len(text), self.width - x)
        if start >= end:
            return
        x0 = x + start
        x1_idx = x + end
        n = end - start
        # C-level slice assignment instead of Python char-by-char loop
        self._rows[y][x0:x1_idx] = list(text[start:end])
        if color is not None:
            self._colors[y][x0:x1_idx] = [color] * n
        # Update bounding box
        x1 = x1_idx - 1
        if x0 < self._bb_x0:
            self._bb_x0 = x0
        if x1 > self._bb_x1:
            self._bb_x1 = x1
        if y < self._bb_y0:
            self._bb_y0 = y
        if y > self._bb_y1:
            self._bb_y1 = y

    def blit(self, x: int, y: int, block: str, color: str | None = None) -> None:
        """Paste a multi-line block of text onto the canvas."""
        for row_idx, line in enumerate(block.split("\n")):
            for col_idx, ch in enumerate(line):
                if ch != " ":
                    self.put(x + col_idx, y + row_idx, ch, color)

    def blit_canvas(self, src: Canvas, x: int, y: int) -> None:
        """Copy non-space cells (and their colors) from *src* onto this canvas."""
        # Use source bounding box to skip empty regions
        if src._bb_x1 < 0:
            return  # source is empty
        sy0 = src._bb_y0
        sy1 = src._bb_y1
        sx0 = src._bb_x0
        sx1 = src._bb_x1
        dst_w = self.width
        dst_h = self.height
        dst_rows = self._rows
        dst_colors = self._colors
        src_rows = src._rows
        src_colors = src._colors
        for sy in range(sy0, sy1 + 1):
            dy = y + sy
            if dy < 0 or dy >= dst_h:
                continue
            src_row = src_rows[sy]
            src_col = src_colors[sy]
            dst_row = dst_rows[dy]
            dst_col = dst_colors[dy]
            for sx in range(sx0, sx1 + 1):
                ch = src_row[sx]
                if ch != " ":
                    dx = x + sx
                    if 0 <= dx < dst_w:
                        dst_row[dx] = ch
                        dst_col[dx] = src_col[sx]
        # Update bounding box
        dx0 = x + sx0
        dx1 = x + sx1
        dy0 = y + sy0
        dy1 = y + sy1
        if dx0 < self._bb_x0:
            self._bb_x0 = max(0, dx0)
        if dx1 > self._bb_x1:
            self._bb_x1 = min(dst_w - 1, dx1)
        if dy0 < self._bb_y0:
            self._bb_y0 = max(0, dy0)
        if dy1 > self._bb_y1:
            self._bb_y1 = min(dst_h - 1, dy1)

    def to_string(self, *, use_color: bool = False) -> str:
        """Convert canvas to a string, trimming trailing whitespace.

        When *use_color* is ``True``, per-cell ANSI color codes are emitted.
        """
        # Fast path: nothing drawn
        if self._bb_x1 < 0:
            return ""

        y0 = self._bb_y0
        y1 = self._bb_y1
        bb_x1 = self._bb_x1
        lines: list[str] = []
        for y in range(y0, y1 + 1):
            row = self._rows[y]

            # Find last non-space character — scan left from bb_x1 hint
            # (bb_x1 is a hint; scan rightward just in case)
            last = min(bb_x1, len(row) - 1)
            while last >= 0 and row[last] == " ":
                last -= 1

            if last < 0:
                lines.append("")
                continue

            if not use_color:
                lines.append("".join(row[: last + 1]))
            else:
                # Pre-join row once; use string slicing for color runs
                end = last + 1
                row_str = "".join(row[:end])
                colors_row = self._colors[y]
                parts: list[str] = []
                current_color: str | None = None
                run_start = 0
                for x in range(end):
                    cell_color = colors_row[x]
                    if cell_color != current_color:
                        # Flush previous run via string slice
                        if x > run_start:
                            parts.append(row_str[run_start:x])
                        if current_color is not None:
                            parts.append(RESET)
                        if cell_color is not None:
                            parts.append(cell_color)
                        current_color = cell_color
                        run_start = x
                # Flush final run
                if end > run_start:
                    parts.append(row_str[run_start:end])
                if current_color is not None:
                    parts.append(RESET)
                lines.append("".join(parts))

        # Trim leading/trailing empty lines — index-based (no O(n) pop(0))
        trim_start = 0
        while trim_start < len(lines) and not lines[trim_start]:
            trim_start += 1
        trim_end = len(lines)
        while trim_end > trim_start and not lines[trim_end - 1]:
            trim_end -= 1
        return "\n".join(lines[trim_start:trim_end])


@dataclass(slots=True)
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

    rows = canvas._rows
    color_rows = canvas._colors
    ch_v = ch["v"]
    ch_h = ch["h"]
    x_end = x + w  # one past the right edge

    # Top border — direct slice write
    if type_label and len(type_label) + 2 <= inner:
        # Embed type label: ┌ type ──┐
        fill = inner - len(type_label) - 2
        top_chars = list(ch["tl"] + " " + type_label + " " + ch_h * fill + ch["tr"])
        rows[y][x:x_end] = top_chars
        if border_color is not None:
            color_rows[y][x:x_end] = [border_color] * w
        # Override type label color region
        tc = type_color or border_color
        if tc is not None:
            lbl_start = x + 2
            lbl_end = lbl_start + len(type_label)
            color_rows[y][lbl_start:lbl_end] = [tc] * len(type_label)
    else:
        top_chars = list(ch["tl"] + ch_h * inner + ch["tr"])
        rows[y][x:x_end] = top_chars
        if border_color is not None:
            color_rows[y][x:x_end] = [border_color] * w

    # Content rows — direct writes
    x_right = x + w - 1
    for i, text in enumerate(lines):
        row_y = y + 1 + i
        row = rows[row_y]
        # Left border
        row[x] = ch_v
        # Right border
        row[x_right] = ch_v
        # Content — centered
        pad_total = inner - len(text)
        pad_l = pad_total // 2
        tx0 = x + 1 + pad_l
        row[tx0 : tx0 + len(text)] = list(text)
        if border_color is not None:
            cr = color_rows[row_y]
            cr[x] = border_color
            cr[x_right] = border_color
        if text_color is not None:
            color_rows[row_y][tx0 : tx0 + len(text)] = [text_color] * len(text)

    # Fill any remaining inner rows (between content and bottom border)
    for ry in range(y + 1 + len(lines), y + h - 1):
        rows[ry][x] = ch_v
        rows[ry][x_right] = ch_v
        if border_color is not None:
            color_rows[ry][x] = border_color
            color_rows[ry][x_right] = border_color

    # Bottom border — direct slice write
    bot_y = y + h - 1
    bot_chars = list(ch["bl"] + ch_h * inner + ch["br"])
    rows[bot_y][x:x_end] = bot_chars
    if border_color is not None:
        color_rows[bot_y][x:x_end] = [border_color] * w

    # Update bounding box once for entire box
    if x < canvas._bb_x0:
        canvas._bb_x0 = x
    if x_right > canvas._bb_x1:
        canvas._bb_x1 = x_right
    if y < canvas._bb_y0:
        canvas._bb_y0 = y
    if bot_y > canvas._bb_y1:
        canvas._bb_y1 = bot_y


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
    canvas.puts(start, y, ch["h"] * (end - start + 1), color)


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
    if x < 0 or x >= canvas.width:
        return
    ch_v = chars(use_unicode)["v"]
    start = max(min(y1, y2), 0)
    end = min(max(y1, y2), canvas.height - 1)
    if start > end:
        return
    rows = canvas._rows
    if color is not None:
        colors = canvas._colors
        for y in range(start, end + 1):
            rows[y][x] = ch_v
            colors[y][x] = color
    else:
        for y in range(start, end + 1):
            rows[y][x] = ch_v
    # Update bounding box once
    if x < canvas._bb_x0:
        canvas._bb_x0 = x
    if x > canvas._bb_x1:
        canvas._bb_x1 = x
    if start < canvas._bb_y0:
        canvas._bb_y0 = start
    if end > canvas._bb_y1:
        canvas._bb_y1 = end
