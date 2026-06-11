"""Render sweep results and pheromone-field snapshots to images/.

    python analysis.py heatmap   # capture-vs-liveness heatmap from output/sweep.csv
    python analysis.py snapshot  # pheromone field at chosen ticks (paper Figs 1/3)
    python analysis.py           # both

The heatmap is the Solara-free reproduction of paper Figure 4: it needs only
matplotlib, so the headline result ships even if the interactive viz misbehaves.
"""

from __future__ import annotations

import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.model import ColonyModel


def heatmap(csv="output/sweep.csv", out="images/heatmap.png") -> None:
    grid = pd.read_csv(csv)
    pivot = grid.pivot(index="mislead_evap_mult", columns="detractor_frac",
                       values="food_delivered_per_coop")
    fig, ax = plt.subplots(figsize=(7, 5))
    im = ax.imshow(pivot.values, aspect="auto", origin="upper", cmap="RdBu")
    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([f"{c:.1%}" for c in pivot.columns], rotation=45, ha="right")
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{r:g}x" for r in pivot.index])
    ax.set_xlabel("detractors in colony")
    ax.set_ylabel("misleading-pheromone evaporation multiplier")
    ax.set_title("Capture vs liveness: food delivered per cooperator")
    fig.colorbar(im, ax=ax, label="food / cooperator")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


def snapshot(out="images/field.png", ticks=(300, 800, 1500), **kw) -> None:
    """Run once, capture the pheromone field at chosen ticks (green=food,
    red=mislead, gold=caution), like paper Figs 1/3."""
    m = ColonyModel(seed=7, max_steps=max(ticks), **kw)
    snaps = {}
    while m.running:
        m.step()
        if m.steps in ticks:
            snaps[m.steps] = (m.food.data.copy(), m.mislead.data.copy(), m.caution.data.copy())

    fig, axes = plt.subplots(1, len(ticks), figsize=(5 * len(ticks), 4))
    if len(ticks) == 1:
        axes = [axes]
    for ax, t in zip(axes, ticks):
        food, mislead, caution = snaps[t]
        rgb = np.zeros((*food.shape, 3))
        rgb[..., 1] = np.clip(food / food.max() if food.max() else food, 0, 1)        # green
        rgb[..., 0] = np.clip(mislead / mislead.max() if mislead.max() else mislead, 0, 1)  # red
        g = np.clip(caution / caution.max() if caution.max() else caution, 0, 1)
        rgb[..., 0] = np.maximum(rgb[..., 0], g)                                       # gold = r+g
        rgb[..., 1] = np.maximum(rgb[..., 1], g)
        ax.imshow(np.transpose(rgb, (1, 0, 2)), origin="lower")
        ax.set_title(f"t = {t}")
        ax.axis("off")
    fig.suptitle("Pheromone field  (green=food, red=mislead, gold=caution)")
    fig.tight_layout()
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    if which in ("heatmap", "both"):
        heatmap()
    if which in ("snapshot", "both"):
        snapshot(detractor_frac=0.06, mislead_evap_mult=0.0)
