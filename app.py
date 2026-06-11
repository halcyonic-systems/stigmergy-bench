"""Interactive dashboard, built directly on Solara (no mesa SolaraViz wrapper).

Run with:
    solara run app.py

Why Solara-direct instead of mesa's SolaraViz: SolaraViz owns the page and drops
every component into a half-width grid cell, so layout is a fight. Here we own the
whole page. The colony is drawn with matplotlib (a grid heatmap + agent scatter);
the metric charts are Plotly, so they are responsive native-DOM elements rather
than frozen PNGs. The model itself is untouched mesa.

If anything here breaks, the headless path is fully sufficient:
`python analysis.py` reproduces the heatmap and field snapshots.
"""

from __future__ import annotations

import time

import numpy as np
import plotly.graph_objects as go
import solara
from matplotlib.figure import Figure

from src.model import ColonyModel
from src.protocol import TO_FOOD, TO_HOME

ABOUT = """
**Stigmergy** is coordination with no messages and no boss: ants read and write a
shared chemical medium, and the trail *is* the protocol. This bench asks what
happens when that medium can be forged.

**On the grid** — red dots are ants searching, gold dots are ants carrying food
home, magenta × are *detractors* (adversaries). The washes are pheromone trails:
green = honest food, red = forged (looks identical to food), gold = cautionary
(the defence). Ants spread from the nest at the centre; some find the food in a
far corner and lay a green trail others sharpen into a line. Detractors lay a red
trail ants cannot tell apart from real food, so the colony reinforces the fake one
and gets trapped.

**Try this**
1. Press play with **detractors = 0**: a clean green line forms. Healthy foraging.
2. Raise **detractors** to ~0.10 and set **mislead evaporation × = 0** (forgery
   never fades). Watch foraging collapse. That is the cliff: a few percent of liars
   starve the colony.
3. Toggle **cautionary defence** on and watch the colony climb back out of the trap.

**The charts.** *Liveness* is food delivered per ant. *Capture vs success* plots the
share **misled** (sitting in forged trails now) against the share **successful**
(reached food): they cross as an attack bites and uncross when the defence works.
"""

# Colours for the pheromone composite and the ants.
SEARCH_C, RETURN_C, DETRACT_C = "#e8483c", "#f6c544", "#d000d0"


def colony_figure(model: ColonyModel) -> Figure:
    """Grid heatmap (green food / red forged / gold caution) with agents on top."""
    p = model.p

    def norm(a):
        m = a.max()
        return a / m if m > 0 else a

    rgb = np.zeros((p.width, p.height, 3))
    g = norm(model.caution.data)
    rgb[..., 1] = np.clip(norm(model.food.data), 0, 1)      # green = food
    rgb[..., 0] = np.clip(norm(model.mislead.data), 0, 1)   # red = forged
    rgb[..., 0] = np.maximum(rgb[..., 0], g)                # gold = red+green
    rgb[..., 1] = np.maximum(rgb[..., 1], g)

    fig = Figure(figsize=(9.0, 5.6))
    ax = fig.subplots()
    ax.imshow(np.transpose(rgb, (1, 0, 2)), origin="lower",
              extent=[0, p.width, 0, p.height], interpolation="nearest")

    buckets = {SEARCH_C: [], RETURN_C: [], DETRACT_C: []}
    for a in model.agents:
        if a.role == "detractor":
            buckets[DETRACT_C].append((a.x, a.y))
        elif a.state == TO_FOOD:
            buckets[SEARCH_C].append((a.x, a.y))
        else:
            buckets[RETURN_C].append((a.x, a.y))
    for color, pts in buckets.items():
        if not pts:
            continue
        xs, ys = zip(*pts)
        marker = "x" if color == DETRACT_C else "o"
        size = 34 if color == DETRACT_C else 7
        ax.scatter(xs, ys, s=size, c=color, marker=marker, linewidths=1.2)

    ax.set_xlim(0, p.width)
    ax.set_ylim(0, p.height)
    ax.set_xticks([])
    ax.set_yticks([])
    fig.tight_layout(pad=0.4)
    return fig


def metric_figure(model, traces, title, yrange=None):
    """A responsive Plotly line chart. `traces` maps a DataCollector column to
    (colour, display name)."""
    df = model.datacollector.get_model_vars_dataframe()
    fig = go.Figure()
    for col, (color, name) in traces.items():
        fig.add_scatter(x=df.index, y=df[col], mode="lines",
                        line=dict(color=color, width=2.5), name=name)
    fig.update_layout(
        title=dict(text=title, font=dict(size=15)),
        template="plotly_white",
        height=300,
        margin=dict(l=55, r=15, t=45, b=40),
        xaxis_title="step",
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, x=0),
    )
    if yrange:
        fig.update_yaxes(range=yrange)
    return fig


@solara.component
def LiveView(model, counter):
    """The live, per-step part of the page. Isolated in its own component so the
    redraw counter only re-renders the figures, not the whole page/controls."""
    counter.value  # subscribe: re-render this component on each step batch
    solara.Markdown(f"**step {model.steps}**  ·  food source remaining: {model.food_available:,}")
    with solara.Card():
        solara.FigureMatplotlib(colony_figure(model), format="png")
    with solara.Columns([1, 1]):
        solara.FigurePlotly(metric_figure(
            model,
            {"food_delivered_per_coop": ("#2e9e5b", "food / ant")},
            "Liveness · food delivered per ant",
        ))
        solara.FigurePlotly(metric_figure(
            model,
            {"fraction_misled": ("#d6342c", "misled — stuck in forged trails"),
             "fraction_successful": ("#2e9e5b", "successful — reached food")},
            "Capture vs success · share of colony",
            yrange=[-0.02, 1.02],
        ))


@solara.component
def Page():
    # --- parameters (reactive) ---
    n_ants = solara.use_reactive(200)
    detractor_frac = solara.use_reactive(0.0)
    mislead_evap = solara.use_reactive(1.0)
    cautionary = solara.use_reactive(False)
    seed = solara.use_reactive(42)
    steps_per_frame = solara.use_reactive(4)

    # --- run state ---
    playing = solara.use_reactive(False)
    counter = solara.use_reactive(0)          # bumped each frame to force a redraw
    reset_nonce = solara.use_reactive(0)

    # Rebuild the model whenever a parameter changes or Reset is pressed. Changing a
    # parameter restarts the run, which is the intuitive behaviour.
    def build():
        return ColonyModel(
            seed=seed.value, n_ants=n_ants.value, detractor_frac=detractor_frac.value,
            mislead_evap_mult=mislead_evap.value, cautionary_on=cautionary.value,
            max_steps=10_000_000,
        )

    model = solara.use_memo(
        build,
        dependencies=[seed.value, n_ants.value, detractor_frac.value,
                      mislead_evap.value, cautionary.value, reset_nonce.value],
    )

    def step_once():
        model.step()
        counter.set(counter.value + 1)

    # A stable holder so the long-lived loop thread always sees the *current* model
    # (use_memo rebuilds model on param change; the thread reads it live here).
    holder = solara.use_memo(lambda: {}, dependencies=[])
    holder["model"] = model

    # ONE long-lived background thread (empty deps -> started once, never restarted).
    # It loops forever and gates stepping on `playing` inside, rather than being
    # toggled via dependencies. Toggling the thread through deps gets it cancelled by
    # the re-renders that counter bumps trigger (it dies after ~2 frames). Decouple
    # sim-rate from render-rate: several steps per redraw, ~10 redraws/s, which also
    # keeps Solara's "too many renders" guard happy.
    def run_loop():
        while True:
            if playing.value:
                for _ in range(steps_per_frame.value):
                    holder["model"].step()
                counter.set(counter.value + 1)
            time.sleep(0.1)

    solara.use_thread(run_loop, dependencies=[])

    # --- sidebar controls (do NOT read counter here, so they don't redraw per frame) ---
    with solara.Sidebar():
        solara.Markdown("### Controls")
        with solara.Row():
            if playing.value:
                solara.Button("⏸ Pause", on_click=lambda: playing.set(False), color="primary")
            else:
                solara.Button("▶ Play", on_click=lambda: playing.set(True), color="primary")
            solara.Button("Step", on_click=step_once, disabled=playing.value)
        solara.Button("↺ Reset", text=True,
                      on_click=lambda: (playing.set(False), reset_nonce.set(reset_nonce.value + 1)))

        solara.Markdown("### Parameters")
        solara.SliderInt("ants", value=n_ants.value, on_value=n_ants.set,
                         min=50, max=600, step=50)
        solara.SliderFloat("detractor fraction", value=detractor_frac.value,
                           on_value=detractor_frac.set, min=0.0, max=0.25, step=0.01)
        solara.SliderFloat("mislead evaporation ×", value=mislead_evap.value,
                           on_value=mislead_evap.set, min=0.0, max=5.0, step=0.5)
        solara.Checkbox(label="cautionary defence", value=cautionary.value,
                        on_value=cautionary.set)
        solara.SliderInt("sim speed (steps/frame)", value=steps_per_frame.value,
                         on_value=steps_per_frame.set, min=1, max=12, step=1)
        solara.SliderInt("seed", value=seed.value, on_value=seed.set, min=1, max=999)

    # --- main panel: static header + isolated live view ---
    with solara.Column(style={"max-width": "1100px", "margin": "0 auto", "padding": "8px"}):
        solara.Markdown("## Stigmergy Protocol Bench")
        with solara.Details("How to read this — legend & guided walkthrough", expand=False):
            solara.Markdown(ABOUT)
        solara.Markdown(
            "**Colony** &nbsp; red = searching · gold = returning · magenta × = detractor "
            "· green/red/gold washes = trails",
            style={"font-size": "13px", "color": "#555"},
        )
        LiveView(model, counter)
