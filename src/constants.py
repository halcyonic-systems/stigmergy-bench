"""Model parameters.

Defaults follow the ratios of Table 1 in Aswale et al., "Hacking the Colony"
(AAMAS 2022, arXiv:2202.01808), rescaled to a grid that runs interactively in
Python. The paper simulates a 1920x1080 world with cell size 4 (a 480x270 grid),
1024 ants, 50000 steps. That is faithful but heavy. We keep the load-bearing
ratios (food-to-nest distance, sensing range in cells, deposit/evaporation
constants) and expose world size and ant count as parameters so the bench can be
dialed from "fast and interactive" up toward paper fidelity.

The phenomenon the bench must reproduce is the Figure 4 boundary: a small
fraction of detractors, combined with slowly-evaporating misleading pheromone,
collapses foraging. Pixel-exact dynamics are not the goal.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class ColonyParams:
    # --- world (rescaled; paper: 480x270 grid) ---
    width: int = 120
    height: int = 80
    nest_xy: tuple[int, int] = (60, 40)        # paper: world centre
    nest_radius: int = 2
    food_xy: tuple[int, int] = (18, 6)          # paper: far corner from nest
    food_radius: int = 3
    food_amount: int = 100_000                  # food bits available at source

    # --- population ---
    n_ants: int = 200                           # paper: 1024
    detractor_frac: float = 0.0                 # fraction of colony that are detractors

    # --- motion (paper: continuous pose; here discretised to the grid) ---
    sensing_radius: int = 3                     # cells; paper l^s_max=40 units ~ 10 cells
    n_probes: int = 12                          # paper chi=32 probing vectors
    heading_cone: float = 0.8                   # * pi; paper theta^s_max=0.8*pi
    turn_noise: float = 0.1                     # * pi; eta, applied while following a trail
    wander_noise: float = 0.35                  # * pi; larger turn when NO trail is sensed, so
                                                #   searchers explore a blob instead of beelining
                                                #   to the world edge (a correlated random walk)

    # --- pheromone deposition / evaporation ---
    # deposit intensity = deposit_max * exp(-lambda * tau)
    deposit_max: float = 1000.0
    lam: float = 0.01                           # paper lambda
    evap_rate: float = 1.0                      # k: linear units lost per step (paper k=1/s)
    mislead_evap_mult: float = 1.0              # multiplier on evaporation of misleading pheromone
                                                #   <1 => mislead persists longer (favours attack)
    tau_attack: int = 100                       # steps before detractors begin depositing

    # --- defence: cautionary pheromone (paper sec. 4) ---
    cautionary_on: bool = False
    patience_max: float = 500.0                 # rho_max. Sweet spot: too low (~250) and caution
                                                #   blankets the area before the real trail forms
                                                #   (defence backfires); too high and it never warns.
    patience_refill_steps: int = 1              # t_p: steps to reset patience to rho_max on finding food

    # --- run control ---
    max_steps: int = 2000                       # paper: 50000
    seed: int | None = None

    def as_kwargs(self) -> dict:
        """Flatten to keyword args for kwargs-only model construction (SolaraViz needs this)."""
        return asdict(self)
