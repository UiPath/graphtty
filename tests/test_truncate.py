"""Tests for graph truncation (depth/breadth pruning)."""

from graphtty import AsciiEdge, AsciiGraph, AsciiNode, RenderOptions, render
from graphtty.truncate import truncate_graph


def _ids(graph: AsciiGraph) -> set[str]:
    return {n.id for n in graph.nodes}


def _edge_pairs(graph: AsciiGraph) -> set[tuple[str, str]]:
    return {(e.source, e.target) for e in graph.edges}


# ---------------------------------------------------------------------------
# Depth truncation
# ---------------------------------------------------------------------------


class TestDepthTruncation:
    def test_chain_depth_1(self):
        """A→B→C→D with max_depth=1 keeps A, B and adds '...' placeholder."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
                AsciiNode(id="C", name="C"),
                AsciiNode(id="D", name="D"),
            ],
            edges=[
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="B", target="C"),
                AsciiEdge(source="C", target="D"),
            ],
        )
        result = truncate_graph(g, max_depth=1)
        ids = _ids(result)
        assert "A" in ids
        assert "B" in ids
        assert "C" not in ids
        assert "D" not in ids
        assert "__truncated_depth__" in ids
        # B should connect to the placeholder
        assert ("B", "__truncated_depth__") in _edge_pairs(result)

    def test_longest_path_reconverging(self):
        """Longest-path must follow the longest route through re-converging paths.

        A→D→E (short) and A→B→C→D→E (long).  D should be at layer 3, E at 4.
        With max_depth=2 only A, B, C are kept (layers 0, 1, 2).
        """
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
                AsciiNode(id="C", name="C"),
                AsciiNode(id="D", name="D"),
                AsciiNode(id="E", name="E"),
            ],
            edges=[
                AsciiEdge(source="A", target="D"),
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="B", target="C"),
                AsciiEdge(source="C", target="D"),
                AsciiEdge(source="D", target="E"),
            ],
        )
        result = truncate_graph(g, max_depth=2)
        ids = _ids(result)
        assert {"A", "B", "C"} <= ids
        # D is at layer 3 (longest path A→B→C→D), so it's truncated
        assert "D" not in ids
        assert "E" not in ids
        assert "__truncated_depth__" in ids

    def test_fan_out_depth_0(self):
        """max_depth=0 keeps only root(s) + placeholder."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="root", name="root"),
                AsciiNode(id="a", name="a"),
                AsciiNode(id="b", name="b"),
            ],
            edges=[
                AsciiEdge(source="root", target="a"),
                AsciiEdge(source="root", target="b"),
            ],
        )
        result = truncate_graph(g, max_depth=0)
        ids = _ids(result)
        assert ids == {"root", "__truncated_depth__"}
        assert ("root", "__truncated_depth__") in _edge_pairs(result)

    def test_cyclic_graph_no_truncation(self):
        """Cyclic graphs should be fully preserved when limits are large enough.

        Models the deep-agent pattern: start → A → B → C → A (cycle), C → end.
        """
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="start", name="start"),
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
                AsciiNode(id="C", name="C"),
                AsciiNode(id="end", name="end"),
            ],
            edges=[
                AsciiEdge(source="start", target="A"),
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="B", target="C"),
                AsciiEdge(source="C", target="A"),  # back-edge
                AsciiEdge(source="C", target="end"),
            ],
        )
        result = truncate_graph(g, max_depth=10, max_breadth=10)
        assert _ids(result) == {"start", "A", "B", "C", "end"}

    def test_depth_no_truncation_needed(self):
        """Graph fits within max_depth — no placeholder added."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
            ],
            edges=[AsciiEdge(source="A", target="B")],
        )
        result = truncate_graph(g, max_depth=5)
        assert _ids(result) == {"A", "B"}
        assert "__truncated_depth__" not in _ids(result)

    def test_diamond_depth(self):
        """Diamond: A→B, A→C, B→D, C→D — longest-path layers: A=0,B=1,C=1,D=2."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
                AsciiNode(id="C", name="C"),
                AsciiNode(id="D", name="D"),
            ],
            edges=[
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="A", target="C"),
                AsciiEdge(source="B", target="D"),
                AsciiEdge(source="C", target="D"),
            ],
        )
        result = truncate_graph(g, max_depth=1)
        ids = _ids(result)
        assert {"A", "B", "C"} <= ids
        assert "D" not in ids
        assert "__truncated_depth__" in ids


# ---------------------------------------------------------------------------
# Breadth truncation
# ---------------------------------------------------------------------------


class TestBreadthTruncation:
    def test_wide_layer(self):
        """5-node layer with max_breadth=3 → 2 nodes + placeholder."""
        nodes = [AsciiNode(id="root", name="root")]
        edges = []
        for i in range(5):
            nid = f"n{i}"
            nodes.append(AsciiNode(id=nid, name=nid))
            edges.append(AsciiEdge(source="root", target=nid))
        g = AsciiGraph(nodes=nodes, edges=edges)

        result = truncate_graph(g, max_breadth=3)
        ids = _ids(result)
        assert "root" in ids
        # Should have 2 original nodes + 1 placeholder = 3 at layer 1
        layer1_ids = ids - {"root"}
        assert len(layer1_ids) == 3
        assert any("__truncated_breadth_" in nid for nid in layer1_ids)

    def test_breadth_no_truncation_needed(self):
        """Layers within limit — no placeholder."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
                AsciiNode(id="C", name="C"),
            ],
            edges=[
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="A", target="C"),
            ],
        )
        result = truncate_graph(g, max_breadth=5)
        assert _ids(result) == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Combined
# ---------------------------------------------------------------------------


class TestCombinedTruncation:
    def test_depth_and_breadth(self):
        """Both limits applied together."""
        # root → a, b, c, d (layer 1, 4 nodes)
        # a → leaf (layer 2)
        nodes = [
            AsciiNode(id="root", name="root"),
            AsciiNode(id="a", name="a"),
            AsciiNode(id="b", name="b"),
            AsciiNode(id="c", name="c"),
            AsciiNode(id="d", name="d"),
            AsciiNode(id="leaf", name="leaf"),
        ]
        edges = [
            AsciiEdge(source="root", target="a"),
            AsciiEdge(source="root", target="b"),
            AsciiEdge(source="root", target="c"),
            AsciiEdge(source="root", target="d"),
            AsciiEdge(source="a", target="leaf"),
        ]
        g = AsciiGraph(nodes=nodes, edges=edges)

        result = truncate_graph(g, max_depth=1, max_breadth=3)
        ids = _ids(result)
        # root kept (layer 0)
        assert "root" in ids
        # layer 1 breadth-truncated to 2 nodes + placeholder
        # leaf removed by depth truncation
        assert "leaf" not in ids


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_noop_no_limits(self):
        """No limits → return original graph."""
        g = AsciiGraph(
            nodes=[AsciiNode(id="A", name="A")],
            edges=[],
        )
        result = truncate_graph(g, max_depth=None, max_breadth=None)
        assert result is g

    def test_single_node(self):
        """Single node graph with depth=0."""
        g = AsciiGraph(
            nodes=[AsciiNode(id="only", name="only")],
            edges=[],
        )
        result = truncate_graph(g, max_depth=0)
        assert _ids(result) == {"only"}

    def test_empty_graph(self):
        """Empty graph stays empty."""
        g = AsciiGraph(nodes=[], edges=[])
        result = truncate_graph(g, max_depth=1, max_breadth=2)
        assert len(result.nodes) == 0

    def test_edge_deduplication(self):
        """Multiple parents → same placeholder should produce one edge each."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="p1", name="p1"),
                AsciiNode(id="p2", name="p2"),
                AsciiNode(id="c1", name="c1"),
                AsciiNode(id="c2", name="c2"),
            ],
            edges=[
                AsciiEdge(source="p1", target="c1"),
                AsciiEdge(source="p1", target="c2"),
                AsciiEdge(source="p2", target="c1"),
                AsciiEdge(source="p2", target="c2"),
            ],
        )
        # p1, p2 are layer 0; c1, c2 are layer 1
        result = truncate_graph(g, max_depth=0)
        edges = _edge_pairs(result)
        # Each parent should have exactly one edge to the placeholder
        p1_edges = [(s, t) for s, t in edges if s == "p1"]
        p2_edges = [(s, t) for s, t in edges if s == "p2"]
        assert len(p1_edges) == 1
        assert len(p2_edges) == 1

    def test_self_loop_ignored(self):
        """Self-loops should not create placeholder edges to self."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
            ],
            edges=[
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="A", target="A"),  # self-loop
            ],
        )
        result = truncate_graph(g, max_depth=1)
        # Self-loop should not cause issues
        assert "A" in _ids(result)

    def test_placeholder_node_name_is_ellipsis(self):
        """Placeholder nodes have name='...'."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
                AsciiNode(id="C", name="C"),
            ],
            edges=[
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="B", target="C"),
            ],
        )
        result = truncate_graph(g, max_depth=1)
        placeholders = [n for n in result.nodes if n.type == "__truncated__"]
        assert len(placeholders) == 1
        assert placeholders[0].name == "..."


# ---------------------------------------------------------------------------
# Subgraph recursion
# ---------------------------------------------------------------------------


class TestSubgraphRecursion:
    def test_subgraph_truncated(self):
        """Truncation should recurse into subgraphs."""
        inner = AsciiGraph(
            nodes=[
                AsciiNode(id="s1", name="s1"),
                AsciiNode(id="s2", name="s2"),
                AsciiNode(id="s3", name="s3"),
            ],
            edges=[
                AsciiEdge(source="s1", target="s2"),
                AsciiEdge(source="s2", target="s3"),
            ],
        )
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="outer", name="outer", subgraph=inner),
            ],
            edges=[],
        )
        result = truncate_graph(g, max_depth=1)
        sub = result.nodes[0].subgraph
        assert sub is not None
        sub_ids = _ids(sub)
        assert "s1" in sub_ids
        assert "s2" in sub_ids
        assert "s3" not in sub_ids


# ---------------------------------------------------------------------------
# Render integration
# ---------------------------------------------------------------------------


class TestRenderIntegration:
    def test_render_with_depth(self):
        """render() with max_depth produces output containing '...'."""
        g = AsciiGraph(
            nodes=[
                AsciiNode(id="A", name="A"),
                AsciiNode(id="B", name="B"),
                AsciiNode(id="C", name="C"),
            ],
            edges=[
                AsciiEdge(source="A", target="B"),
                AsciiEdge(source="B", target="C"),
            ],
        )
        opts = RenderOptions(max_depth=1)
        out = render(g, opts)
        assert "..." in out
        assert "A" in out
        assert "B" in out
        # C should be replaced by "..."
        assert "C" not in out

    def test_render_with_breadth(self):
        """render() with max_breadth produces output containing '...'."""
        nodes = [AsciiNode(id="root", name="root")]
        edges = []
        for i in range(5):
            nid = f"child{i}"
            nodes.append(AsciiNode(id=nid, name=nid))
            edges.append(AsciiEdge(source="root", target=nid))
        g = AsciiGraph(nodes=nodes, edges=edges)

        opts = RenderOptions(max_breadth=3)
        out = render(g, opts)
        assert "..." in out
        assert "root" in out
