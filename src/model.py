"""ColonyModel: the stigmergic foraging system.

The environment is four pheromone PropertyLayers on one grid:
    food     honest food trail (cooperators, returning)
    home     trail back to the nest (cooperators, searching)
    mislead  the adversary's forged food trail (detractors)
    caution  the defence's distrust signal (cooperators, when enabled)

Cooperators read food + mislead as one indistinguishable channel; that
indistinguishability is the whole attack surface. Deposition is max-merge,
evaporation is linear, both vectorised over the layer's numpy array.
"""

from __future__ import annotations

import numpy as np
from mesa import Model
from mesa.datacollection import DataCollector
from mesa.discrete_space import OrthogonalMooreGrid, PropertyLayer

from .agents import Ant
from .constants import ColonyParams
from .metrics import MODEL_REPORTERS
from .protocol import HONEST, DETRACTOR, NAIVE, CAUTIONARY


class ColonyModel(Model):
    """Keyword-only construction so SolaraViz can instantiate it from sliders.

    The signature is spelled out (rather than **overrides) because SolaraViz
    introspects __init__ and rejects a VAR_KEYWORD parameter. test_mechanism.py
    guards this signature against ColonyParams to catch drift.
    """

    def __init__(
        self,
        *,
        width: int = 120,
        height: int = 80,
        nest_xy: tuple[int, int] = (60, 40),
        nest_radius: int = 2,
        food_xy: tuple[int, int] = (18, 6),
        food_radius: int = 3,
        food_amount: int = 100_000,
        n_ants: int = 200,
        detractor_frac: float = 0.0,
        sensing_radius: int = 3,
        n_probes: int = 12,
        heading_cone: float = 0.8,
        turn_noise: float = 0.1,
        deposit_max: float = 1000.0,
        lam: float = 0.01,
        evap_rate: float = 1.0,
        mislead_evap_mult: float = 1.0,
        tau_attack: int = 100,
        cautionary_on: bool = False,
        patience_max: float = 250.0,
        patience_refill_steps: int = 1,
        max_steps: int = 2000,
        seed=None,
    ):
        super().__init__(seed=seed)
        self.p = ColonyParams(
            width=width, height=height, nest_xy=nest_xy, nest_radius=nest_radius,
            food_xy=food_xy, food_radius=food_radius, food_amount=food_amount,
            n_ants=n_ants, detractor_frac=detractor_frac, sensing_radius=sensing_radius,
            n_probes=n_probes, heading_cone=heading_cone, turn_noise=turn_noise,
            deposit_max=deposit_max, lam=lam, evap_rate=evap_rate,
            mislead_evap_mult=mislead_evap_mult, tau_attack=tau_attack,
            cautionary_on=cautionary_on, patience_max=patience_max,
            patience_refill_steps=patience_refill_steps, max_steps=max_steps, seed=seed,
        )
        p = self.p

        self.grid = OrthogonalMooreGrid((p.width, p.height), torus=False, random=self.random)
        self.food = PropertyLayer("pheromone_food", (p.width, p.height), default_value=0.0)
        self.home = PropertyLayer("pheromone_home", (p.width, p.height), default_value=0.0)
        self.mislead = PropertyLayer("pheromone_mislead", (p.width, p.height), default_value=0.0)
        self.caution = PropertyLayer("pheromone_caution", (p.width, p.height), default_value=0.0)
        for layer in (self.food, self.home, self.mislead, self.caution):
            self.grid.add_property_layer(layer)

        self.food_available = p.food_amount

        n_detractors = round(p.n_ants * p.detractor_frac)
        for i in range(p.n_ants):
            if i < n_detractors:
                Ant(self, role="detractor", write_policy=DETRACTOR, trust_policy=NAIVE)
            else:
                trust = CAUTIONARY if p.cautionary_on else NAIVE
                Ant(self, role="cooperator", write_policy=HONEST, trust_policy=trust)

        self.datacollector = DataCollector(model_reporters=MODEL_REPORTERS)
        self.running = True
        self.datacollector.collect(self)

    # -- medium operations (vectorised) ----------------------------------- #
    def deposit(self, layer: PropertyLayer, x: int, y: int, intensity: float) -> None:
        """Max-merge a deposit into a cell (Sec. 3.2)."""
        if intensity > layer.data[x, y]:
            layer.data[x, y] = intensity

    def _evaporate(self) -> None:
        """Linear evaporation, k units/step (Eq. 2). Misleading pheromone
        evaporates at k * mislead_evap_mult; mult < 1 makes the forgery persist
        and favours the attack."""
        k = self.p.evap_rate
        np.subtract(self.food.data, k, out=self.food.data)
        np.subtract(self.home.data, k, out=self.home.data)
        np.subtract(self.caution.data, k, out=self.caution.data)
        np.subtract(self.mislead.data, k * self.p.mislead_evap_mult, out=self.mislead.data)
        for layer in (self.food, self.home, self.mislead, self.caution):
            np.clip(layer.data, 0.0, None, out=layer.data)

    def step(self) -> None:
        self.agents.shuffle_do("step")
        self._evaporate()
        self.datacollector.collect(self)
        if self.steps >= self.p.max_steps:
            self.running = False
