# graphtty

[![PyPI downloads](https://img.shields.io/pypi/dm/graphtty.svg)](https://pypi.org/project/graphtty/)
[![PyPI - Version](https://img.shields.io/pypi/v/graphtty)](https://img.shields.io/pypi/v/graphtty)
[![Python versions](https://img.shields.io/pypi/pyversions/graphtty.svg)](https://pypi.org/project/graphtty/)

Turn any directed graph into colored ASCII art for your terminal. Pure Python, zero external dependencies.

## Installation

```bash
pip install graphtty
```

### Deep Agent (ocean theme)

<img src="https://raw.githubusercontent.com/uipath/graphtty/main/screenshots/deep-agent.png" width="700">

### Supervisor Agent (dracula theme)

<img src="https://raw.githubusercontent.com/uipath/graphtty/main/screenshots/supervisor-agent.png" width="700">

> More examples available in the [`screenshots/`](https://github.com/UiPath/graphtty/tree/main/screenshots) directory.

## Quick start

```python
from graphtty import render

graph = {
    "nodes": [
        {"id": "start", "name": "User Input", "type": "entry"},
        {"id": "router", "name": "Router", "type": "condition"},
        {"id": "search", "name": "Web Search", "type": "tool"},
        {"id": "calc", "name": "Calculator", "type": "tool"},
        {"id": "respond", "name": "Respond", "type": "model"},
    ],
    "edges": [
        {"source": "start", "target": "router"},
        {"source": "router", "target": "search", "label": "search"},
        {"source": "router", "target": "calc", "label": "calc"},
        {"source": "search", "target": "respond"},
        {"source": "calc", "target": "respond"},
    ],
}

print(render(graph))
```

```
           ┌ entry ─────┐
           │ User Input │
           └─────┬──────┘
                 │
                 ▼
          ┌ condition ──┐
          │   Router    │
          └──────┬──────┘
         ┌search─└──calc───┐
         ▼                 ▼
  ┌ tool ──────┐    ┌ tool ──────┐
  │ Web Search │    │ Calculator │
  └──────┬─────┘    └──────┬─────┘
         └───────┌─────────┘
                 ▼
            ┌ model ──┐
            │ Respond │
            └─────────┘
```

Nodes support descriptions and nested subgraphs:

```python
# Descriptions appear as extra lines inside the box
{"id": "a", "name": "LLM", "type": "model", "description": "gpt-4o"}

# Nested subgraphs render as boxes within boxes
{"id": "b", "name": "Pipeline", "type": "subgraph", "subgraph": {"nodes": [...], "edges": [...]}}
```

Apply a color theme:

```python
from graphtty import render, RenderOptions, get_theme

print(render(graph, RenderOptions(theme=get_theme("monokai"))))
```

## CLI

```bash
graphtty graph.json
graphtty graph.json --theme monokai
graphtty graph.json --ascii
graphtty graph.json --no-types
```

### Themes

Ten built-in color themes:

`default` `monokai` `ocean` `forest` `dracula` `solarized` `nord` `catppuccin` `gruvbox` `tokyo-night`

```bash
graphtty --list-themes
```

## JSON format

graphtty reads a simple JSON format:

```json
{
  "nodes": [
    { "id": "a", "name": "Start", "type": "entry" },
    { "id": "b", "name": "Process", "type": "tool", "description": "optional detail" },
    { "id": "c", "name": "End", "type": "exit" }
  ],
  "edges": [
    { "source": "a", "target": "b", "label": "optional" },
    { "source": "b", "target": "c" }
  ]
}
```

## Benchmarks

graphtty uses a custom Sugiyama-style layout engine and optimized canvas operations for fast rendering. Benchmarks across all 8 sample graphs (50 iterations each, Python 3.11):

| Sample | Avg (ms) | Ops/sec |
|---|---:|---:|
| react-agent (4 nodes) | 0.17 | 5,985 |
| deep-agent (7 nodes) | 0.35 | 2,824 |
| workflow-agent (11 nodes) | 0.46 | 2,173 |
| world-map (15 nodes) | 0.62 | 1,603 |
| rag-pipeline (10 nodes) | 0.77 | 1,305 |
| supervisor-agent (7+subs) | 0.86 | 1,167 |
| etl-pipeline (12 nodes) | 0.87 | 1,151 |
| code-review (8+subs) | 1.40 | 713 |

Run `python scripts/benchmark.py` to reproduce on your machine.

## Related Projects

- **[uipath-dev](https://github.com/UiPath/uipath-dev)**: Developer console for debugging and inspecting AI agents
- **[uipath-python](https://github.com/UiPath/uipath-python)**: Python SDK and CLI to build, test, and deploy AI agents
