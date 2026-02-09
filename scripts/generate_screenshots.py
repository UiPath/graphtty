"""Generate PNG screenshots of graphtty output for README."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

# ANSI code → RGB color (xterm-256 standard colors on dark background)
ANSI_COLORS = {
    "30": (0, 0, 0),
    "31": (205, 49, 49),
    "32": (13, 188, 121),
    "33": (229, 229, 16),
    "34": (36, 114, 200),
    "35": (188, 63, 188),
    "36": (17, 168, 205),
    "37": (204, 204, 204),
    "90": (118, 118, 118),
    "91": (241, 76, 76),
    "92": (35, 209, 139),
    "93": (245, 245, 67),
    "94": (59, 142, 234),
    "95": (214, 112, 214),
    "96": (41, 184, 219),
    "97": (242, 242, 242),
}

DEFAULT_FG = (204, 204, 204)
BG_COLOR = (30, 30, 30)


def _dim(color: tuple[int, int, int]) -> tuple[int, int, int]:
    """Reduce brightness to simulate the DIM (faint) ANSI attribute."""
    return (color[0] * 2 // 3, color[1] * 2 // 3, color[2] * 2 // 3)


def _parse_ansi(code: str) -> tuple[tuple[int, int, int] | None, bool]:
    """Parse an ANSI parameter string, returning (color, is_dim)."""
    parts = code.split(";")
    color = None
    dim = False
    for p in parts:
        if p == "2":
            dim = True
        if p in ANSI_COLORS:
            color = ANSI_COLORS[p]
    return color, dim


def line_to_char_colors(
    line: str,
) -> list[tuple[str, tuple[int, int, int]]]:
    """Parse ANSI line into per-character (char, color) list."""
    chars: list[tuple[str, tuple[int, int, int]]] = []
    current_color = DEFAULT_FG
    pos = 0
    pattern = re.compile(r"\033\[([0-9;]*)m")

    for match in pattern.finditer(line):
        # Characters before this escape
        for ch in line[pos : match.start()]:
            chars.append((ch, current_color))

        code = match.group(1)
        if code == "0":
            current_color = DEFAULT_FG
        else:
            color, dim = _parse_ansi(code)
            if color:
                current_color = _dim(color) if dim else color

        pos = match.end()

    # Remaining characters
    for ch in line[pos:]:
        chars.append((ch, current_color))

    return chars


def try_load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Try to load a monospace font, falling back to default."""
    candidates = [
        "C:/Windows/Fonts/CascadiaMono.ttf",
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/cour.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render_png(ansi_output: str, title: str = "") -> Image.Image:
    """Render ANSI terminal output to a PIL Image."""
    font_size = 16
    font = try_load_font(font_size)

    # Use the font's own advance width for perfect monospace alignment
    char_w = font.getlength("M")
    line_h = font_size + 6  # 6px line spacing

    lines = ansi_output.split("\n")
    plain_lines = [re.sub(r"\033\[[0-9;]*m", "", line) for line in lines]

    max_cols = max((len(line) for line in plain_lines), default=0)
    num_lines = len(lines)

    padding_x = 24
    padding_y = 20
    title_h = 32 if title else 0
    corner_r = 10

    width = int(round(max_cols * char_w)) + 2 * padding_x
    height = num_lines * line_h + 2 * padding_y + title_h

    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Rounded background
    draw.rounded_rectangle(
        [(0, 0), (width - 1, height - 1)],
        radius=corner_r,
        fill=BG_COLOR,
    )

    # Title
    if title:
        title_font = try_load_font(13)
        title_bbox = title_font.getbbox(title)
        title_w = title_bbox[2] - title_bbox[0]
        draw.text(
            ((width - title_w) // 2, padding_y),
            title,
            fill=(98, 114, 164),
            font=title_font,
        )

    # Render each line character by character for perfect alignment.
    # Use float x positions — Pillow handles sub-pixel text rendering.
    for row, line in enumerate(lines):
        char_colors = line_to_char_colors(line)
        y = padding_y + title_h + row * line_h

        for col, (ch, color) in enumerate(char_colors):
            if ch == " ":
                continue
            x = padding_x + col * char_w
            draw.text((x, y), ch, fill=color, font=font)

    return img


def main():
    """Generate screenshots for README samples."""
    root = Path(__file__).parent.parent
    screenshots_dir = root / "screenshots"
    screenshots_dir.mkdir(exist_ok=True)

    samples = [
        ("samples/react-agent/graph.json", "monokai", "React Agent (monokai)"),
        ("samples/deep-agent/graph.json", "ocean", "Deep Agent (ocean)"),
        ("samples/workflow-agent/graph.json", "forest", "Workflow Agent (forest)"),
        (
            "samples/supervisor-agent/graph.json",
            "dracula",
            "Supervisor Agent (dracula)",
        ),
        (
            "samples/world-map/graph.json",
            "solarized",
            "World Map (solarized)",
        ),
        (
            "samples/rag-pipeline/graph.json",
            "dracula",
            "RAG Pipeline (dracula)",
        ),
        (
            "samples/code-review/graph.json",
            "ocean",
            "Code Review Multi-Agent (ocean)",
        ),
        (
            "samples/etl-pipeline/graph.json",
            "forest",
            "ETL Data Pipeline (forest)",
        ),
        (
            "samples/function-agent/graph.json",
            "monokai",
            "Function Agent (monokai)",
        ),
        (
            "samples/book-writer-agent/graph.json",
            "nord",
            "Book Writer Agent (nord)",
        ),
    ]

    images: list[tuple[str, Image.Image]] = []

    for sample_path, theme, title in samples:
        full_path = root / sample_path
        if not full_path.exists():
            print(f"Skipping {sample_path} (not found)")
            continue

        result = subprocess.run(
            [sys.executable, "-m", "graphtty", str(full_path), "--theme", theme],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(root),
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        stdout = result.stdout.decode("utf-8", errors="replace")
        stderr = result.stderr.decode("utf-8", errors="replace")

        if result.returncode != 0:
            print(f"Error rendering {sample_path}: {stderr}")
            continue

        img = render_png(stdout.rstrip(), title)
        name = sample_path.split("/")[1]
        images.append((name, img))

    # Pad all images to the same width for visual consistency
    max_w = max((img.width for _, img in images), default=0)
    for name, img in images:
        if img.width < max_w:
            padded = Image.new("RGB", (max_w, img.height), BG_COLOR)
            padded.paste(img, ((max_w - img.width) // 2, 0))
            img = padded
        out_path = screenshots_dir / f"{name}.png"
        img.save(str(out_path), "PNG")
        print(f"Generated {out_path} ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
