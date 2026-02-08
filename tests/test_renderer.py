"""Tests for the rendering engine."""

from graphtty import RenderOptions, render
from graphtty.types import AsciiEdge, AsciiGraph, AsciiNode


def _node(id: str, name: str, type: str = "action", **kwargs) -> AsciiNode:
    return AsciiNode(id=id, name=name, type=type, **kwargs)


def _edge(src: str, tgt: str, label: str | None = None) -> AsciiEdge:
    return AsciiEdge(source=src, target=tgt, label=label)


class TestRenderEmpty:
    def test_empty_graph(self):
        g = AsciiGraph(nodes=[], edges=[])
        assert render(g) == ""

    def test_no_nodes(self):
        g = AsciiGraph()
        assert render(g) == ""


class TestRenderDict:
    def test_render_from_dict(self):
        result = render(
            {
                "nodes": [{"id": "a", "name": "Hello", "type": "tool"}],
                "edges": [],
            }
        )
        assert "Hello" in result

    def test_render_dict_with_edges(self):
        result = render(
            {
                "nodes": [
                    {"id": "a", "name": "A", "type": "x"},
                    {"id": "b", "name": "B", "type": "y"},
                ],
                "edges": [{"source": "a", "target": "b"}],
            }
        )
        assert "A" in result
        assert "B" in result


class TestRenderSingleNode:
    def test_single_node_unicode(self):
        g = AsciiGraph(nodes=[_node("a", "Hello", "tool")])
        result = render(g)
        assert "Hello" in result
        assert "\u250c" in result
        assert "tool" in result

    def test_single_node_ascii(self):
        g = AsciiGraph(nodes=[_node("a", "Hello", "tool")])
        result = render(g, RenderOptions(use_unicode=False))
        assert "Hello" in result
        assert "+" in result
        assert "-" in result

    def test_single_node_no_types(self):
        g = AsciiGraph(nodes=[_node("a", "Hello", "tool")])
        result = render(g, RenderOptions(show_types=False))
        assert "Hello" in result
        assert "[tool]" not in result
        assert "tool" not in result


class TestRenderLinearChain:
    def test_two_nodes(self):
        g = AsciiGraph(
            nodes=[_node("a", "Start", "entry"), _node("b", "End", "exit")],
            edges=[_edge("a", "b")],
        )
        result = render(g)
        assert "Start" in result
        assert "End" in result
        assert "\u25bc" in result  # arrow

    def test_three_nodes(self):
        g = AsciiGraph(
            nodes=[
                _node("a", "Start", "entry"),
                _node("b", "Process", "tool"),
                _node("c", "End", "exit"),
            ],
            edges=[_edge("a", "b"), _edge("b", "c")],
        )
        result = render(g)
        assert "Start" in result
        assert "Process" in result
        assert "End" in result

    def test_arrow_not_on_border(self):
        """Arrow should not overwrite the type label in box border."""
        g = AsciiGraph(
            nodes=[_node("a", "Start", "entry"), _node("b", "End", "exit")],
            edges=[_edge("a", "b")],
        )
        result = render(g)
        lines = result.split("\n")
        # Find the line with the target box top border
        for line in lines:
            if "exit" in line and "\u250c" in line:
                # The type label should not contain the arrow character
                assert "\u25bc" not in line


class TestRenderEdgeLabels:
    def test_edge_with_label(self):
        g = AsciiGraph(
            nodes=[_node("a", "Check", "condition"), _node("b", "Do", "action")],
            edges=[_edge("a", "b", label="yes")],
        )
        result = render(g)
        assert "yes" in result

    def test_multiple_labels(self):
        g = AsciiGraph(
            nodes=[
                _node("a", "Check", "condition"),
                _node("b", "Left", "action"),
                _node("c", "Right", "action"),
            ],
            edges=[
                _edge("a", "b", label="true"),
                _edge("a", "c", label="false"),
            ],
        )
        result = render(g)
        assert "true" in result
        assert "false" in result


class TestRenderBranching:
    def test_diamond_shape(self):
        """Two branches from one node, merging back."""
        g = AsciiGraph(
            nodes=[
                _node("a", "Start", "entry"),
                _node("b", "Check", "condition"),
                _node("c", "Left", "action"),
                _node("d", "Right", "action"),
                _node("e", "End", "exit"),
            ],
            edges=[
                _edge("a", "b"),
                _edge("b", "c"),
                _edge("b", "d"),
                _edge("c", "e"),
                _edge("d", "e"),
            ],
        )
        result = render(g)
        assert "Start" in result
        assert "Check" in result
        assert "Left" in result
        assert "Right" in result
        assert "End" in result


class TestRenderSubgraphs:
    def test_subgraph_node(self):
        sub = AsciiGraph(
            nodes=[_node("s1", "Inner A", "step"), _node("s2", "Inner B", "step")],
            edges=[_edge("s1", "s2")],
        )
        g = AsciiGraph(
            nodes=[
                _node("a", "Start", "entry"),
                _node("b", "Pipeline", "subgraph", subgraph=sub),
                _node("c", "End", "exit"),
            ],
            edges=[_edge("a", "b"), _edge("b", "c")],
        )
        result = render(g)
        assert "Start" in result
        assert "Pipeline" in result
        assert "Inner A" in result
        assert "Inner B" in result
        assert "End" in result

    def test_empty_subgraph_ignored(self):
        """A node with an empty subgraph is rendered as a regular node."""
        empty_sub = AsciiGraph(nodes=[], edges=[])
        g = AsciiGraph(
            nodes=[_node("a", "Box", "container", subgraph=empty_sub)],
        )
        result = render(g)
        assert "Box" in result

    def test_none_subgraph(self):
        g = AsciiGraph(
            nodes=[_node("a", "Box", "tool", subgraph=None)],
        )
        result = render(g)
        assert "Box" in result


class TestRenderOptions:
    def test_default_options(self):
        g = AsciiGraph(nodes=[_node("a", "Test", "tool")])
        result = render(g)
        assert "tool" in result  # show_types default True (in border)
        assert "\u250c" in result  # use_unicode default True

    def test_unicode_off(self):
        g = AsciiGraph(nodes=[_node("a", "Test", "tool")])
        result = render(g, RenderOptions(use_unicode=False))
        assert "\u250c" not in result
        assert "+" in result

    def test_types_off(self):
        g = AsciiGraph(nodes=[_node("a", "Test", "tool")])
        result = render(g, RenderOptions(show_types=False))
        assert "[tool]" not in result

    def test_custom_padding(self):
        g = AsciiGraph(nodes=[_node("a", "Test", "tool")])
        result_small = render(g, RenderOptions(padding=0))
        result_large = render(g, RenderOptions(padding=5))
        # Larger padding should produce more leading whitespace
        lines_small = [line for line in result_small.split("\n") if line.strip()]
        lines_large = [line for line in result_large.split("\n") if line.strip()]
        lead_small = len(lines_small[0]) - len(lines_small[0].lstrip())
        lead_large = len(lines_large[0]) - len(lines_large[0].lstrip())
        assert lead_large >= lead_small


class TestRenderAsciiMode:
    def test_full_graph_ascii(self):
        g = AsciiGraph(
            nodes=[
                _node("a", "Start", "entry"),
                _node("b", "Process", "tool"),
                _node("c", "End", "exit"),
            ],
            edges=[_edge("a", "b"), _edge("b", "c")],
        )
        result = render(g, RenderOptions(use_unicode=False))
        assert "+" in result
        assert "|" in result
        assert "-" in result
        assert "v" in result  # ASCII arrow
        # No unicode characters
        assert "\u250c" not in result
        assert "\u2502" not in result
        assert "\u25bc" not in result


class TestRenderEdgeCases:
    def test_long_node_names(self):
        g = AsciiGraph(
            nodes=[_node("a", "This is a very long node name", "tool")],
        )
        result = render(g)
        assert "This is a very long node name" in result

    def test_edge_to_nonexistent_node(self):
        """Edges referencing missing nodes should be silently skipped."""
        g = AsciiGraph(
            nodes=[_node("a", "Start", "entry")],
            edges=[_edge("a", "missing")],
        )
        result = render(g)
        assert "Start" in result  # should not crash

    def test_disconnected_nodes(self):
        """Nodes with no edges should still be rendered."""
        g = AsciiGraph(
            nodes=[
                _node("a", "Node A", "tool"),
                _node("b", "Node B", "tool"),
            ],
        )
        result = render(g)
        assert "Node A" in result
        assert "Node B" in result

    def test_self_loop_edge(self):
        """Self-loop edges should not crash."""
        g = AsciiGraph(
            nodes=[_node("a", "Loop", "tool")],
            edges=[_edge("a", "a")],
        )
        result = render(g)
        assert "Loop" in result

    def test_node_with_description(self):
        """Description should be rendered as metadata lines."""
        g = AsciiGraph(
            nodes=[_node("a", "Agent", "model", description="gpt-4")],
        )
        result = render(g)
        assert "Agent" in result
        assert "gpt-4" in result


class TestRenderComplexGraphs:
    def test_agentic_workflow(self):
        """Simulate a realistic agentic workflow graph."""
        g = AsciiGraph(
            nodes=[
                _node("start", "User Input", type="entry"),
                _node("router", "Router Agent", type="model"),
                _node("tool1", "Web Search", type="tool"),
                _node("tool2", "Calculator", type="tool"),
                _node("llm", "LLM Response", type="model"),
                _node("end", "Output", type="exit"),
            ],
            edges=[
                _edge("start", "router"),
                _edge("router", "tool1", label="search"),
                _edge("router", "tool2", label="calc"),
                _edge("tool1", "llm"),
                _edge("tool2", "llm"),
                _edge("llm", "end"),
            ],
        )
        result = render(g)
        assert "User Input" in result
        assert "Router Agent" in result
        assert "Web Search" in result
        assert "Calculator" in result
        assert "LLM Response" in result
        assert "Output" in result

    def test_nested_subgraphs(self):
        """Two levels of nesting."""
        inner = AsciiGraph(
            nodes=[_node("i1", "Deep", "step")],
        )
        middle = AsciiGraph(
            nodes=[_node("m1", "Mid", "group", subgraph=inner)],
        )
        g = AsciiGraph(
            nodes=[_node("top", "Top", "root", subgraph=middle)],
        )
        result = render(g)
        assert "Top" in result
        assert "Mid" in result
        assert "Deep" in result
