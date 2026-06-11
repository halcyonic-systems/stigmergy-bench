"""The protocol layer: stigmergy as a *swappable* coordination protocol.

This is what makes the project a bench rather than a reimplementation. The paper
studies one (attack, defence) point. Here the protocol is factored into two
strategy interfaces, both pure functions of local pheromone state:

  WritePolicy  -- what an agent deposits into the shared medium
  TrustPolicy  -- how an agent reads the medium when choosing where to go

The paper's three regimes are three policy assignments:

  honest colony   cooperators = (HonestWrite,   NaiveTrust)
  under attack    + detractors = (DetractorWrite, NaiveTrust)
  with defence    cooperators = (HonestWrite,   CautionaryTrust)

The deeper point for protocol theory: an authentication-free shared-medium
protocol has a sharp adversarial cliff, because the read side cannot tell an
honest signal from a forged one. NaiveTrust is exactly that blind spot;
CautionaryTrust is a second-order trust layer that buys safety at the cost of
liveness. The bench measures both.
"""

from __future__ import annotations

import math

import numpy as np

# Ant states
TO_FOOD = "to_food"     # searching: reads the food trail, lays home pheromone
TO_HOME = "to_home"     # returning: reads home pheromone, lays food pheromone


# --------------------------------------------------------------------------- #
# Write policies                                                              #
# --------------------------------------------------------------------------- #
class WritePolicy:
    """Decides what an agent deposits into the medium this step."""

    def deposit(self, agent, model) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class HonestWrite(WritePolicy):
    """Cooperator deposition.

    Searching ants lay *home* pheromone (a trail back to the nest). Returning
    ants lay *food* pheromone (a trail to the food they found). Intensity decays
    with tau, the steps since the relevant landmark, per Eq. 1:
        intensity = deposit_max * exp(-lambda * tau)
    A cell keeps the max of its current value and the new deposit (Sec. 3.2).
    """

    def deposit(self, agent, model) -> None:
        intensity = model.p.deposit_max * math.exp(-model.p.lam * agent.tau)
        if agent.state == TO_FOOD:
            model.deposit(model.home, agent.x, agent.y, intensity)
            if model.p.cautionary_on:
                _deposit_cautionary(agent, model)
        else:  # TO_HOME
            model.deposit(model.food, agent.x, agent.y, intensity)


class DetractorWrite(WritePolicy):
    """Adversary deposition: a misleading food trail, indistinguishable from the
    honest one on the read side (Sec. 3.3).

    Detractors stay dormant until tau_attack, then deposit misleading pheromone
    into the same channel cooperators read as food. tau_d (steps since the
    deposit campaign refreshed) resets whenever the detractor touches the nest,
    keeping the fake trail strong.
    """

    def deposit(self, agent, model) -> None:
        if model.steps < model.p.tau_attack:
            return
        intensity = model.p.deposit_max * math.exp(-model.p.lam * agent.tau_d)
        model.deposit(model.mislead, agent.x, agent.y, intensity)


def _deposit_cautionary(agent, model) -> None:
    """Cautionary pheromone (Eq. 4): intensity = deposit_max * exp(-lambda*rho).

    Patience rho starts at rho_max and falls while an ant searches without
    finding food, so caution *grows* the longer a trail leads nowhere. Finding
    food refills patience, silencing the warning.
    """
    intensity = model.p.deposit_max * math.exp(-model.p.lam * agent.patience)
    model.deposit(model.caution, agent.x, agent.y, intensity)


# --------------------------------------------------------------------------- #
# Trust policies                                                             #
# --------------------------------------------------------------------------- #
class TrustPolicy:
    """Decides how an agent perceives the food trail when searching."""

    def perceived_food_trail(self, model) -> np.ndarray:  # pragma: no cover
        raise NotImplementedError


class NaiveTrust(TrustPolicy):
    """The attackable baseline: follow the strongest food signal, unable to tell
    honest food pheromone from a detractor's forgery. Perceived trail is simply
    the sum of the two channels."""

    def perceived_food_trail(self, model) -> np.ndarray:
        return model.food.data + model.mislead.data


class CautionaryTrust(TrustPolicy):
    """Second-order trust: ignore any cell whose cautionary pheromone exceeds its
    food pheromone (Sec. 4.2). A trail that others have flagged as fruitless is
    distrusted, blunting the attack. The cost is liveness: over-cautious ants
    abandon real trails too."""

    def perceived_food_trail(self, model) -> np.ndarray:
        food = model.food.data + model.mislead.data
        return np.where(model.caution.data > food, 0.0, food)


# Singletons (policies are stateless)
HONEST = HonestWrite()
DETRACTOR = DetractorWrite()
NAIVE = NaiveTrust()
CAUTIONARY = CautionaryTrust()
