"""Capture-vs-liveness reporters: the protocol-theory readout.

Liveness  -- is the colony still doing useful work? (food delivered per
             cooperator; fraction of cooperators that ever found food)
Capture   -- has the adversary trapped the colony? (fraction of cooperators
             stuck searching, having never reached food)

These are model-level reporters registered with Mesa's DataCollector.
"""

from __future__ import annotations

from .protocol import TO_FOOD


def _cooperators(model):
    return [a for a in model.agents if a.role == "cooperator"]


def food_delivered_per_cooperator(model) -> float:
    coop = _cooperators(model)
    if not coop:
        return 0.0
    return sum(a.food_delivered for a in coop) / len(coop)


def food_collected_per_cooperator(model) -> float:
    coop = _cooperators(model)
    if not coop:
        return 0.0
    return sum(a.food_collected for a in coop) / len(coop)


def fraction_successful(model) -> float:
    """Liveness: fraction of cooperators that have reached food at least once."""
    coop = _cooperators(model)
    if not coop:
        return 0.0
    return sum(1 for a in coop if a.food_collected > 0) / len(coop)


def fraction_captured(model) -> float:
    """Capture: fraction of cooperators still searching and never fed."""
    coop = _cooperators(model)
    if not coop:
        return 0.0
    return sum(1 for a in coop if a.state == TO_FOOD and a.food_collected == 0) / len(coop)


MODEL_REPORTERS = {
    "food_delivered_per_coop": food_delivered_per_cooperator,
    "food_collected_per_coop": food_collected_per_cooperator,
    "fraction_successful": fraction_successful,
    "fraction_captured": fraction_captured,
}
