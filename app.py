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
**What this is.** A colony of ants coordinating with no messages and no leader: they
read and write a shared chemical trail, and that trail *is* the protocol. This bench
shows what happens when the trail can be **forged**.

#### How it works
Ants leave the nest (centre) and wander until they find food in a far corner. They lay
a green trail home, and other ants sharpen it into a line. *Detractors* lay a red trail
that looks **identical** to real food, so the colony reinforces the fake one and gets
trapped. The *cautionary defence* lets ants flag trails that led nowhere, so others
learn to distrust them.

#### Try this
1. **Healthy colony.** Press play with **detractor fraction = 0**. A clean green line forms.
2. **The cliff.** Raise **detractor fraction** to ~0.10 and set **mislead evaporation × = 0**
   (forgery never fades). Foraging collapses: a few percent of liars starve the colony.
3. **The defence.** Turn on **cautionary defence** and watch the colony climb back out.

#### Reading the charts
- **Liveness** — food delivered per ant. Higher means the colony is fed.
- **Capture vs success** — the share **misled** (stuck in fake trails now) against the
  share **successful** (reached food). They cross as an attack bites, and uncross when
  the defence works.
"""

# Colours for the pheromone composite and the ants.
SEARCH_C, RETURN_C, DETRACT_C = "#e8483c", "#f6c544", "#d000d0"
FOOD_C, FORGED_C, CAUTION_C = "#22c55e", "#ef4444", "#f6c544"


def _chip(color, label, round_=True):
    radius = "50%" if round_ else "3px"
    return (
        '<span style="display:inline-flex;align-items:center;margin:2px 16px 2px 0;'
        'white-space:nowrap;font-size:13px;color:#374151">'
        f'<span style="width:12px;height:12px;background:{color};border-radius:{radius};'
        'display:inline-block;margin-right:6px;border:1px solid rgba(0,0,0,.15)"></span>'
        f'{label}</span>'
    )


def legend_html():
    ants = "".join([
        _chip(SEARCH_C, "searching"),
        _chip(RETURN_C, "returning with food"),
        '<span style="display:inline-flex;align-items:center;margin:2px 16px 2px 0;'
        'font-size:13px;color:#374151"><span style="color:%s;font-weight:700;'
        'margin-right:5px">×</span>detractor</span>' % DETRACT_C,
    ])
    trails = "".join([
        _chip(FOOD_C, "real food trail", round_=False),
        _chip(FORGED_C, "forged trail", round_=False),
        _chip(CAUTION_C, "cautionary trail", round_=False),
    ])
    label = ('display:inline-block;width:54px;color:#6b7280;font-weight:600;'
             'font-size:11px;letter-spacing:.04em')
    return (
        '<div style="padding:10px 14px;background:#f9fafb;border:1px solid #eceef1;'
        'border-radius:8px;line-height:2.0">'
        f'<div><span style="{label}">ANTS</span>{ants}</div>'
        f'<div><span style="{label}">TRAILS</span>{trails}</div>'
        '</div>'
    )


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

    def caption(text):
        solara.Markdown(text, style={"font-size": "12px", "color": "#6b7280",
                                     "margin": "-10px 0 14px 2px", "line-height": "1.45"})

    # --- sidebar controls (do NOT read counter here, so they don't redraw per frame) ---
    with solara.Sidebar():
        solara.Markdown("### Run")
        with solara.Row(gap="8px"):
            if playing.value:
                solara.Button("⏸ Pause", on_click=lambda: playing.set(False), color="primary")
            else:
                solara.Button("▶ Play", on_click=lambda: playing.set(True), color="primary")
            solara.Button("Step", on_click=step_once, disabled=playing.value, outlined=True)
        solara.Button("↺ Reset", text=True,
                      on_click=lambda: (playing.set(False), reset_nonce.set(reset_nonce.value + 1)))

        solara.Markdown("### The attack")
        solara.SliderFloat("Detractor fraction", value=detractor_frac.value,
                           on_value=detractor_frac.set, min=0.0, max=0.25, step=0.01)
        caption("Share of ants that are adversaries, laying fake trails that look "
                "identical to real food.")
        solara.SliderFloat("Forgery persistence", value=mislead_evap.value,
                           on_value=mislead_evap.set, min=0.0, max=5.0, step=0.5)
        caption("How fast forged trails fade (the *mislead evaporation* rate). "
                "**0 = never fade**, the strongest attack; higher decays the forgery faster.")

        solara.Markdown("### The defence")
        solara.Checkbox(label="Cautionary defence", value=cautionary.value,
                        on_value=cautionary.set)
        caption("Ants flag trails that led nowhere so others learn to distrust them. "
                "Helps, but trades some foraging speed for safety.")

        solara.Markdown("### Colony & run")
        solara.SliderInt("Colony size (ants)", value=n_ants.value, on_value=n_ants.set,
                         min=50, max=600, step=50)
        caption("Number of ants foraging.")
        solara.SliderInt("Sim speed (steps / frame)", value=steps_per_frame.value,
                         on_value=steps_per_frame.set, min=1, max=12, step=1)
        caption("Model steps per redraw. Higher animates faster.")
        solara.SliderInt("Random seed", value=seed.value, on_value=seed.set, min=1, max=999)
        caption("Change to reshuffle the run. Any change here restarts the simulation.")

    # --- main panel: static header + isolated live view ---
    with solara.Column(style={"max-width": "1100px", "margin": "0 auto", "padding": "8px 8px 40px"}):
        solara.Markdown("## Stigmergy Protocol Bench")
        solara.Markdown(
            "How a coordination protocol with no way to authenticate its signals "
            "collapses under a few forged ones, and what a defence costs.",
            style={"font-size": "15px", "color": "#4b5563", "margin": "-6px 0 10px"},
        )
        with solara.Details("ⓘ  About — how it works & a guided walkthrough", expand=False):
            solara.Markdown(ABOUT)
        solara.HTML(tag="div", unsafe_innerHTML=legend_html(),
                    style="margin:10px 0 4px")
        LiveView(model, counter)
