"""Graph truncation — prune large graphs by depth and breadth."""

from __future__ import annotations

from collections import deque

from .types import AsciiEdge, AsciiGraph, AsciiNode

_DEPTH_PLACEHOLDER_ID = "__truncated_depth__"


def truncate_graph(
    graph: AsciiGraph,
    *,
    max_depth: int | None = None,
    max_breadth: int | None = None,
) -> AsciiGraph:
    """Return a truncated copy of *graph*.

    * **max_depth** — keep only nodes within this many layers from the roots
      (in-degree-0 nodes).  Nodes beyond the limit are replaced by a single
      ``...`` placeholder node.
    * **max_breadth** — keep at most this many nodes per layer.  Excess nodes
      in a layer are collapsed into a per-layer ``...`` placeholder.

    Returns a new :class:`AsciiGraph`; the original is not modified.
    """
    if max_depth is None and max_breadth is None:
        return graph

    node_ids = {n.id for n in graph.nodes}

    # Build forward adjacency & in-degree
    forward: dict[str, list[str]] = {nid: [] for nid in node_ids}
    in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
    for e in graph.edges:
        if e.source in node_ids and e.target in node_ids and e.source != e.target:
            forward[e.source].append(e.target)
            in_degree[e.target] += 1

    # Longest-path layer assignment via topological order (Kahn's algorithm).
    # Processing in topo order guarantees all incoming edges are resolved
    # before a node is expanded — correct for longest-path in a DAG.
    roots = [nid for nid in node_ids if in_degree[nid] == 0]
    if not roots:
        # Pure cycle — treat all nodes as layer 0
        layers: dict[str, int] = {nid: 0 for nid in node_ids}
    else:
        layers = {nid: 0 for nid in node_ids}
        remaining = dict(in_degree)
        topo: deque[str] = deque(roots)
        while topo:
            nid = topo.popleft()
            for child in forward[nid]:
                new_layer = layers[nid] + 1
                if new_layer > layers[child]:
                    layers[child] = new_layer
                remaining[child] -= 1
                if remaining[child] == 0:
                    topo.append(child)

    # --- Depth truncation ---
    keep_ids: set[str] = set()
    depth_trunc_parents: set[str] = set()  # kept nodes with children beyond limit

    if max_depth is not None:
        for nid, layer in layers.items():
            if layer <= max_depth:
                keep_ids.add(nid)
        # Find kept nodes that have children beyond the depth limit
        for nid in list(keep_ids):
            for child in forward[nid]:
                if child not in keep_ids:
                    depth_trunc_parents.add(nid)
    else:
        keep_ids = set(node_ids)

    # --- Breadth truncation ---
    breadth_replacements: dict[str, str] = {}  # removed_id -> placeholder_id

    if max_breadth is not None and max_breadth >= 1:
        # Group nodes by layer (preserving original graph order)
        max_layer = max(layers.values()) if layers else 0
        nodes_by_layer: list[list[str]] = [[] for _ in range(max_layer + 1)]
        for n in graph.nodes:
            nodes_by_layer[layers[n.id]].append(n.id)

        for layer_idx, layer_nodes in enumerate(nodes_by_layer):
            # Only consider nodes that survived depth truncation
            surviving = [nid for nid in layer_nodes if nid in keep_ids]
            if len(surviving) <= max_breadth:
                continue
            # Keep first (max_breadth - 1) nodes, replace rest with placeholder
            removed = surviving[max_breadth - 1 :]
            placeholder_id = f"__truncated_breadth_{layer_idx}__"
            for rid in removed:
                keep_ids.discard(rid)
                breadth_replacements[rid] = placeholder_id
                # If this node was a depth-truncation parent, remove it
                depth_trunc_parents.discard(rid)

    # --- Build result nodes ---
    result_nodes: list[AsciiNode] = []
    added_placeholders: set[str] = set()

    for n in graph.nodes:
        if n.id in keep_ids:
            # Recurse into subgraphs
            if n.subgraph and n.subgraph.nodes:
                sub = truncate_graph(
                    n.subgraph, max_depth=max_depth, max_breadth=max_breadth
                )
                result_nodes.append(
                    AsciiNode(
                        id=n.id,
                        name=n.name,
                        type=n.type,
                        description=n.description,
                        subgraph=sub,
                    )
                )
            else:
                result_nodes.append(n)
        elif n.id in breadth_replacements:
            pid = breadth_replacements[n.id]
            if pid not in added_placeholders:
                added_placeholders.add(pid)
                result_nodes.append(AsciiNode(id=pid, name="...", type="__truncated__"))

    if depth_trunc_parents:
        result_nodes.append(
            AsciiNode(id=_DEPTH_PLACEHOLDER_ID, name="...", type="__truncated__")
        )

    # --- Build result edges ---
    result_node_ids = {n.id for n in result_nodes}
    seen_edges: set[tuple[str, str]] = set()
    result_edges: list[AsciiEdge] = []

    for e in graph.edges:
        src = e.source
        tgt = e.target

        # Remap breadth-truncated nodes
        if src in breadth_replacements:
            src = breadth_replacements[src]
        if tgt in breadth_replacements:
            tgt = breadth_replacements[tgt]

        # Depth-truncated target: redirect to depth placeholder
        if src in result_node_ids and tgt not in result_node_ids:
            if src in depth_trunc_parents:
                tgt = _DEPTH_PLACEHOLDER_ID

        if src not in result_node_ids or tgt not in result_node_ids:
            continue
        if src == tgt:
            continue

        pair = (src, tgt)
        if pair in seen_edges:
            continue
        seen_edges.add(pair)

        # Preserve label only if both endpoints are original (not placeholders)
        label = e.label if src == e.source and tgt == e.target else None
        result_edges.append(AsciiEdge(source=src, target=tgt, label=label))

    return AsciiGraph(nodes=result_nodes, edges=result_edges)
