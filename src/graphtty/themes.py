"""Theme system for colored ASCII/Unicode graph rendering."""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# ANSI escape codes
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"

# Foreground colors
BLACK = "\033[30m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

BRIGHT_BLACK = "\033[90m"
BRIGHT_RED = "\033[91m"
BRIGHT_GREEN = "\033[92m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_BLUE = "\033[94m"
BRIGHT_MAGENTA = "\033[95m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_WHITE = "\033[97m"

# Combined DIM + color (single escape sequence for Windows compatibility)
DIM_RED = "\033[2;31m"
DIM_GREEN = "\033[2;32m"
DIM_YELLOW = "\033[2;33m"
DIM_BLUE = "\033[2;34m"
DIM_MAGENTA = "\033[2;35m"
DIM_CYAN = "\033[2;36m"
DIM_WHITE = "\033[2;37m"


# ---------------------------------------------------------------------------
# Style dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NodeStyle:
    """Visual style for a node type."""

    border: str = ""
    text: str = ""
    type_label: str = ""


def _stable_hash(s: str) -> int:
    """FNV-1a hash — deterministic across Python sessions."""
    h = 2166136261
    for c in s:
        h = (h ^ ord(c)) * 16777619 & 0xFFFFFFFF
    return h


@dataclass(frozen=True)
class Theme:
    """A complete color theme for graph rendering.

    ``palette`` is a list of :class:`NodeStyle` instances.  Each node type
    is assigned a style from the palette based on a deterministic hash of
    the type name, so different types get different colors automatically.
    Nodes with an empty type string use ``default_style``.

    All built-in palettes have 6 entries.  With the FNV-1a hash the most
    common generic type ``"node"`` lands on index **5**, so that slot
    holds each theme's primary / signature color.
    """

    name: str
    palette: list[NodeStyle] = field(default_factory=list)
    default_style: NodeStyle = field(default_factory=NodeStyle)
    edge: str = ""
    edge_label: str = ""

    def get_style(self, node_type: str) -> NodeStyle:
        """Return the style for *node_type*."""
        if not node_type or not self.palette:
            return self.default_style
        return self.palette[_stable_hash(node_type) % len(self.palette)]


# ---------------------------------------------------------------------------
# Built-in themes
#
# Palette layout (6 entries, FNV-1a assignments for common types):
#   [0] model, hub, __end__, agent
#   [1] exit, subgraph
#   [2] task, condition, router
#   [3] tool, action, country, entry, input
#   [4] end, output
#   [5] node, step, start, __start__, worker  ← PRIMARY color
# ---------------------------------------------------------------------------

# No colors — plain text (identical to pre-theme behaviour)
DEFAULT = Theme(name="default")

MONOKAI = Theme(
    name="monokai",
    palette=[
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_CYAN, type_label=CYAN),
        NodeStyle(border=BRIGHT_MAGENTA, text=BRIGHT_MAGENTA, type_label=MAGENTA),
        NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_BLUE, type_label=BLUE),
        NodeStyle(border=BRIGHT_YELLOW, text=BRIGHT_YELLOW, type_label=YELLOW),
        NodeStyle(border=BRIGHT_RED, text=BRIGHT_RED, type_label=RED),
        NodeStyle(border=GREEN, text=GREEN, type_label=DIM_GREEN),
    ],
    default_style=NodeStyle(border=GREEN, text=GREEN, type_label=DIM_GREEN),
    edge=BRIGHT_BLACK,
    edge_label=BRIGHT_YELLOW,
)

OCEAN = Theme(
    name="ocean",
    palette=[
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_WHITE, type_label=DIM_CYAN),
        NodeStyle(border=BRIGHT_MAGENTA, text=BRIGHT_WHITE, type_label=MAGENTA),
        NodeStyle(border=CYAN, text=BRIGHT_WHITE, type_label=DIM_CYAN),
        NodeStyle(border=BRIGHT_GREEN, text=BRIGHT_WHITE, type_label=GREEN),
        NodeStyle(border=BRIGHT_WHITE, text=BRIGHT_WHITE, type_label=DIM_WHITE),
        NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_WHITE, type_label=BLUE),
    ],
    default_style=NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_WHITE, type_label=BLUE),
    edge=CYAN,
    edge_label=BRIGHT_WHITE,
)

FOREST = Theme(
    name="forest",
    palette=[
        NodeStyle(border=YELLOW, text=BRIGHT_YELLOW, type_label=DIM_YELLOW),
        NodeStyle(border=BRIGHT_YELLOW, text=BRIGHT_YELLOW, type_label=YELLOW),
        NodeStyle(border=CYAN, text=BRIGHT_CYAN, type_label=DIM_CYAN),
        NodeStyle(border=GREEN, text=BRIGHT_GREEN, type_label=DIM_GREEN),
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_CYAN, type_label=DIM_CYAN),
        NodeStyle(border=BRIGHT_GREEN, text=BRIGHT_GREEN, type_label=DIM_GREEN),
    ],
    default_style=NodeStyle(
        border=BRIGHT_GREEN, text=BRIGHT_GREEN, type_label=DIM_GREEN
    ),
    edge=DIM_GREEN,
    edge_label=BRIGHT_YELLOW,
)

DRACULA = Theme(
    name="dracula",
    palette=[
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_WHITE, type_label=CYAN),
        NodeStyle(border=BRIGHT_GREEN, text=BRIGHT_WHITE, type_label=GREEN),
        NodeStyle(border=BRIGHT_YELLOW, text=BRIGHT_WHITE, type_label=YELLOW),
        NodeStyle(border=BRIGHT_RED, text=BRIGHT_WHITE, type_label=RED),
        NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_WHITE, type_label=BLUE),
        NodeStyle(border=BRIGHT_MAGENTA, text=BRIGHT_WHITE, type_label=MAGENTA),
    ],
    default_style=NodeStyle(
        border=BRIGHT_MAGENTA, text=BRIGHT_WHITE, type_label=DIM_MAGENTA
    ),
    edge=BRIGHT_BLACK,
    edge_label=BRIGHT_CYAN,
)

SOLARIZED = Theme(
    name="solarized",
    palette=[
        NodeStyle(border=GREEN, text=BRIGHT_GREEN, type_label=DIM_GREEN),
        NodeStyle(border=MAGENTA, text=BRIGHT_MAGENTA, type_label=DIM_MAGENTA),
        NodeStyle(border=CYAN, text=BRIGHT_CYAN, type_label=DIM_CYAN),
        NodeStyle(border=YELLOW, text=BRIGHT_YELLOW, type_label=DIM_YELLOW),
        NodeStyle(border=RED, text=BRIGHT_RED, type_label=DIM_RED),
        NodeStyle(border=BLUE, text=BRIGHT_BLUE, type_label=DIM_BLUE),
    ],
    default_style=NodeStyle(border=BLUE, text=BRIGHT_BLUE, type_label=DIM_BLUE),
    edge=BRIGHT_BLACK,
    edge_label=YELLOW,
)

NORD = Theme(
    name="nord",
    palette=[
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_WHITE, type_label=DIM_CYAN),
        NodeStyle(border=BRIGHT_GREEN, text=BRIGHT_WHITE, type_label=DIM_GREEN),
        NodeStyle(border=BRIGHT_YELLOW, text=BRIGHT_WHITE, type_label=DIM_YELLOW),
        NodeStyle(border=BRIGHT_MAGENTA, text=BRIGHT_WHITE, type_label=DIM_MAGENTA),
        NodeStyle(border=BRIGHT_RED, text=BRIGHT_WHITE, type_label=DIM_RED),
        NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_WHITE, type_label=DIM_BLUE),
    ],
    default_style=NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_WHITE, type_label=DIM_BLUE),
    edge=DIM_CYAN,
    edge_label=BRIGHT_CYAN,
)

CATPPUCCIN = Theme(
    name="catppuccin",
    palette=[
        NodeStyle(border=BRIGHT_GREEN, text=BRIGHT_GREEN, type_label=DIM_GREEN),
        NodeStyle(border=BRIGHT_MAGENTA, text=BRIGHT_MAGENTA, type_label=DIM_MAGENTA),
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_CYAN, type_label=DIM_CYAN),
        NodeStyle(border=BRIGHT_YELLOW, text=BRIGHT_YELLOW, type_label=DIM_YELLOW),
        NodeStyle(border=BRIGHT_RED, text=BRIGHT_RED, type_label=DIM_RED),
        NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_BLUE, type_label=DIM_BLUE),
    ],
    default_style=NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_BLUE, type_label=DIM_BLUE),
    edge=DIM_MAGENTA,
    edge_label=BRIGHT_MAGENTA,
)

GRUVBOX = Theme(
    name="gruvbox",
    palette=[
        NodeStyle(border=BRIGHT_GREEN, text=BRIGHT_GREEN, type_label=DIM_GREEN),
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_CYAN, type_label=DIM_CYAN),
        NodeStyle(border=BRIGHT_RED, text=BRIGHT_RED, type_label=RED),
        NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_BLUE, type_label=DIM_BLUE),
        NodeStyle(border=BRIGHT_MAGENTA, text=BRIGHT_MAGENTA, type_label=DIM_MAGENTA),
        NodeStyle(border=BRIGHT_YELLOW, text=BRIGHT_YELLOW, type_label=DIM_YELLOW),
    ],
    default_style=NodeStyle(
        border=BRIGHT_YELLOW, text=BRIGHT_YELLOW, type_label=DIM_YELLOW
    ),
    edge=BRIGHT_BLACK,
    edge_label=BRIGHT_YELLOW,
)

TOKYO_NIGHT = Theme(
    name="tokyo-night",
    palette=[
        NodeStyle(border=BRIGHT_CYAN, text=BRIGHT_WHITE, type_label=DIM_CYAN),
        NodeStyle(border=BRIGHT_GREEN, text=BRIGHT_WHITE, type_label=DIM_GREEN),
        NodeStyle(border=BRIGHT_YELLOW, text=BRIGHT_WHITE, type_label=DIM_YELLOW),
        NodeStyle(border=BRIGHT_MAGENTA, text=BRIGHT_WHITE, type_label=MAGENTA),
        NodeStyle(border=BRIGHT_RED, text=BRIGHT_WHITE, type_label=DIM_RED),
        NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_CYAN, type_label=DIM_BLUE),
    ],
    default_style=NodeStyle(border=BRIGHT_BLUE, text=BRIGHT_CYAN, type_label=DIM_BLUE),
    edge=DIM_BLUE,
    edge_label=BRIGHT_CYAN,
)

# ---------------------------------------------------------------------------
# Theme registry
# ---------------------------------------------------------------------------

_THEMES: dict[str, Theme] = {
    t.name: t
    for t in [
        DEFAULT,
        MONOKAI,
        OCEAN,
        FOREST,
        DRACULA,
        SOLARIZED,
        NORD,
        CATPPUCCIN,
        GRUVBOX,
        TOKYO_NIGHT,
    ]
}


def get_theme(name: str) -> Theme:
    """Return a built-in theme by *name*.

    Raises :class:`ValueError` if the name is not recognised.
    """
    theme = _THEMES.get(name)
    if theme is None:
        available = ", ".join(sorted(_THEMES))
        raise ValueError(f"Unknown theme {name!r}. Available: {available}")
    return theme


def list_themes() -> list[str]:
    """Return sorted list of available theme names."""
    return sorted(_THEMES)
