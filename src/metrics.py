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


def fraction_misled(model) -> float:
    """Capture: fraction of the colony currently standing in adversary-controlled
    territory, i.e. searching cooperators on a cell where misleading pheromone
    outweighs food pheromone.

    Parameter-free and real-time: reads 0 at baseline (no misleading pheromone
    exists), rises as the attack pulls ants into the forged web, and falls again
    when the cautionary defence pulls them out. Unlike a "never fed" proxy, it
    distinguishes "still searching" from "actively trapped" throughout a run.
    """
    coop = _cooperators(model)
    if not coop:
        return 0.0
    misled = sum(
        1 for a in coop
        if a.state == TO_FOOD and model.mislead.data[a.x, a.y] > model.food.data[a.x, a.y]
    )
    return misled / len(coop)


MODEL_REPORTERS = {
    "food_delivered_per_coop": food_delivered_per_cooperator,
    "food_collected_per_coop": food_collected_per_cooperator,
    "fraction_successful": fraction_successful,
    "fraction_misled": fraction_misled,
}
