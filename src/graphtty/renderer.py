"""Layout and rendering engine for directed graphs.

Uses a custom Sugiyama-style algorithm for DAG layout and renders to
ASCII/Unicode art.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from typing import Any

from .canvas import UNICODE_CHARS, Box, Canvas, chars, draw_box, draw_vline
from .layout import layout as _sugiyama_layout
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
    if not isinstance(graph, AsciiGraph):
        graph = AsciiGraph(nodes=graph.get("nodes", []), edges=graph.get("edges", []))

    if options is None:
        options = RenderOptions()

    if not graph.nodes:
        return ""

    use_color = options.theme is not DEFAULT_THEME
    canvas = _render_canvas(graph, options)
    return canvas.to_string(use_color=use_color)


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
            sub_w, sub_h = sub_canvas.visual_size

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

    # 3. Layout
    boxes = _sugiyama_layout(graph.nodes, graph.edges, node_sizes, options.padding)

    # 4. Determine canvas size — account for edge corridors
    corridor_map, extra_right = _backward_edge_corridors(graph.edges, boxes)
    # Forward skip-layer corridors (placed after backward corridors)
    min_fwd = (max(corridor_map.values()) + 3) if corridor_map else 0
    fwd_map, fwd_extra = _forward_skip_corridors(
        graph.edges, boxes, min_route_x=min_fwd
    )
    corridor_map.update(fwd_map)
    extra_right = max(extra_right, fwd_extra)
    max_x = max(b.x + b.w for b in boxes.values()) + extra_right + options.padding
    max_y = max(b.y + b.h for b in boxes.values()) + options.padding
    canvas = Canvas(max_x, max_y)

    # Pre-cache theme styles per node type (avoid redundant hash lookups)
    style_cache: dict[str, Any] = {}
    for node in graph.nodes:
        if node.type not in style_cache:
            style_cache[node.type] = theme.get_style(node.type)

    # 5. Draw nodes
    node_border_colors: dict[str, str | None] = {}
    for node in graph.nodes:
        box = boxes[node.id]
        type_lbl = _type_label(node.type, options.show_types)
        style = style_cache[node.type]
        border_c = style.border or None
        node_border_colors[node.id] = border_c
        draw_box(
            canvas,
            box,
            node_content[node.id],
            use_unicode=options.use_unicode,
            type_label=type_lbl,
            border_color=border_c,
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
# Edge drawing
# ---------------------------------------------------------------------------


def _backward_edge_corridors(
    edges: list[AsciiEdge],
    boxes: dict[str, Box],
) -> tuple[dict[int, int], int]:
    """Compute route_x corridors and margin for backward edges.

    Returns ``(corridor_map, margin)`` where *corridor_map* maps edge index
    to a global route_x value and *margin* is the extra right-side space needed.

    Each backward edge routes to the right of boxes that vertically overlap
    with the edge's path, so corridors stay close to the connected nodes.
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
            # Only clear boxes whose y-range overlaps the edge path
            src_mid_y = src.y + src.h // 2
            tgt_mid_y = tgt.y + tgt.h // 2
            y_min = min(src_mid_y, tgt_mid_y)
            y_max = max(src_mid_y, tgt_mid_y)

            local_max_right = 0
            for b in boxes.values():
                if b.y < y_max and (b.y + b.h) > y_min:
                    local_max_right = max(local_max_right, b.x + b.w)

            corridor_map[idx] = local_max_right + 3 + slot * 3
            slot += 1

    if not corridor_map:
        return corridor_map, 0

    max_route_x = max(corridor_map.values())
    # Account for label width on backward corridors
    max_label_w = 0
    for idx in corridor_map:
        lbl = edges[idx].label
        if lbl:
            max_label_w = max(max_label_w, len(lbl) + 2)  # +2 gap
    margin = max(0, max_route_x + max_label_w - global_max_right + 3)
    return corridor_map, margin


def _forward_skip_corridors(
    edges: list[AsciiEdge],
    boxes: dict[str, Box],
    min_route_x: int = 0,
) -> tuple[dict[int, int], int]:
    """Compute route_x corridors for forward edges that skip layers.

    Forward edges whose straight vertical path passes through an intermediate
    box are re-routed through a right-side corridor, similar to backward edges.

    Returns ``(corridor_map, margin)`` — same shape as backward corridors.
    """
    all_boxes = list(boxes.values())
    global_max_right = max((b.x + b.w for b in all_boxes), default=0)
    corridor_map: dict[int, int] = {}
    slot = 0
    for idx, edge in enumerate(edges):
        src = boxes.get(edge.source)
        tgt = boxes.get(edge.target)
        if src is None or tgt is None:
            continue
        if src.bottom >= tgt.top:
            continue  # not a forward edge

        src_cx = src.cx
        tgt_cx = tgt.cx
        if abs(src_cx - tgt_cx) > _STRAIGHT_TOLERANCE:
            continue  # Z-shape edges unlikely to collide with intermediate boxes

        edge_x = tgt_cx  # straight edges align to target centre
        src_bottom = src.bottom
        tgt_top = tgt.top
        # Check if vertical at edge_x passes through any intermediate box
        collides = False
        local_max_right = 0
        for b in all_boxes:
            if b is src or b is tgt:
                continue
            # Box must be vertically between src and tgt
            b_bottom = b.y + b.h
            if b_bottom <= src_bottom or b.y >= tgt_top:
                continue
            b_right = b.x + b.w
            # Box must horizontally contain the edge x
            if b.x <= edge_x < b_right:
                collides = True
            # Track rightmost box in the vertical span for corridor placement
            if b_right > local_max_right:
                local_max_right = b_right

        if collides:
            route_x = max(local_max_right + 3, min_route_x) + slot * 3
            corridor_map[idx] = route_x
            slot += 1

    if not corridor_map:
        return corridor_map, 0

    max_route_x = max(corridor_map.values())
    # Account for label width on forward corridors
    max_label_w = 0
    for idx in corridor_map:
        lbl = edges[idx].label
        if lbl:
            lbl_w = len(lbl) + 2  # +2 gap
            if lbl_w > max_label_w:
                max_label_w = lbl_w
    margin = max(0, max_route_x + max_label_w - global_max_right + 3)
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
            route_x=route_x,
            all_boxes=all_boxes,
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
    route_x: int | None = None,
    all_boxes: dict[str, Box] | None = None,
) -> None:
    """Source is above target — connect bottom-centre to top-centre."""
    if route_x is not None:
        _draw_forward_corridor(
            canvas,
            src,
            tgt,
            label,
            ch,
            route_x=route_x,
            edge_color=edge_color,
            label_color=label_color,
            all_boxes=all_boxes,
        )
        return

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
        ch_v = ch["v"]
        rows = canvas._rows
        colors = canvas._colors
        for y in range(start_y + 1, mid_y):
            rows[y][src_cx] = ch_v
            if edge_color is not None:
                colors[y][src_cx] = edge_color

        # Horizontal at mid_y
        x_min = min(src_cx, tgt_cx)
        x_max = max(src_cx, tgt_cx)
        canvas.puts(x_min, mid_y, ch["h"] * (x_max - x_min + 1), edge_color)

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
            rows[y][tgt_cx] = ch_v
            if edge_color is not None:
                colors[y][tgt_cx] = edge_color

        # Arrow above target box
        canvas.put(tgt_cx, arrow_y, ch["arrow_down"], edge_color)


def _draw_forward_corridor(
    canvas: Canvas,
    src: Box,
    tgt: Box,
    label: str | None,
    ch: dict[str, str],
    *,
    route_x: int,
    edge_color: str | None = None,
    label_color: str | None = None,
    all_boxes: dict[str, Box] | None = None,
) -> None:
    """Draw a forward edge routed through a right-side corridor.

    Used when the straight vertical path would collide with intermediate boxes.
    Routes: src ┬ → down → └──┐ corridor │ ┘──┌ → down → ▼ tgt
    """
    src_cx = src.cx
    tgt_cx = tgt.cx
    start_y = src.bottom
    end_y = tgt.top

    top_horiz_y = start_y + 2
    bot_horiz_y = end_y - 2
    # Safety clamp
    if top_horiz_y >= bot_horiz_y:
        mid = (start_y + end_y) // 2
        top_horiz_y = mid
        bot_horiz_y = mid + 1

    arrow_y = end_y - 1 if end_y - 1 > start_y else end_y

    # Pre-compute occupied intervals for the two horizontal rows
    top_intervals: list[tuple[int, int]] = []
    bot_intervals: list[tuple[int, int]] = []
    if all_boxes:
        top_intervals = _x_intervals_at_y(top_horiz_y, all_boxes, src, tgt)
        bot_intervals = _x_intervals_at_y(bot_horiz_y, all_boxes, src, tgt)

    # Direct array access for performance
    rows = canvas._rows
    colors = canvas._colors
    ch_v = ch["v"]
    ch_h = ch["h"]

    # 1. Junction at source bottom
    canvas.put(src_cx, start_y, ch["jt"], edge_color)

    # 2. Vertical from source down to top_horiz_y
    for y in range(start_y + 1, top_horiz_y):
        rows[y][src_cx] = ch_v
        if edge_color is not None:
            colors[y][src_cx] = edge_color

    # 3. Corner └ at (src_cx, top_horiz_y), horizontal to route_x, corner ┐
    canvas.put(src_cx, top_horiz_y, ch["bl"], edge_color)
    top_row = rows[top_horiz_y]
    top_color_row = colors[top_horiz_y]
    for x in range(src_cx + 1, route_x):
        if top_intervals and _x_in_intervals(x, top_intervals):
            continue
        top_row[x] = ch_h
        if edge_color is not None:
            top_color_row[x] = edge_color
    canvas.put(route_x, top_horiz_y, ch["tr"], edge_color)

    # 4. Vertical down corridor
    for y in range(top_horiz_y + 1, bot_horiz_y):
        rows[y][route_x] = ch_v
        if edge_color is not None:
            colors[y][route_x] = edge_color

    # 5. Corner ┘ at (route_x, bot_horiz_y), horizontal back to tgt_cx, corner ┌
    canvas.put(route_x, bot_horiz_y, ch["br"], edge_color)
    bot_row = rows[bot_horiz_y]
    bot_color_row = colors[bot_horiz_y]
    for x in range(tgt_cx + 1, route_x):
        if bot_intervals and _x_in_intervals(x, bot_intervals):
            continue
        bot_row[x] = ch_h
        if edge_color is not None:
            bot_color_row[x] = edge_color
    canvas.put(tgt_cx, bot_horiz_y, ch["tl"], edge_color)

    # 6. Vertical down to arrow
    for y in range(bot_horiz_y + 1, arrow_y):
        rows[y][tgt_cx] = ch_v
        if edge_color is not None:
            colors[y][tgt_cx] = edge_color

    # 7. Arrow above target box
    canvas.put(tgt_cx, arrow_y, ch["arrow_down"], edge_color)

    # 8. Label alongside corridor vertical
    if label:
        label_y = (top_horiz_y + bot_horiz_y) // 2
        canvas.puts(route_x + 2, label_y, label, label_color)


def _x_intervals_at_y(
    y: int, boxes: dict[str, Box], src: Box, tgt: Box
) -> list[tuple[int, int]]:
    """Return sorted (x_start, x_end) intervals of boxes overlapping row *y*."""
    intervals = []
    for b in boxes.values():
        if b is src or b is tgt:
            continue
        if b.y <= y < b.y + b.h:
            intervals.append((b.x, b.x + b.w))
    intervals.sort()
    return intervals


def _x_in_intervals(x: int, intervals: list[tuple[int, int]]) -> bool:
    """Return True if *x* falls inside any of the pre-sorted intervals."""
    for x0, x1 in intervals:
        if x0 > x:
            break
        if x0 <= x < x1:
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

    # Pre-compute occupied x-intervals for the two horizontal rows
    src_intervals: list[tuple[int, int]] = []
    tgt_intervals: list[tuple[int, int]] = []
    if all_boxes:
        src_intervals = _x_intervals_at_y(src_mid_y, all_boxes, src, tgt)
        tgt_intervals = _x_intervals_at_y(tgt_mid_y, all_boxes, src, tgt)

    # Horizontal from source right side — skip intermediate node boxes
    for x in range(src.x + src.w, route_x + 1):
        if src_intervals and _x_in_intervals(x, src_intervals):
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
        if tgt_intervals and _x_in_intervals(x, tgt_intervals):
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
        span = tgt.x - (src.x + src.w)
        if span > 0:
            canvas.puts(src.x + src.w, y, ch["h"] * span, edge_color)
        canvas.put(tgt.x, y, ch["arrow_right"], edge_color)
    elif tgt.x + tgt.w <= src.x:
        # tgt is left of src
        y = max(src.y, tgt.y) + 1
        span = src.x - (tgt.x + tgt.w)
        if span > 0:
            canvas.puts(tgt.x + tgt.w, y, ch["h"] * span, edge_color)
        canvas.put(tgt.x + tgt.w - 1, y, ch["arrow_left"], edge_color)

    if label:
        mid_x = (src.cx + tgt.cx) // 2 - len(label) // 2
        y_lbl = max(src.y, tgt.y)
        canvas.puts(mid_x, y_lbl, label, label_color)
