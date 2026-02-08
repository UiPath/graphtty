"""Data models for graphtty graphs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AsciiEdge(BaseModel):
    """A directed edge in the graph."""

    model_config = ConfigDict(extra="ignore")

    source: str
    target: str
    label: str | None = None


class AsciiNode(BaseModel):
    """A node in the graph."""

    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    type: str = ""
    description: str = ""
    subgraph: AsciiGraph | None = None


class AsciiGraph(BaseModel):
    """A directed graph that can be rendered to ASCII art."""

    model_config = ConfigDict(extra="ignore")

    nodes: list[AsciiNode] = []
    edges: list[AsciiEdge] = []
