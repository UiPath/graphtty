"""Example: Render a LangGraph graph with graphtty.

Uses LangGraph's native `get_graph()` method to extract the graph schema,
converts it to graphtty format, and renders it as ASCII/Unicode art.

Install dependencies:
    pip install langgraph graphtty

Usage:
    python example.py
    python example.py --theme monokai
    python example.py --ascii
"""

from __future__ import annotations

import argparse

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from graphtty import AsciiEdge, AsciiGraph, AsciiNode, RenderOptions, get_theme, render

# ---------------------------------------------------------------------------
# 1. Define a sample LangGraph graph (ReAct-style agent)
# ---------------------------------------------------------------------------


class AgentState(TypedDict):
    messages: list[str]


def call_model(state: AgentState) -> AgentState:
    return {"messages": state["messages"] + ["model response"]}


def use_tools(state: AgentState) -> AgentState:
    return {"messages": state["messages"] + ["tool result"]}


def should_continue(state: AgentState) -> str:
    """Route to tools or end."""
    last = state["messages"][-1] if state["messages"] else ""
    return "tools" if "tool_call" in last else "end"


builder = StateGraph(AgentState)
builder.add_node("model", call_model)
builder.add_node("tools", use_tools)

builder.add_edge(START, "model")
builder.add_conditional_edges("model", should_continue, {"tools": "tools", "end": END})
builder.add_edge("tools", "model")

graph = builder.compile()


# ---------------------------------------------------------------------------
# 2. Convert LangGraph graph schema → graphtty format
# ---------------------------------------------------------------------------


def langgraph_to_graphtty(compiled_graph) -> AsciiGraph:
    """Convert a compiled LangGraph graph into a graphtty AsciiGraph."""
    lg = compiled_graph.get_graph()

    nodes = []
    for node_id, node in lg.nodes.items():
        nodes.append(
            AsciiNode(
                id=str(node_id),
                name=node.name,
            )
        )

    edges = []
    for edge in lg.edges:
        label = str(edge.data) if edge.data else None
        edges.append(
            AsciiEdge(
                source=str(edge.source),
                target=str(edge.target),
                label=label,
            )
        )

    return AsciiGraph(nodes=nodes, edges=edges)


# ---------------------------------------------------------------------------
# 3. Render
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Render a LangGraph graph with graphtty"
    )
    parser.add_argument(
        "--theme", default="monokai", help="Theme name (default: monokai)"
    )
    parser.add_argument(
        "--ascii", action="store_true", help="Use ASCII-only characters"
    )
    args = parser.parse_args()

    ascii_graph = langgraph_to_graphtty(graph)
    options = RenderOptions(
        theme=get_theme(args.theme),
        use_unicode=not args.ascii,
    )
    output = render(ascii_graph, options)
    print(output)
