"""Profile graphtty render to identify bottlenecks."""

from __future__ import annotations

import cProfile
import json
import pstats
from pathlib import Path

from graphtty import RenderOptions, render
from graphtty.themes import MONOKAI

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


def main() -> None:
    """Profile rendering of the most complex sample."""
    path = SAMPLES_DIR / "code-review" / "graph.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    opts = RenderOptions(theme=MONOKAI)
    render(data, opts)  # warm up

    pr = cProfile.Profile()
    pr.enable()
    for _ in range(200):
        render(data, opts)
    pr.disable()

    stats = pstats.Stats(pr)
    stats.strip_dirs()
    stats.sort_stats("cumulative")
    print("=== Top 30 by cumulative time ===")
    stats.print_stats(30)
    stats.sort_stats("tottime")
    print("\n=== Top 30 by total (self) time ===")
    stats.print_stats(30)


if __name__ == "__main__":
    main()
