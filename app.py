"""Interactive Solara dashboard.

Run with:
    solara run app.py

Sliders retune the protocol live: dial up the detractor fraction or slow the
misleading-pheromone evaporation to watch foraging collapse, then toggle the
cautionary defence to watch it partly recover. The grid shows ants (red =
searching, gold = returning) over three pheromone layers (green = honest food,
red = forged, gold = cautionary).

If this dashboard misbehaves (Solara's PropertyLayer rendering has been finicky
across mesa 3.x), the headless path is fully sufficient: `python analysis.py`
reproduces the heatmap and field snapshots without Solara.
"""

from __future__ import annotations

from mesa.visualization import SolaraViz, make_space_component, make_plot_component
from mesa.visualization.components import PropertyLayerStyle
from mesa.visualization import Slider

from src.model import ColonyModel
from src.protocol import TO_FOOD


def agent_portrayal(agent):
    if agent.role == "detractor":
        return {"color": "magenta", "size": 8, "marker": "x"}
    if agent.state == TO_FOOD:
        return {"color": "tab:red", "size": 6}
    return {"color": "gold", "size": 6}


# Intensity -> alpha of a single colour, per layer. mesa 3.4.1 wants a callable
# returning a PropertyLayerStyle (the dict form is deprecated). The home layer is
# left unstyled (returns None) to keep the picture readable.
_LAYER_COLORS = {
    "pheromone_food": ("lime", 0.8),
    "pheromone_mislead": ("red", 0.8),
    "pheromone_caution": ("gold", 0.6),
}


def propertylayer_portrayal(layer):
    spec = _LAYER_COLORS.get(layer.name)
    if spec is None:
        return None
    color, alpha = spec
    return PropertyLayerStyle(color=color, alpha=alpha, vmin=0.0, vmax=200.0, colorbar=False)

model_params = {
    "seed": {"type": "InputText", "value": 42, "label": "seed"},
    "max_steps": 4000,
    "n_ants": Slider("ants", value=200, min=50, max=600, step=50),
    "detractor_frac": Slider("detractor fraction", value=0.0, min=0.0, max=0.25, step=0.01),
    "mislead_evap_mult": Slider("mislead evaporation x", value=1.0, min=0.0, max=5.0, step=0.5),
    "cautionary_on": {"type": "Checkbox", "value": False, "label": "cautionary defence"},
}

model = ColonyModel(seed=42)

page = SolaraViz(
    model,
    components=[
        make_space_component(
            agent_portrayal=agent_portrayal,
            propertylayer_portrayal=propertylayer_portrayal,
        ),
        make_plot_component(["food_delivered_per_coop", "fraction_successful"]),
        make_plot_component(["fraction_captured"]),
    ],
    model_params=model_params,
    name="Stigmergy Protocol Bench",
)
