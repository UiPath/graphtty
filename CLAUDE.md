# CLAUDE.md — Developer Guide for graphtty

## Architecture

- **Package**: `src/graphtty/` with `canvas.py`, `renderer.py`, `layout.py`, `themes.py`, `types.py`, `__main__.py`
- **Import**: `from graphtty import render, AsciiGraph, AsciiNode, AsciiEdge`
- **CLI**: `uv run graphtty <file.json> [--theme NAME] [--ascii] [--no-types]`
- **Layout engine**: Sugiyama-style in `layout.py` — purpose-built for graphtty's typical 5-30 node DAGs
- **Data models**: `AsciiGraph`, `AsciiNode`, `AsciiEdge` in `types.py` (dataclasses with custom `__init__` for extra-field ignoring and nested dict coercion)
- **Dependencies**: None — pure Python, zero external runtime dependencies

## Key Design Decisions

- Canvas uses a parallel `_colors` grid (not inline ANSI) for clean color support
- Canvas tracks a bounding box (`_bb_x0/x1/y0/y1`) for O(1) `visual_size` and optimized `blit_canvas`/`to_string`
- Themes are frozen dataclasses with per-node-type styles; "default" theme = no colors
- `to_string(use_color=True)` emits ANSI codes with run-length batching (consecutive same-color cells → one sequence)
- `_metadata_lines()` wraps `node.description` into display lines (max 40 chars)
- Type label shown ONLY in top border (not as content line) to avoid redundancy
- **Types are generic/agnostic** — legacy metadata mapping (`model_name`, `tool_names`) lives ONLY in `__main__.py` (`_preprocess_nodes`), not in the library types
- Node `description` field is the generic way to add detail lines under the node name

## Layout Engine (`layout.py`)

The custom Sugiyama layout has 4 coordinate assignment phases:

1. **Phase 1** — Initial left-to-right placement per layer
2. **Phase 2** (top-down) — Centre children under parents with overlap prevention. Includes **group centering**: after overlap-prevented placement, the sibling block is shifted so it's symmetric around the average parent center
3. **Phase 3** (bottom-up) — **Only single-node layers**. Centres parents over children. Multi-node layers keep Phase 2 positions to avoid fan-in clustering (e.g. 3 nodes → 1 child would all cluster at the child's position)
4. **Phase 4** (top-down) — **Only single-node layers**. Propagates Phase 3 shifts back down (e.g. centres `__end__` under its parents)

**CRITICAL**: Do NOT apply full alternating bottom-up/top-down passes on multi-node layers — this causes rightward drift and breaks `test_multiple_labels` (edge labels overlap when nodes over-align within `_STRAIGHT_TOLERANCE`).

Other layout stages: component detection (BFS), cycle breaking (DFS back-edge reversal), layer assignment (Kahn's topological sort + longest-path), crossing minimization (3-pass barycenter: down/up/down).

## Rules

- After modifying any Python file, always run `uv run ruff format .` before finishing
- After modifying any Python file, always run `uv run ruff check --fix .` before finishing
- Before committing or creating a PR, always run `uv run mypy --config-file pyproject.toml .` and fix any errors
- Commit messages MUST follow the [Conventional Commits](https://www.conventionalcommits.org/) format: `type(scope): description` (e.g. `feat: add adaptive width rendering`, `fix(renderer): handle zero-width canvas`). Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`, `revert`. The repo uses commitlint to enforce this.

## Common Commands

```bash
uv sync                                  # install dependencies
uv run pytest tests/ -v                  # run tests (79 tests, ~0.5s)
uv run graphtty samples/react-agent/graph.json              # render a sample
uv run graphtty samples/react-agent/graph.json --theme monokai  # with theme
uv run python scripts/generate_screenshots.py                # regenerate PNGs
uv run python scripts/benchmark.py                           # performance benchmark
uv run python scripts/profile_render.py                      # cProfile bottleneck analysis
```

## Edge Routing

- **Backward edges**: `_backward_edge_corridors()` computes local route_x (right of vertically overlapping boxes) so corridors stay close to connected nodes
- **Near-straight edges**: `_STRAIGHT_TOLERANCE = 2` prevents Z-shapes when src/tgt centers differ by <=2 chars
- **Z-shape routing**: `mid_y = start_y + 2` keeps horizontal segment near source to avoid cutting through tall subgraph boxes

## Subgraph Rendering

- **CRITICAL**: Subgraphs rendered as Canvas objects via `_render_canvas()`, then blitted canvas-to-canvas with `blit_canvas()`
- Never render subgraphs as strings with ANSI codes — `len()` counts escape chars, which breaks box sizing

## Performance

- ~5.5ms total across all 8 sample graphs (50 iterations each, Python 3.11)
- Key optimizations: custom layout (no object allocation overhead), batch `puts()`, BB-scoped `blit_canvas`/`to_string`, run-length color batching, `Box` with `__slots__`, direct array access in `draw_vline`, cached theme style lookups

## Screenshots

- PNG screenshots in `screenshots/`, generated by `scripts/generate_screenshots.py` (uses Pillow + Cascadia Mono font)
- 4 samples: react-agent (monokai), deep-agent (ocean), workflow-agent (forest), supervisor-agent (dracula)
- GitHub strips SVG foreignObject/style elements, so use PNG not SVG for README

## Gotchas

- Windows cp1252 encoding: CLI uses `sys.stdout.reconfigure(encoding='utf-8')`
- `PYTHONIOENCODING=utf-8` needed when running from shell on Windows
- Cycle breaking: don't try to "restore" reversed edges after layout — just discard the bookkeeping
- Canvas `to_string()` BB hint: `_bb_x1` is a hint, scan rightward just in case
- Use combined ANSI sequences (`\033[2;32m`) not compound (`\033[2m\033[32m`)
- `to_string()` strips both leading AND trailing empty lines to avoid asymmetric padding
- Layer assignment uses topological order (Kahn's) for initial layer population, not input node order
