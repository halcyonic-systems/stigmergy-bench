# CLAUDE — stigmergy-bench

Mesa 3 ABM reimplementing + generalizing "Hacking the Colony" (arXiv:2202.01808) as a **coordination-protocol fragility bench** for the Formal Protocol Theory SIG. Stigmergy = authentication-free shared-medium protocol; detractors = Sybil-style forgery attack; cautionary pheromone = second-order trust layer trading liveness for safety.

## Core idea

The protocol is factored out of agents into `src/protocol.py`: `WritePolicy` (Honest/Detractor) and `TrustPolicy` (Naive/Cautionary). The paper's three regimes are three policy assignments. The bench sweeps over them and measures **capture vs liveness**.

## Run

```bash
source venv/bin/activate
pytest tests/                  # 10 mechanism invariants
python -m src.sweep --quick    # -> output/sweep.csv
python analysis.py             # -> images/heatmap.png, images/field.png
solara run app.py              # interactive
```

## UI: Solara-direct, NOT SolaraViz

`app.py` is built **directly on Solara**, not mesa's `SolaraViz` wrapper. We tried SolaraViz first and it fought us at every turn (see history below); the rewrite owns the whole page: our own sidebar (Play/Pause/Step/Reset + sliders), a matplotlib colony view, and **responsive Plotly** metric charts. The model is untouched mesa.

Pattern worth reusing for any mesa dashboard:
- Params + run-state as `solara.use_reactive`; rebuild model via `solara.use_memo(build, dependencies=[...params, reset_nonce])` so a param change restarts the run.
- **ONE long-lived `solara.use_thread(run_loop, dependencies=[])`** that loops forever and gates stepping on `if playing.value:` inside, reading the model via a stable `holder` dict. Do NOT pass `dependencies=[playing, model]` with a `while playing.value:` body — the re-renders that the counter bumps trigger cancel that thread after ~2 frames, so Play looks dead. Decouple sim-rate from render-rate (steps/frame + a `time.sleep`, ~10 redraws/s) to dodge Solara's "too many renders" guard.
- Isolate the per-frame figures in a child component (`LiveView`) that reads the counter; the sidebar/controls must NOT read it, or they redraw every frame.
- Colony = matplotlib (`solara.FigureMatplotlib`); line charts = Plotly (`solara.FigurePlotly`, needs `anywidget` installed).

## Gotchas (hard-won)

- **Mesa version: 3.4.1**, Python 3.14, own venv. `mesa.discrete_space` for grid + PropertyLayers; `PropertyLayer.data` is a raw numpy array (vectorize evap/deposit on it).
- **`ColonyModel.__init__` spells out every field** (no `**kwargs`). This was originally to satisfy SolaraViz introspection; kept because `test_model_signature_matches_params` guards it against `ColonyParams` drift and it's clean.
- Verify Solara changes in a **real browser (Playwright)**, not just by importing `app.py`. Every UI bug here (PropertyLayerStyle shape, the render-loop guard, the missing `anywidget` dep) surfaced only on render, never on import.
- **SolaraViz history** (no longer used, kept as warning): it forces every component to half-grid-width (`make_initial_grid_layout` → `"w": 6`), wants a callable `propertylayer_portrayal` (dict-of-PropertyLayerStyle errors), and rejects `**kwargs` init. Fighting all that is why we went Solara-direct.

## Scale

Defaults are rescaled from paper Table 1 (120×80 grid, 200 ants, ~1500 steps) for interactivity. Dial up in `src/constants.py` toward paper fidelity (480×270, 1024 ants, 50000 steps). The target is the Fig-4 boundary, not pixel fidelity.

## Status / next

Bench complete and runnable: reproduces the boundary (baseline ~10 food/coop at 100% success → 3% detractors ~2.0 at 62% → cautionary recovers success to ~92%). Field snapshot matches paper Figs 1/3. **Deferred:** SIG one-pager framing this as protocol fragility (Conant-Ashby homeostat / governance-lens hooks), to be written after Shingai has run the bench.

Conventional commits + Claude co-author (personal-project default).
