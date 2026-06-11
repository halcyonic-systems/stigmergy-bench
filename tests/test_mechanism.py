"""Mechanism invariants. These pin the protocol's load-bearing behaviour so a
later refactor can't silently break the result the bench exists to show.
"""

import dataclasses
import inspect

import numpy as np
import pytest

from src.constants import ColonyParams
from src.model import ColonyModel
from src.protocol import NAIVE, CAUTIONARY


def test_model_signature_matches_params():
    """SolaraViz introspects ColonyModel.__init__; its keyword params must stay
    in sync with ColonyParams or sliders silently break."""
    sig = {n for n, p in inspect.signature(ColonyModel.__init__).parameters.items()
           if p.kind == inspect.Parameter.KEYWORD_ONLY}
    fields = {f.name for f in dataclasses.fields(ColonyParams)}
    assert sig == fields


def _run(steps=1500, **kw):
    m = ColonyModel(seed=42, max_steps=steps, **kw)
    while m.running:
        m.step()
    return m


# -- medium operations ---------------------------------------------------- #
def test_deposit_is_max_merge():
    m = ColonyModel(seed=1, max_steps=1)
    m.deposit(m.food, 5, 5, 10.0)
    m.deposit(m.food, 5, 5, 4.0)      # smaller deposit must not lower the cell
    assert m.food.data[5, 5] == 10.0
    m.deposit(m.food, 5, 5, 20.0)
    assert m.food.data[5, 5] == 20.0


def test_evaporation_is_monotonic_and_nonnegative():
    m = ColonyModel(seed=1, max_steps=1, evap_rate=5.0)
    m.food.data[5, 5] = 12.0
    m._evaporate()
    assert m.food.data[5, 5] == 7.0
    for _ in range(5):
        m._evaporate()
    assert m.food.data[5, 5] == 0.0     # clipped, never negative


def test_mislead_evap_multiplier():
    """mislead_evap_mult < 1 makes the forgery persist longer than honest pheromone."""
    m = ColonyModel(seed=1, max_steps=1, evap_rate=2.0, mislead_evap_mult=0.5)
    m.food.data[1, 1] = 10.0
    m.mislead.data[1, 1] = 10.0
    m._evaporate()
    assert m.food.data[1, 1] == 8.0      # lost 2.0
    assert m.mislead.data[1, 1] == 9.0   # lost 2.0 * 0.5


# -- trust policies ------------------------------------------------------- #
def test_naive_trust_cannot_distinguish_forgery():
    m = ColonyModel(seed=1, max_steps=1)
    m.food.data[3, 3] = 4.0
    m.mislead.data[3, 3] = 6.0
    # Naive perceives the sum: honest and forged signals are indistinguishable.
    assert NAIVE.perceived_food_trail(m)[3, 3] == 10.0


def test_cautionary_trust_masks_flagged_cells():
    m = ColonyModel(seed=1, max_steps=1, cautionary_on=True)
    m.food.data[3, 3] = 5.0
    m.caution.data[3, 3] = 9.0           # caution exceeds food -> distrust
    assert CAUTIONARY.perceived_food_trail(m)[3, 3] == 0.0
    m.caution.data[3, 3] = 1.0           # caution below food -> trust
    assert CAUTIONARY.perceived_food_trail(m)[3, 3] == 5.0


# -- emergent system behaviour ------------------------------------------- #
def test_baseline_colony_forages():
    m = _run()
    assert m.datacollector.get_model_vars_dataframe().iloc[-1].fraction_successful > 0.8


def test_attack_collapses_foraging():
    base = _run().datacollector.get_model_vars_dataframe().iloc[-1]
    atk = _run(detractor_frac=0.10, mislead_evap_mult=0.0).datacollector.get_model_vars_dataframe().iloc[-1]
    # A small detractor fraction with persistent forgery sharply cuts delivery.
    assert atk.food_delivered_per_coop < 0.5 * base.food_delivered_per_coop


def test_cautionary_defence_improves_success_under_attack():
    atk = _run(detractor_frac=0.03, mislead_evap_mult=0.0).datacollector.get_model_vars_dataframe().iloc[-1]
    dfn = _run(detractor_frac=0.03, mislead_evap_mult=0.0,
               cautionary_on=True).datacollector.get_model_vars_dataframe().iloc[-1]
    assert dfn.fraction_successful >= atk.fraction_successful


def test_no_detractors_means_empty_mislead_channel():
    m = _run(steps=300)
    assert np.all(m.mislead.data == 0.0)


def test_fraction_misled_is_zero_without_attack():
    """Capture reads exactly 0 in a healthy colony: no forged pheromone exists,
    so no ant can be standing in adversary territory."""
    df = _run(steps=400).datacollector.get_model_vars_dataframe()
    assert (df.fraction_misled == 0.0).all()


def test_fraction_misled_rises_under_attack():
    df = _run(detractor_frac=0.10, mislead_evap_mult=0.0).datacollector.get_model_vars_dataframe()
    assert df.fraction_misled.max() > 0.0
