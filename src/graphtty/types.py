"""Data models for graphtty graphs."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AsciiEdge:
    """A directed edge in the graph."""

    source: str
    target: str
    label: str | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.source = str(kwargs["source"])
        self.target = str(kwargs["target"])
        self.label = kwargs.get("label")


@dataclass
class AsciiNode:
    """A node in the graph."""

    id: str
    name: str
    type: str = ""
    description: str = ""
    subgraph: AsciiGraph | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.id = str(kwargs["id"])
        self.name = str(kwargs["name"])
        self.type = str(kwargs.get("type", ""))
        self.description = str(kwargs.get("description", ""))
        sub = kwargs.get("subgraph")
        if isinstance(sub, dict):
            self.subgraph = AsciiGraph(**sub)
        elif isinstance(sub, AsciiGraph):
            self.subgraph = sub
        else:
            self.subgraph = None


@dataclass
class AsciiGraph:
    """A directed graph that can be rendered to ASCII art."""

    nodes: list[AsciiNode] = field(default_factory=list)
    edges: list[AsciiEdge] = field(default_factory=list)

    def __init__(self, **kwargs: Any) -> None:
        raw_nodes = kwargs.get("nodes", [])
        raw_edges = kwargs.get("edges", [])
        self.nodes = [
            n if isinstance(n, AsciiNode) else AsciiNode(**n) for n in raw_nodes
        ]
        self.edges = [
            e if isinstance(e, AsciiEdge) else AsciiEdge(**e) for e in raw_edges
        ]
