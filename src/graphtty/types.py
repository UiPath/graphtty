"""Data models for graphtty graphs."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any


def _filter_kwargs(cls: type, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Return only the kwargs that match fields of *cls*."""
    valid = {f.name for f in fields(cls)}
    return {k: v for k, v in kwargs.items() if k in valid}


@dataclass
class AsciiEdge:
    """A directed edge in the graph."""

    source: str
    target: str
    label: str | None = None

    def __init__(self, **kwargs: Any) -> None:
        filtered = _filter_kwargs(type(self), kwargs)
        self.source = str(filtered["source"])
        self.target = str(filtered["target"])
        self.label = filtered.get("label")


@dataclass
class AsciiNode:
    """A node in the graph."""

    id: str
    name: str
    type: str = ""
    description: str = ""
    subgraph: AsciiGraph | None = None

    def __init__(self, **kwargs: Any) -> None:
        filtered = _filter_kwargs(type(self), kwargs)
        self.id = str(filtered["id"])
        self.name = str(filtered["name"])
        self.type = str(filtered.get("type", ""))
        self.description = str(filtered.get("description", ""))
        sub = filtered.get("subgraph")
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
        filtered = _filter_kwargs(type(self), kwargs)
        raw_nodes = filtered.get("nodes", [])
        raw_edges = filtered.get("edges", [])
        self.nodes = [
            n if isinstance(n, AsciiNode) else AsciiNode(**n) for n in raw_nodes
        ]
        self.edges = [
            e if isinstance(e, AsciiEdge) else AsciiEdge(**e) for e in raw_edges
        ]
