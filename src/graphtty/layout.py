"""Sugiyama-style layout engine for DAGs."""

from __future__ import annotations

from collections import deque
from typing import Any

from .canvas import Box


def layout(
    nodes: list[Any],
    edges: list[Any],
    node_sizes: dict[str, tuple[int, int]],
    padding: int,
) -> dict[str, Box]:
    """Compute box positions for a DAG.

    Returns a dict mapping node id to :class:`Box`.
    """
    if len(nodes) == 1:
        w, h = node_sizes[nodes[0].id]
        return {nodes[0].id: Box(x=padding, y=padding, w=w, h=h)}

    node_ids = [n.id for n in nodes]
    id_set = set(node_ids)

    # Build adjacency
    children: dict[str, list[str]] = {nid: [] for nid in node_ids}
    parents: dict[str, list[str]] = {nid: [] for nid in node_ids}
    for e in edges:
        if e.source in id_set and e.target in id_set and e.source != e.target:
            children[e.source].append(e.target)
            parents[e.target].append(e.source)

    # Find connected components (undirected)
    components = _find_components(node_ids, children, parents)

    all_boxes: dict[str, Box] = {}
    x_offset = 0

    for comp_ids in components:
        comp_children = {nid: children[nid] for nid in comp_ids}
        comp_parents = {nid: parents[nid] for nid in comp_ids}

        # Break cycles
        _break_cycles(comp_ids, comp_children, comp_parents)

        # Layer assignment
        layers = _assign_layers(comp_ids, comp_children, comp_parents)

        # Crossing minimisation (barycenter, 3 passes)
        layers = _minimise_crossings(layers, comp_children, comp_parents)

        # Coordinate assignment
        boxes = _assign_coordinates(
            layers, node_sizes, comp_children, comp_parents, xspace=4, yspace=2
        )

        # Shift component to x_offset
        if x_offset > 0:
            min_x = min(b.x for b in boxes.values())
            shift = x_offset - min_x + 4
            for nid in boxes:
                b = boxes[nid]
                boxes[nid] = Box(x=b.x + shift, y=b.y, w=b.w, h=b.h)

        max_x = max(b.x + b.w for b in boxes.values())
        x_offset = max_x
        all_boxes.update(boxes)

    # Normalise to padding
    min_x = min(b.x for b in all_boxes.values())
    min_y = min(b.y for b in all_boxes.values())
    dx = padding - min_x
    dy = padding - min_y

    return {
        nid: Box(x=b.x + dx, y=b.y + dy, w=b.w, h=b.h) for nid, b in all_boxes.items()
    }


# ---------------------------------------------------------------------------
# Component detection
# ---------------------------------------------------------------------------


def _find_components(
    node_ids: list[str],
    children: dict[str, list[str]],
    parents: dict[str, list[str]],
) -> list[list[str]]:
    """Partition nodes into connected components (undirected)."""
    visited: set[str] = set()
    components: list[list[str]] = []
    for nid in node_ids:
        if nid in visited:
            continue
        comp: list[str] = []
        queue = deque([nid])
        visited.add(nid)
        while queue:
            cur = queue.popleft()
            comp.append(cur)
            for nb in children[cur]:
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
            for nb in parents[cur]:
                if nb not in visited:
                    visited.add(nb)
                    queue.append(nb)
        components.append(comp)
    return components


# ---------------------------------------------------------------------------
# Cycle breaking
# ---------------------------------------------------------------------------


def _break_cycles(
    node_ids: list[str],
    children: dict[str, list[str]],
    parents: dict[str, list[str]],
) -> list[tuple[str, str]]:
    """Detect back edges via DFS and temporarily reverse them.

    Returns list of (original_src, original_tgt) pairs that were reversed.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in node_ids}
    reversed_edges: list[tuple[str, str]] = []

    def dfs(u: str) -> None:
        color[u] = GRAY
        for v in list(children[u]):
            if color[v] == GRAY:
                # Back edge — reverse it
                children[u].remove(v)
                parents[v].remove(u)
                children[v].append(u)
                parents[u].append(v)
                reversed_edges.append((u, v))
            elif color[v] == WHITE:
                dfs(v)
        color[u] = BLACK

    for nid in node_ids:
        if color[nid] == WHITE:
            dfs(nid)

    return reversed_edges


# ---------------------------------------------------------------------------
# Layer assignment (longest-path from sources)
# ---------------------------------------------------------------------------


def _assign_layers(
    node_ids: list[str],
    children: dict[str, list[str]],
    parents: dict[str, list[str]],
) -> list[list[str]]:
    """Assign each node to a layer using Kahn's topological sort + longest-path."""
    in_degree = {nid: len(parents[nid]) for nid in node_ids}
    layer_of: dict[str, int] = {}
    topo_order: list[str] = []

    queue: deque[str] = deque()
    for nid in node_ids:
        if in_degree[nid] == 0:
            queue.append(nid)
            layer_of[nid] = 0

    while queue:
        u = queue.popleft()
        topo_order.append(u)
        for v in children[u]:
            layer_of[v] = max(layer_of.get(v, 0), layer_of[u] + 1)
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)

    # Handle any remaining nodes (shouldn't happen after cycle breaking)
    for nid in node_ids:
        if nid not in layer_of:
            layer_of[nid] = 0
            topo_order.append(nid)

    # Group by layer — use topological order for natural left-to-right placement
    max_layer = max(layer_of.values(), default=0)
    layers: list[list[str]] = [[] for _ in range(max_layer + 1)]
    for nid in topo_order:
        layers[layer_of[nid]].append(nid)

    return layers


# ---------------------------------------------------------------------------
# Crossing minimisation (barycenter heuristic)
# ---------------------------------------------------------------------------


def _minimise_crossings(
    layers: list[list[str]],
    children: dict[str, list[str]],
    parents: dict[str, list[str]],
) -> list[list[str]]:
    """3-pass barycenter heuristic: down, up, down."""
    if len(layers) <= 1:
        return layers

    def pos_map(layer: list[str]) -> dict[str, int]:
        return {nid: i for i, nid in enumerate(layer)}

    # Down pass
    for i in range(1, len(layers)):
        pmap = pos_map(layers[i - 1])
        bary: dict[str, float] = {}
        for nid in layers[i]:
            ps = [pmap[p] for p in parents[nid] if p in pmap]
            bary[nid] = sum(ps) / len(ps) if ps else 0.0
        layers[i].sort(key=lambda n: bary[n])

    # Up pass
    for i in range(len(layers) - 2, -1, -1):
        cmap = pos_map(layers[i + 1])
        bary = {}
        for nid in layers[i]:
            cs = [cmap[c] for c in children[nid] if c in cmap]
            bary[nid] = sum(cs) / len(cs) if cs else 0.0
        layers[i].sort(key=lambda n: bary[n])

    # Down pass again
    for i in range(1, len(layers)):
        pmap = pos_map(layers[i - 1])
        bary = {}
        for nid in layers[i]:
            ps = [pmap[p] for p in parents[nid] if p in pmap]
            bary[nid] = sum(ps) / len(ps) if ps else 0.0
        layers[i].sort(key=lambda n: bary[n])

    return layers


# ---------------------------------------------------------------------------
# Coordinate assignment
# ---------------------------------------------------------------------------


def _assign_coordinates(
    layers: list[list[str]],
    node_sizes: dict[str, tuple[int, int]],
    children: dict[str, list[str]],
    parents: dict[str, list[str]],
    xspace: int,
    yspace: int,
) -> dict[str, Box]:
    """Assign (x, y) coordinates to nodes.

    Uses size-aware left-to-right placement, then centres nodes under their
    parents with overlap prevention.
    """
    # Build layer membership sets for fast parent/child filtering
    layer_set: list[set[str]] = [set(layer) for layer in layers]

    # Phase 1: initial left-to-right placement per layer
    layer_x: list[dict[str, int]] = []
    layer_centers: list[dict[str, float]] = []

    for layer in layers:
        x_pos: dict[str, int] = {}
        centers: dict[str, float] = {}
        cx = 0
        for nid in layer:
            w = node_sizes[nid][0]
            x_pos[nid] = cx
            centers[nid] = cx + w / 2.0
            cx += w + xspace
        layer_x.append(x_pos)
        layer_centers.append(centers)

    # Phase 2: centre under parents (top-down) with overlap prevention
    for li in range(1, len(layers)):
        prev_set = layer_set[li - 1]
        prev_centers = layer_centers[li - 1]
        layer = layers[li]
        desired: dict[str, float] = {}
        for nid in layer:
            parent_cx = [prev_centers[p] for p in parents[nid] if p in prev_set]
            if parent_cx:
                desired[nid] = sum(parent_cx) / len(parent_cx)
            else:
                desired[nid] = layer_centers[li][nid]

        # Sort by desired position, then place preventing overlap
        order = sorted(layer, key=lambda n: desired[n])
        layers[li] = order
        layer_set[li] = set(order)
        cx = 0
        new_x: dict[str, int] = {}
        new_centers: dict[str, float] = {}
        for nid in order:
            w = node_sizes[nid][0]
            ideal_x = int(desired[nid] - w / 2.0)
            x = max(ideal_x, cx)
            new_x[nid] = x
            new_centers[nid] = x + w / 2.0
            cx = x + w + xspace

        # Centre the group around the average desired position.
        # Overlap prevention left-packs siblings that share a parent,
        # so shift the whole block to balance the layout.
        if len(order) > 1:
            avg_desired = sum(desired[n] for n in order) / len(order)
            first = order[0]
            last = order[-1]
            actual_center = (new_x[first] + new_x[last] + node_sizes[last][0]) / 2.0
            shift = int(avg_desired - actual_center)
            min_x_val = min(new_x.values())
            if shift < 0:
                shift = max(shift, -min_x_val)  # don't go below 0
            if shift != 0:
                for nid in order:
                    new_x[nid] += shift
                    new_centers[nid] += shift

        layer_x[li] = new_x
        layer_centers[li] = new_centers

    # Phase 3: bottom-up centering — only single-node layers.
    # Multi-node layers keep their Phase 2 positions to avoid clustering
    # when sibling nodes share a single fan-in child (e.g. 3 nodes → __end__).
    for _pass in range(2):
        for li in range(len(layers) - 2, -1, -1):
            if len(layers[li]) != 1:
                continue
            nid = layers[li][0]
            next_set = layer_set[li + 1]
            child_cx = [
                layer_centers[li + 1][c] for c in children[nid] if c in next_set
            ]
            if not child_cx:
                continue
            desired_center = sum(child_cx) / len(child_cx)
            w = node_sizes[nid][0]
            x = max(int(desired_center - w / 2.0), 0)
            layer_x[li] = {nid: x}
            layer_centers[li] = {nid: x + w / 2.0}

    # Phase 4: top-down centering — only single-node layers.
    # Propagates shifts from Phase 3 back down (e.g. centres __end__
    # under its parents after they were repositioned).
    for li in range(1, len(layers)):
        if len(layers[li]) != 1:
            continue
        nid = layers[li][0]
        prev_set = layer_set[li - 1]
        parent_cx = [layer_centers[li - 1][p] for p in parents[nid] if p in prev_set]
        if not parent_cx:
            continue
        desired_center = sum(parent_cx) / len(parent_cx)
        w = node_sizes[nid][0]
        x = max(int(desired_center - w / 2.0), 0)
        layer_x[li] = {nid: x}
        layer_centers[li] = {nid: x + w / 2.0}

    # Y-coordinate assignment: cumulative layer heights
    boxes: dict[str, Box] = {}
    y = 0
    for li, layer in enumerate(layers):
        max_h = 0
        for nid in layer:
            w, h = node_sizes[nid]
            boxes[nid] = Box(x=layer_x[li][nid], y=y, w=w, h=h)
            max_h = max(max_h, h)
        y += max_h + yspace

    return boxes
