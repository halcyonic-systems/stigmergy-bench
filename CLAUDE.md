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

## Gotchas (hard-won)

- **Mesa version: 3.4.1**, Python 3.14, own venv. `mesa.discrete_space` for grid + PropertyLayers; `PropertyLayer.data` is a raw numpy array (vectorize evap/deposit on it).
- **SolaraViz needs an explicit keyword `__init__` signature** — a `**overrides` VAR_KEYWORD param makes it raise "Missing required model parameter: overrides". `ColonyModel.__init__` spells out every field; `test_model_signature_matches_params` guards it against `ColonyParams` drift.
- **`propertylayer_portrayal` in mesa 3.4.1** is a *callable returning `PropertyLayerStyle`* (the dict-of-PropertyLayerStyle form errors with `'PropertyLayerStyle' object has no attribute 'get'`). See `app.py`.
- Verify Solara changes in a real browser (Playwright), not just by importing `app.py`. Both bugs above only surfaced on render.

## Scale

Defaults are rescaled from paper Table 1 (120×80 grid, 200 ants, ~1500 steps) for interactivity. Dial up in `src/constants.py` toward paper fidelity (480×270, 1024 ants, 50000 steps). The target is the Fig-4 boundary, not pixel fidelity.

## Status / next

Bench complete and runnable: reproduces the boundary (baseline ~10 food/coop at 100% success → 3% detractors ~2.0 at 62% → cautionary recovers success to ~92%). Field snapshot matches paper Figs 1/3. **Deferred:** SIG one-pager framing this as protocol fragility (Conant-Ashby homeostat / governance-lens hooks), to be written after Shingai has run the bench.

Conventional commits + Claude co-author (personal-project default).
