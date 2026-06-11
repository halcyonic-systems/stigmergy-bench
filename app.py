"""Interactive Solara dashboard.

Run with:
    solara run app.py

Drive the protocol live with the sliders. The About panel in the dashboard
explains the legend and what to do; this docstring is just the entry point.

If the dashboard ever misbehaves (mesa's viz API has moved across 3.x), the
headless path is fully sufficient: `python analysis.py` reproduces the heatmap
and field snapshots without Solara.
"""

from __future__ import annotations

import solara
from matplotlib.figure import Figure
from mesa.visualization import SolaraViz, make_space_component, Slider
from mesa.visualization.components import PropertyLayerStyle
from mesa.visualization.utils import update_counter

from src.model import ColonyModel
from src.protocol import TO_FOOD

TITLE_FS, LABEL_FS, LEG_FS = 12, 10, 9


def agent_portrayal(agent):
    if agent.role == "detractor":
        return {"color": "magenta", "size": 14, "marker": "x"}
    if agent.state == TO_FOOD:
        return {"color": "#e8483c", "size": 5}      # searching
    return {"color": "gold", "size": 6}             # returning with food


# Per-layer colour and a low vmax so even faint trails saturate to a bright wash.
# mesa 3.4.1 wants a callable returning a PropertyLayerStyle (the dict form is
# deprecated). The home layer is left unstyled to keep the picture readable.
_LAYER_STYLE = {
    "pheromone_food": dict(color="lime", alpha=0.9, vmax=70.0),
    "pheromone_mislead": dict(color="red", alpha=0.9, vmax=70.0),
    "pheromone_caution": dict(color="gold", alpha=0.7, vmax=120.0),
}


def propertylayer_portrayal(layer):
    spec = _LAYER_STYLE.get(layer.name)
    if spec is None:
        return None
    return PropertyLayerStyle(vmin=0.0, colorbar=False, **spec)


ABOUT = """
## Stigmergy Protocol Bench

**Stigmergy** is coordination with no messages and no boss: ants read and write a
shared chemical medium, and the trail *is* the protocol. This bench asks what
happens when that medium can be forged.

**On the grid**
- **red dots** &mdash; ants searching for food
- **gold dots** &mdash; ants carrying food back to the nest
- **magenta &times;** &mdash; *detractors* (adversaries); only present if the detractor slider is above 0
- **green wash** &mdash; honest food trail
- **red wash** &mdash; forged trail laid by detractors (looks identical to food)
- **gold wash** &mdash; cautionary trail, the defence (only when enabled)

Ants spread from the nest (centre) in a loose blob. When some find the food (far
corner) they lay a green trail home and others sharpen it into a line. Detractors
lay a red trail that ants **cannot tell apart** from real food, so the colony
reinforces the fake one and gets trapped.

**Try this**
1. Press play with **detractor fraction = 0**: a clean green line forms. Healthy foraging.
2. Raise **detractor fraction** to ~0.10 and set **mislead evaporation &times; = 0** (forgery never fades). Watch foraging collapse. That is the cliff: a few percent of liars starve the colony.
3. Toggle **cautionary defence** on. Ants distrust trails that lead nowhere (gold), and foraging partly recovers &mdash; never fully, and the defence has its own sweet spot.

**The point (for protocol theory):** any coordination protocol whose shared
medium cannot be authenticated has this cliff. The defence is a second-order
trust layer, and it trades liveness for safety. The two right-hand panels track
exactly that. *Is the colony still foraging?* is food delivered per ant
(liveness). *Is the colony trapped?* plots the share **misled** (sitting in
forged trails now) against the share **successful** (reached food): watch them
cross as an attack bites, and uncross when the defence works.
"""


def pp_space(ax):
    ax.set_title("Colony  ·  nest at centre, food in a far corner", fontsize=TITLE_FS)
    ax.set_xticks([]); ax.set_yticks([])


# mesa's space component renders well; keep it. mesa's plot component, by contrast,
# hard-codes a default figure and crops with bbox_inches="tight", so the metric
# charts come out tiny. We render those ourselves at a controlled size instead.
SpaceView = make_space_component(
    agent_portrayal=agent_portrayal,
    propertylayer_portrayal=propertylayer_portrayal,
    post_process=pp_space,
)


@solara.component
def LinePlot(model, series, title, ylabel, ylim=None, legend=None):
    """A model-metric line chart we size and label ourselves. `series` maps a
    DataCollector column to a colour."""
    update_counter.get()   # re-render on every model step
    df = model.datacollector.get_model_vars_dataframe()
    fig = Figure(figsize=(6.6, 3.4))
    ax = fig.subplots()
    for col, color in series.items():
        ax.plot(df.index, df[col], color=color, linewidth=2.0)
    ax.set_title(title, fontsize=TITLE_FS)
    ax.set_xlabel("step", fontsize=LABEL_FS)
    ax.set_ylabel(ylabel, fontsize=LABEL_FS)
    ax.margins(x=0.01)
    if ylim:
        ax.set_ylim(*ylim)
    if legend:
        ax.legend(legend, fontsize=LEG_FS, loc="center right", framealpha=0.9)
    fig.tight_layout()
    solara.FigureMatplotlib(fig, format="png", bbox_inches="tight")


@solara.component
def Dashboard(model):
    """Deliberate, width-capped layout: walkthrough on top (collapsed), the colony
    as a hero panel, the two read-outs side by side beneath it."""
    with solara.Column(gap="12px", style={"max-width": "1000px", "margin": "0 auto"}):
        with solara.Details(summary="How to read this  —  legend & guided walkthrough", expand=False):
            solara.Markdown(ABOUT)
        solara.Markdown(
            "**Colony** &nbsp; red = searching &nbsp;·&nbsp; gold = returning with food "
            "&nbsp;·&nbsp; magenta × = detractor &nbsp;·&nbsp; green/red/gold washes = trails",
            style={"font-size": "13px", "color": "#555"},
        )
        with solara.Card():
            SpaceView(model)
        with solara.Columns([1, 1], wrap=False):
            with solara.Card():
                LinePlot(
                    model, {"food_delivered_per_coop": "tab:green"},
                    "Liveness  ·  food delivered per ant", "food / ant",
                )
            with solara.Card():
                LinePlot(
                    model,
                    {"fraction_misled": "tab:red", "fraction_successful": "tab:green"},
                    "Capture vs success  ·  share of colony", "fraction (0–1)",
                    ylim=(-0.02, 1.02),
                    legend=["misled — stuck in forged trails", "successful — reached food"],
                )


model_params = {
    "seed": {"type": "InputText", "value": 42, "label": "seed"},
    "max_steps": 5000,
    "n_ants": Slider("ants", value=200, min=50, max=600, step=50),
    "detractor_frac": Slider("detractor fraction", value=0.0, min=0.0, max=0.25, step=0.01),
    "mislead_evap_mult": Slider("mislead evaporation x", value=1.0, min=0.0, max=5.0, step=0.5),
    "cautionary_on": {"type": "Checkbox", "value": False, "label": "cautionary defence"},
}

model = ColonyModel(seed=42)

page = SolaraViz(
    model,
    components=[Dashboard],   # one composite component, laid out explicitly above
    model_params=model_params,
    name="Stigmergy Protocol Bench",
    play_interval=100,
    render_interval=4,   # simulate 4 steps per redraw; the per-step redraw, not the
                         # model, is the live bottleneck, so this ~4x's wall-clock speed
)
