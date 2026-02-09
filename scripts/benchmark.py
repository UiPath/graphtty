"""Benchmark graphtty render performance across all sample graphs."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from graphtty import RenderOptions, render
from graphtty.themes import MONOKAI

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"
ITERATIONS = 50


def _load_samples() -> list[tuple[str, dict[str, Any]]]:
    """Load all sample graph JSON files."""
    samples = []
    for p in sorted(SAMPLES_DIR.glob("*/graph.json")):
        with open(p, encoding="utf-8") as f:
            samples.append((p.parent.name, json.load(f)))
    return samples


def bench_one(name: str, data: dict[str, Any], iterations: int) -> float:
    """Benchmark a single sample, return average time in ms."""
    opts = RenderOptions(theme=MONOKAI)
    # Warm up
    render(data, opts)

    start = time.perf_counter()
    for _ in range(iterations):
        render(data, opts)
    elapsed = time.perf_counter() - start
    return (elapsed / iterations) * 1000


def main() -> None:
    """Run benchmarks and print results."""
    samples = _load_samples()
    if not samples:
        print("No samples found!")
        return

    print(f"Benchmarking {len(samples)} samples x {ITERATIONS} iterations each\n")
    print(f"{'Sample':<25} {'Avg (ms)':>10} {'Ops/sec':>10}")
    print("-" * 47)

    total_ms = 0.0
    for name, data in samples:
        avg_ms = bench_one(name, data, ITERATIONS)
        total_ms += avg_ms
        ops = 1000 / avg_ms if avg_ms > 0 else float("inf")
        print(f"{name:<25} {avg_ms:>10.3f} {ops:>10.0f}")

    print("-" * 47)
    avg_all = total_ms / len(samples)
    print(f"{'AVERAGE':<25} {avg_all:>10.3f} {1000 / avg_all:>10.0f}")
    print(f"{'TOTAL':<25} {total_ms:>10.3f}")


if __name__ == "__main__":
    main()
