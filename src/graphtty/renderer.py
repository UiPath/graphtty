"""Layout and rendering engine for directed graphs.

Uses grandalf (Sugiyama algorithm) for DAG layout and renders to ASCII/Unicode art.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from typing import Any

from grandalf.graphs import Edge, Graph, Vertex  # type: ignore[import-untyped]
from grandalf.layouts import SugiyamaLayout  # type: ignore[import-untyped]

from .canvas import UNICODE_CHARS, Box, Canvas, chars, draw_box, draw_vline
from .themes import DEFAULT as DEFAULT_THEME
from .themes import Theme
from .types import AsciiEdge, AsciiGraph, AsciiNode

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# Tolerance: if source and target centre-x differ by at most this many
# characters, treat the edge as a straight vertical line.
_STRAIGHT_TOLERANCE = 2

_MAX_ITEMS_SHOWN = 5
_META_MAX_LINE = 40


@dataclass
class RenderOptions:
    """Options for ASCII/Unicode rendering."""

    use_unicode: bool = True
    show_types: bool = True
    padding: int = 2
    theme: Theme = field(default_factory=lambda: DEFAULT_THEME)
    max_width: int | None = None


def render(
    graph: AsciiGraph | dict[str, Any],
    options: RenderOptions | None = None,
) -> str:
    """Render an *AsciiGraph* to ASCII/Unicode art.

    *graph* can be an :class:`AsciiGraph` instance or a plain dict with
    ``nodes`` and ``edges`` keys.

    Returns a multi-line string ready for ``print()``.
    """
    if isinstance(graph, dict):
        graph = AsciiGraph(**graph)

    if options is None:
        options = RenderOptions()

    if not graph.nodes:
        return ""

    use_color = options.theme is not DEFAULT_THEME
    canvas = _render_canvas(graph, options)
    return canvas.to_string(use_color=use_color)


def _canvas_visual_size(c: Canvas) -> tuple[int, int]:
    """Return (width, height) of the non-space bounding box in *c*."""
    w = 0
    h = 0
    for y in range(c.height):
        row = c._rows[y]
        rx = len(row) - 1
        while rx >= 0 and row[rx] == " ":
            rx -= 1
        if rx >= 0:
            h = y + 1
            w = max(w, rx + 1)
    return w, h


def _render_canvas(
    graph: AsciiGraph,
    options: RenderOptions,
) -> Canvas:
    """Adaptive rendering — re-renders with shorter descriptions to fit max_width."""
    max_width = options.max_width
    meta_max = _META_MAX_LINE

    for _ in range(3):
        canvas = _do_render_canvas(graph, options, meta_max)
        if max_width is None or canvas.width <= max_width:
            return canvas
        if meta_max <= 0:
            return canvas
        ratio = max_width / canvas.width
        meta_max = max(0, int(meta_max * ratio) - 1)

    return canvas


def _do_render_canvas(
    graph: AsciiGraph,
    options: RenderOptions,
    meta_max_line: int = _META_MAX_LINE,
) -> Canvas:
    """Core rendering — returns the Canvas (with per-cell colors)."""
    theme = options.theme

    # 1. Recursively render subgraphs as Canvas objects (with no padding —
    #    the parent box provides the frame)
    sub_options = RenderOptions(
        use_unicode=options.use_unicode,
        show_types=options.show_types,
        padding=0,
        theme=options.theme,
        max_width=options.max_width,
    )
    subgraph_canvases: dict[str, Canvas] = {}
    for node in graph.nodes:
        if node.subgraph and node.subgraph.nodes:
            subgraph_canvases[node.id] = _do_render_canvas(
                node.subgraph, sub_options, meta_max_line
            )

    # 2. Compute node box sizes (in character coordinates)
    node_sizes: dict[str, tuple[int, int]] = {}
    node_content: dict[str, list[str]] = {}
    # For subgraph nodes: header line count and visual sub-size
    subgraph_meta: dict[
        str, tuple[int, int, int]
    ] = {}  # id -> (header_lines, sub_w, sub_h)

    for node in graph.nodes:
        content_lines: list[str] = []

        # Build metadata detail lines (description wrapping)
        meta_lines = _metadata_lines(node, meta_max_line)

        if node.id in subgraph_canvases:
            # Subgraph node: size from the canvas (NOT from string lengths)
            sub_canvas = subgraph_canvases[node.id]
            sub_w, sub_h = _canvas_visual_size(sub_canvas)

            header_w = len(node.name)
            for ml in meta_lines:
                header_w = max(header_w, len(ml))

            inner_w = max(sub_w + 2, header_w)  # +2 for padding around subgraph
            box_w = inner_w + 2  # borders

            # Header lines (name + metadata) — drawn as centered text
            content_lines.append(node.name.center(inner_w))
            for ml in meta_lines:
                content_lines.append(ml.center(inner_w))
            header_count = len(content_lines)

            # Reserve blank lines for the subgraph area (blitted later)
            for _ in range(sub_h):
                content_lines.append(" " * inner_w)

            box_h = len(content_lines) + 2  # borders
            subgraph_meta[node.id] = (header_count, sub_w, sub_h)
        else:
            # Regular node
            content_lines.append(node.name)
            for ml in meta_lines:
                content_lines.append(ml)

            inner_w = max(len(line) for line in content_lines)
            # Ensure box is wide enough for the type label in the border
            type_lbl = _type_label(node.type, options.show_types)
            if type_lbl:
                inner_w = max(inner_w, len(type_lbl) + 2)
            box_w = inner_w + 4  # 1 border + 1 pad + content + 1 pad + 1 border
            box_h = len(content_lines) + 2  # top border + content + bottom border

        node_sizes[node.id] = (box_w, box_h)
        node_content[node.id] = content_lines

    # 3. Layout with grandalf
    boxes = _layout(graph.nodes, graph.edges, node_sizes, options.padding)

    # 4. Determine canvas size — account for backward-edge corridors
    corridor_map, extra_right = _backward_edge_corridors(graph.edges, boxes)
    max_x = max(b.x + b.w for b in boxes.values()) + extra_right + options.padding
    max_y = max(b.y + b.h for b in boxes.values()) + options.padding
    canvas = Canvas(max_x, max_y)

    # 5. Draw nodes
    for node in graph.nodes:
        box = boxes[node.id]
        type_lbl = _type_label(node.type, options.show_types)
        style = theme.get_style(node.type)
        draw_box(
            canvas,
            box,
            node_content[node.id],
            use_unicode=options.use_unicode,
            type_label=type_lbl,
            border_color=style.border or None,
            text_color=style.text or None,
            type_color=style.type_label or None,
        )

        # Blit subgraph canvas into the parent box (preserving per-cell colors)
        if node.id in subgraph_canvases:
            sub_canvas = subgraph_canvases[node.id]
            header_count = subgraph_meta[node.id][0]
            blit_x = box.x + 1 + 1  # border + 1 char padding
            blit_y = box.y + 1 + header_count  # border + header lines
            canvas.blit_canvas(sub_canvas, blit_x, blit_y)

    # 6. Draw edges
    edge_color = theme.edge or None
    label_color = theme.edge_label or None
    # Map node id → border color for junction/arrow tinting
    node_border_colors: dict[str, str | None] = {}
    for node in graph.nodes:
        style = theme.get_style(node.type)
        node_border_colors[node.id] = style.border or None
    for idx, edge in enumerate(graph.edges):
        src_box = boxes.get(edge.source)
        tgt_box = boxes.get(edge.target)
        if src_box is None or tgt_box is None:
            continue
        _draw_edge(
            canvas,
            src_box,
            tgt_box,
            edge.label,
            options.use_unicode,
            edge_color=edge_color,
            label_color=label_color,
            route_x=corridor_map.get(idx),
            all_boxes=boxes,
            src_color=node_border_colors.get(edge.source),
        )

    return canvas


# ---------------------------------------------------------------------------
# Metadata helpers
# ---------------------------------------------------------------------------

# Node types that are structural markers — no border label needed.
_HIDDEN_TYPE_LABELS = {"__start__", "__end__"}


def _type_label(node_type: str, show_types: bool) -> str | None:
    """Return the border type label, or *None* if it should be hidden."""
    if not show_types:
        return None
    if node_type in _HIDDEN_TYPE_LABELS:
        return None
    return node_type


def _metadata_lines(node: AsciiNode, max_line: int = _META_MAX_LINE) -> list[str]:
    """Build display lines from *node.description* with word-wrapping."""
    if not node.description or max_line <= 0:
        return []

    # Split comma-separated descriptions into wrapped lines
    items = [s.strip() for s in node.description.split(",") if s.strip()]
    if not items:
        return []

    # If it's a single value (no commas), word-wrap it
    if len(items) == 1:
        return textwrap.wrap(items[0], width=max_line) or [items[0]]

    # Multiple items: wrap at max_line
    lines: list[str] = []
    shown = items[:_MAX_ITEMS_SHOWN]
    remainder = len(items) - len(shown)
    row: list[str] = []
    row_len = 0
    for name in shown:
        added = len(name) + (2 if row else 0)  # ", " separator
        if row and row_len + added > max_line:
            lines.append(", ".join(row))
            row = [name]
            row_len = len(name)
        else:
            row.append(name)
            row_len += added
    if remainder > 0:
        suffix = f"+{remainder} more"
        added = len(suffix) + (2 if row else 0)
        if row and row_len + added > max_line:
            lines.append(", ".join(row))
            lines.append(suffix)
        else:
            row.append(suffix)
            lines.append(", ".join(row))
    elif row:
        lines.append(", ".join(row))

    return lines


# ---------------------------------------------------------------------------
# Layout engine (grandalf wrapper)
# ---------------------------------------------------------------------------


class _VertexView:
    """Minimal view for grandalf SugiyamaLayout."""

    def __init__(self, w: float = 10, h: float = 4) -> None:
        self.w = w
        self.h = h
        self.xy = (0.0, 0.0)


def _layout(
    nodes: list[AsciiNode],
    edges: list[AsciiEdge],
    node_sizes: dict[str, tuple[int, int]],
    padding: int,
) -> dict[str, Box]:
    """Compute box positions using grandalf Sugiyama layout."""
    if len(nodes) == 1:
        # Single node — centre it
        w, h = node_sizes[nodes[0].id]
        return {nodes[0].id: Box(x=padding, y=padding, w=w, h=h)}

    vertices: dict[str, Vertex] = {}
    for node in nodes:
        w, h = node_sizes[node.id]
        v = Vertex(node.id)
        v.view = _VertexView(w, h)
        vertices[node.id] = v

    edge_list: list[Edge] = []
    for edge in edges:
        src_v = vertices.get(edge.source)
        tgt_v = vertices.get(edge.target)
        if src_v and tgt_v:
            edge_list.append(Edge(src_v, tgt_v))

    g = Graph(list(vertices.values()), edge_list)

    # Layout each connected component and arrange them side-by-side
    x_offset = 0.0
    try:
        for component in g.C:
            sug = SugiyamaLayout(component)
            sug.xspace = 4
            sug.yspace = 2
            for v in component.sV:
                if v.view is None:
                    v.view = _VertexView()
            sug.init_all()
            sug.draw()

            # Shift this component right so it doesn't overlap previous ones
            if x_offset > 0:
                comp_min_x = min(v.view.xy[0] - v.view.w / 2 for v in component.sV)
                shift = x_offset - comp_min_x + 4  # 4 chars gap between components
                for v in component.sV:
                    cx, cy = v.view.xy
                    v.view.xy = (cx + shift, cy)

            comp_max_x = max(v.view.xy[0] + v.view.w / 2 for v in component.sV)
            x_offset = comp_max_x
    except Exception as err:
        raise RuntimeError(f"Layout failed: {err}") from err

    # Convert centre coordinates to top-left Box instances
    raw_boxes: dict[str, Box] = {}
    for node in nodes:
        v = vertices[node.id]
        cx, cy = v.view.xy
        w, h = node_sizes[node.id]
        raw_boxes[node.id] = Box(
            x=int(round(cx - w / 2)),
            y=int(round(cy - h / 2)),
            w=w,
            h=h,
        )

    # Compact horizontally: close excess gaps between same-layer nodes
    raw_boxes = _compact_x(raw_boxes, xspace=4)

    # Normalise: shift everything so minimum coordinate equals *padding*
    min_x = min(b.x for b in raw_boxes.values())
    min_y = min(b.y for b in raw_boxes.values())
    dx = padding - min_x
    dy = padding - min_y

    return {
        nid: Box(x=b.x + dx, y=b.y + dy, w=b.w, h=b.h) for nid, b in raw_boxes.items()
    }


def _compact_x(boxes: dict[str, Box], xspace: int) -> dict[str, Box]:
    """Reduce excess horizontal gaps between nodes on the same layer.

    Grandalf's coordinate assignment can over-spread nodes.  This pass
    keeps the left-to-right ordering but closes gaps so adjacent nodes
    are separated by at most *xspace* characters.
    """
    from collections import defaultdict

    # Group by layer — nodes with the same centre-y are on the same layer
    layers: dict[int, list[str]] = defaultdict(list)
    for nid, b in boxes.items():
        cy = round(b.y + b.h / 2)
        layers[cy].append(nid)

    shifts: dict[str, int] = {}  # nid → cumulative x shift

    for _cy, nids in layers.items():
        if len(nids) < 2:
            continue
        nids.sort(key=lambda n: boxes[n].x)

        for i in range(1, len(nids)):
            prev = nids[i - 1]
            curr = nids[i]
            prev_right = boxes[prev].x + shifts.get(prev, 0) + boxes[prev].w
            curr_x = boxes[curr].x + shifts.get(curr, 0)
            gap = curr_x - prev_right
            if gap > xspace:
                shifts[curr] = shifts.get(curr, 0) - (gap - xspace)

    if not shifts:
        return boxes

    return {
        nid: Box(x=b.x + shifts.get(nid, 0), y=b.y, w=b.w, h=b.h)
        for nid, b in boxes.items()
    }


# ---------------------------------------------------------------------------
# Edge drawing
# ---------------------------------------------------------------------------


def _backward_edge_corridors(
    edges: list[AsciiEdge],
    boxes: dict[str, Box],
) -> tuple[dict[int, int], int]:
    """Compute route_x corridors and margin for backward edges.

    Returns ``(corridor_map, margin)`` where *corridor_map* maps edge index
    to a global route_x value and *margin* is the extra right-side space needed.

    All backward edges route to the right of **every** box in the graph so
    they never cut through other nodes (e.g. subgraph boxes).
    """
    global_max_right = max((b.x + b.w for b in boxes.values()), default=0)
    corridor_map: dict[int, int] = {}
    slot = 0
    for idx, edge in enumerate(edges):
        src = boxes.get(edge.source)
        tgt = boxes.get(edge.target)
        if src is None or tgt is None:
            continue
        if tgt.bottom < src.top:
            corridor_map[idx] = global_max_right + 3 + slot * 3
            slot += 1
    margin = (3 + slot * 3) if slot else 0
    return corridor_map, margin


def _draw_edge(
    canvas: Canvas,
    src: Box,
    tgt: Box,
    label: str | None,
    use_unicode: bool,
    *,
    edge_color: str | None = None,
    label_color: str | None = None,
    route_x: int | None = None,
    all_boxes: dict[str, Box] | None = None,
    src_color: str | None = None,
) -> None:
    """Draw an orthogonal edge from *src* bottom to *tgt* top."""
    ch = chars(use_unicode)
    # Edge inherits source node's border color when available
    color = src_color or edge_color

    if src.bottom < tgt.top:
        _draw_forward_edge(
            canvas,
            src,
            tgt,
            label,
            ch,
            edge_color=color,
            label_color=label_color,
        )
    elif tgt.bottom < src.top:
        _draw_backward_edge(
            canvas,
            src,
            tgt,
            label,
            ch,
            edge_color=color,
            label_color=label_color,
            route_x=route_x,
            all_boxes=all_boxes,
        )
    else:
        _draw_side_edge(
            canvas,
            src,
            tgt,
            label,
            ch,
            edge_color=color,
            label_color=label_color,
        )


def _draw_forward_edge(
    canvas: Canvas,
    src: Box,
    tgt: Box,
    label: str | None,
    ch: dict[str, str],
    *,
    edge_color: str | None = None,
    label_color: str | None = None,
) -> None:
    """Source is above target — connect bottom-centre to top-centre."""
    src_cx = src.cx
    tgt_cx = tgt.cx
    start_y = src.bottom
    end_y = tgt.top
    is_unicode = ch is UNICODE_CHARS

    # Arrow goes one row above target box (not on the border)
    arrow_y = end_y - 1 if end_y - 1 > start_y else end_y

    # Treat near-straight edges as perfectly straight
    if abs(src_cx - tgt_cx) <= _STRAIGHT_TOLERANCE:
        cx = tgt_cx  # align to target
        canvas.put(cx, start_y, ch["jt"], edge_color)
        draw_vline(
            canvas,
            cx,
            start_y + 1,
            arrow_y - 1,
            use_unicode=is_unicode,
            color=edge_color,
        )
        # Label at midpoint
        if label:
            mid_y = (start_y + arrow_y) // 2
            canvas.puts(cx + 2, mid_y, label, label_color)
        # Arrow above target box
        canvas.put(cx, arrow_y, ch["arrow_down"], edge_color)
    else:
        # Z-shaped route — keep horizontal segment close to the source box
        # so it doesn't cut through tall target boxes (e.g. subgraphs).
        canvas.put(src_cx, start_y, ch["jt"], edge_color)
        mid_y = start_y + 2
        if mid_y >= end_y - 1:
            mid_y = (start_y + end_y) // 2

        # Vertical from source down to mid_y
        for y in range(start_y + 1, mid_y):
            canvas.put(src_cx, y, ch["v"], edge_color)

        # Horizontal at mid_y
        x_min = min(src_cx, tgt_cx)
        x_max = max(src_cx, tgt_cx)
        for x in range(x_min, x_max + 1):
            canvas.put(x, mid_y, ch["h"], edge_color)

        # Corners
        if src_cx < tgt_cx:
            canvas.put(src_cx, mid_y, ch["bl"], edge_color)  # └
            canvas.put(tgt_cx, mid_y, ch["tr"], edge_color)  # ┐
        else:
            canvas.put(src_cx, mid_y, ch["br"], edge_color)  # ┘
            canvas.put(tgt_cx, mid_y, ch["tl"], edge_color)  # ┌

        # Label between source and target, just below source border
        if label:
            mid_x = (src_cx + tgt_cx) // 2 - len(label) // 2
            canvas.puts(mid_x, start_y + 1, label, label_color)

        # Vertical from mid_y down to arrow
        for y in range(mid_y + 1, arrow_y):
            canvas.put(tgt_cx, y, ch["v"], edge_color)

        # Arrow above target box
        canvas.put(tgt_cx, arrow_y, ch["arrow_down"], edge_color)


def _inside_other_box(
    x: int, y: int, boxes: dict[str, Box], src: Box, tgt: Box
) -> bool:
    """Return True if (x, y) falls inside any box other than *src* or *tgt*."""
    for b in boxes.values():
        if b is src or b is tgt:
            continue
        if b.x <= x < b.x + b.w and b.y <= y < b.y + b.h:
            return True
    return False


def _draw_backward_edge(
    canvas: Canvas,
    src: Box,
    tgt: Box,
    label: str | None,
    ch: dict[str, str],
    *,
    edge_color: str | None = None,
    label_color: str | None = None,
    route_x: int | None = None,
    all_boxes: dict[str, Box] | None = None,
) -> None:
    """Target is above source — route on the right side."""
    if route_x is None:
        route_x = max(src.x + src.w, tgt.x + tgt.w) + 3
    src_mid_y = src.y + src.h // 2
    tgt_mid_y = tgt.y + tgt.h // 2

    # Horizontal from source right side — skip intermediate node boxes
    for x in range(src.x + src.w, route_x + 1):
        if all_boxes and _inside_other_box(x, src_mid_y, all_boxes, src, tgt):
            continue
        canvas.put(x, src_mid_y, ch["h"], edge_color)
    canvas.put(src.x + src.w - 1, src_mid_y, ch["jl"], edge_color)  # ├

    # Vertical
    y_min = min(src_mid_y, tgt_mid_y)
    y_max = max(src_mid_y, tgt_mid_y)
    for y in range(y_min, y_max + 1):
        canvas.put(route_x, y, ch["v"], edge_color)

    # Corners
    if src_mid_y > tgt_mid_y:
        canvas.put(route_x, src_mid_y, ch["br"], edge_color)
        canvas.put(route_x, tgt_mid_y, ch["tr"], edge_color)
    else:
        canvas.put(route_x, src_mid_y, ch["tl"], edge_color)
        canvas.put(route_x, tgt_mid_y, ch["bl"], edge_color)

    # Horizontal to target right side — skip intermediate node boxes
    for x in range(tgt.x + tgt.w, route_x):
        if all_boxes and _inside_other_box(x, tgt_mid_y, all_boxes, src, tgt):
            continue
        canvas.put(x, tgt_mid_y, ch["h"], edge_color)

    # Arrow at target border
    canvas.put(tgt.x + tgt.w - 1, tgt_mid_y, ch["arrow_left"], edge_color)

    # Label
    if label:
        canvas.puts(route_x + 2, (src_mid_y + tgt_mid_y) // 2, label, label_color)


def _draw_side_edge(
    canvas: Canvas,
    src: Box,
    tgt: Box,
    label: str | None,
    ch: dict[str, str],
    *,
    edge_color: str | None = None,
    label_color: str | None = None,
) -> None:
    """Boxes overlap vertically — draw a horizontal connector."""
    if src.x + src.w <= tgt.x:
        # src is left of tgt
        y = max(src.y, tgt.y) + 1
        for x in range(src.x + src.w, tgt.x):
            canvas.put(x, y, ch["h"], edge_color)
        canvas.put(tgt.x, y, ch["arrow_right"], edge_color)
    elif tgt.x + tgt.w <= src.x:
        # tgt is left of src
        y = max(src.y, tgt.y) + 1
        for x in range(tgt.x + tgt.w, src.x):
            canvas.put(x, y, ch["h"], edge_color)
        canvas.put(tgt.x + tgt.w - 1, y, ch["arrow_left"], edge_color)

    if label:
        mid_x = (src.cx + tgt.cx) // 2 - len(label) // 2
        y_lbl = max(src.y, tgt.y)
        canvas.puts(mid_x, y_lbl, label, label_color)
