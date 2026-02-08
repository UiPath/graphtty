# LangGraph + graphtty

Render any [LangGraph](https://github.com/langchain-ai/langgraph) graph as Unicode/ASCII art using [graphtty](https://github.com/uipath/graphtty).

## Quick start

```bash
pip install langgraph graphtty
python example.py
```

## Options

```bash
python example.py --theme monokai   # apply a color theme
python example.py --ascii           # ASCII-only characters
```

## How it works

LangGraph exposes the graph structure via `compiled_graph.get_graph()`, which returns a `Graph` object with `.nodes` and `.edges`. The example converts these into graphtty's `AsciiGraph` format and renders it:

```python
from graphtty import AsciiEdge, AsciiGraph, AsciiNode, render


def langgraph_to_graphtty(compiled_graph) -> AsciiGraph:
    lg = compiled_graph.get_graph()

    nodes = [
        AsciiNode(id=str(nid), name=node.name)
        for nid, node in lg.nodes.items()
    ]
    edges = [
        AsciiEdge(
            source=str(e.source),
            target=str(e.target),
            label=str(e.data) if e.data else None,
        )
        for e in lg.edges
    ]

    return AsciiGraph(nodes=nodes, edges=edges)


ascii_graph = langgraph_to_graphtty(compiled_graph)
print(render(ascii_graph, theme="monokai"))
```
