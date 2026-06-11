"""Parameter sweep -> capture-vs-liveness heatmap (reproduces paper Figure 4).

Sweeps detractor fraction (x) against the misleading-pheromone evaporation
multiplier (y). Each cell reports food delivered per cooperator, averaged over
replicate seeds. The expected result is a sharp boundary: low evaporation
multiplier + even a few percent detractors collapses foraging.

Uses Mesa's batch_run. Run small first:
    python -m src.sweep --quick
Full grid:
    python -m src.sweep
"""

from __future__ import annotations

import argparse
import pandas as pd
from mesa.batchrunner import batch_run

from .model import ColonyModel

# x-axis: detractor fraction. Includes the paper's striking 0.39% point.
DETRACTOR_FRACS = [0.0039, 0.01, 0.03, 0.06, 0.10, 0.15, 0.25]
# y-axis: misleading-pheromone evaporation multiplier (0 = never evaporates).
EVAP_MULTS = [0.0, 0.2, 0.5, 1.0, 2.0, 5.0]


def run_sweep(*, quick: bool = False, max_steps: int = 1500, reps: int = 3) -> pd.DataFrame:
    fracs = [0.0039, 0.03, 0.10] if quick else DETRACTOR_FRACS
    mults = [0.0, 1.0] if quick else EVAP_MULTS
    params = {
        "detractor_frac": fracs,
        "mislead_evap_mult": mults,
        "max_steps": [max_steps],
    }
    results = batch_run(
        ColonyModel,
        parameters=params,
        iterations=1 if quick else reps,
        max_steps=max_steps,
        number_processes=1,          # ant grid is numpy-heavy; processes add little
        data_collection_period=-1,   # only the final tick
        display_progress=True,
    )
    df = pd.DataFrame(results)
    grid = (
        df.groupby(["detractor_frac", "mislead_evap_mult"])["food_delivered_per_coop"]
        .mean()
        .reset_index()
    )
    return grid


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="tiny grid, 1 rep")
    ap.add_argument("--steps", type=int, default=1500)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default="output/sweep.csv")
    args = ap.parse_args()

    grid = run_sweep(quick=args.quick, max_steps=args.steps, reps=args.reps)
    grid.to_csv(args.out, index=False)
    print(f"\nwrote {args.out}")
    print(grid.pivot(index="mislead_evap_mult", columns="detractor_frac",
                     values="food_delivered_per_coop").round(2))


if __name__ == "__main__":
    main()
