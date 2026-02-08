# graphtty

[![PyPI downloads](https://img.shields.io/pypi/dm/graphtty.svg)](https://pypi.org/project/graphtty/)
[![PyPI - Version](https://img.shields.io/pypi/v/graphtty)](https://img.shields.io/pypi/v/graphtty)
[![Python versions](https://img.shields.io/pypi/pyversions/graphtty.svg)](https://pypi.org/project/graphtty/)

Turn any directed graph into colored ASCII art for your terminal.

## Installation

```bash
pip install graphtty
```

### Deep Agent (ocean theme)

<img src="https://raw.githubusercontent.com/uipath/graphtty/main/screenshots/deep-agent.png" width="700">

### Supervisor Agent (dracula theme)

<img src="https://raw.githubusercontent.com/uipath/graphtty/main/screenshots/supervisor-agent.png" width="700">

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

## Acknowledgements

Built with :heart: on top of [grandalf](https://github.com/bdcht/grandalf), a Python library for graph layout using the Sugiyama algorithm.
