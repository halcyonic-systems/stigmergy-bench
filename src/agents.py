"""The Ant agent.

Behaviour is B = f(P, E) in Lewin's terms (the abm skill's discipline):

  P (person)       pose (x, y, heading), state (searching / returning),
                   role (cooperator / detractor), tau counters, patience
  E (environment)  the pheromone PropertyLayers, the nest, the food source
  f (interaction)  sense a cone of cells -> step toward the strongest *trusted*
                   trail -> deposit -> handle landmark events

Every decision is local to the ant's sensing radius. No agent rule reads a
colony-level aggregate; the collapse under attack is emergent, not encoded.
"""

from __future__ import annotations

import math

from mesa.discrete_space import CellAgent

from .protocol import TO_FOOD, TO_HOME

# Eight Moore steps, indexed by heading octant.
_STEPS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def _dist2(ax: int, ay: int, bx: int, by: int) -> int:
    return (ax - bx) ** 2 + (ay - by) ** 2


class Ant(CellAgent):
    def __init__(self, model, *, role: str, write_policy, trust_policy):
        super().__init__(model)
        self.role = role
        self.write_policy = write_policy
        self.trust_policy = trust_policy

        nx, ny = model.p.nest_xy
        self.x, self.y = nx, ny
        self.cell = model.grid[(nx, ny)]
        self.heading = model.random.uniform(0, 2 * math.pi)

        self.state = TO_FOOD
        self.tau = 0                       # steps since last landmark (deposit decay)
        self.tau_d = 0                     # detractor: steps since nest (mislead decay)
        self.patience = model.p.patience_max
        self.food_collected = 0            # times this ant reached food
        self.food_delivered = 0            # times this ant returned food to nest

    # -- sensing ---------------------------------------------------------- #
    def _choose_heading(self) -> float:
        """Probe a cone of cells, head toward the strongest trusted trail."""
        p = self.model.p
        if self.state == TO_FOOD:
            field = self.trust_policy.perceived_food_trail(self.model)
        else:
            field = self.model.home.data

        best_val, best_heading = -1.0, None
        for _ in range(p.n_probes):
            ang = self.heading + self.model.random.uniform(
                -p.heading_cone * math.pi, p.heading_cone * math.pi
            )
            dist = self.model.random.randint(1, p.sensing_radius)
            cx = int(round(self.x + dist * math.cos(ang)))
            cy = int(round(self.y + dist * math.sin(ang)))
            if not (0 <= cx < p.width and 0 <= cy < p.height):
                continue
            val = field[cx, cy]
            if val > best_val:
                best_val, best_heading = val, math.atan2(cy - self.y, cx - self.x)

        if best_val <= 0.0 or best_heading is None:
            best_heading = self.heading  # no trail: keep course
        noise = self.model.random.uniform(-p.turn_noise * math.pi, p.turn_noise * math.pi)
        return best_heading + noise

    # -- motion ----------------------------------------------------------- #
    def _step_forward(self) -> None:
        p = self.model.p
        octant = int(round(self.heading / (math.pi / 4))) % 8
        dx, dy = _STEPS[octant]
        nx, ny = self.x + dx, self.y + dy
        # Law of reflection at the world boundary (paper Sec. 3.2).
        if not (0 <= nx < p.width):
            self.heading = math.pi - self.heading
            nx = min(max(nx, 0), p.width - 1)
        if not (0 <= ny < p.height):
            self.heading = -self.heading
            ny = min(max(ny, 0), p.height - 1)
        self.x, self.y = nx, ny
        self.cell = self.model.grid[(nx, ny)]

    # -- landmark events -------------------------------------------------- #
    def _handle_landmarks(self) -> None:
        m, p = self.model, self.model.p

        at_nest = _dist2(self.x, self.y, *p.nest_xy) <= p.nest_radius ** 2
        at_food = _dist2(self.x, self.y, *p.food_xy) <= p.food_radius ** 2

        if self.role == "detractor":
            if at_nest:
                self.tau_d = 0
            elif at_food:                       # bounce off the food region
                self.heading += math.pi
            return

        # cooperator
        if self.state == TO_FOOD and at_food and m.food_available > 0:
            m.food_available -= 1
            self.food_collected += 1
            self.state = TO_HOME
            self.tau = 0
            self.patience = p.patience_max       # finding food refills patience
            self.heading += math.pi              # turn back toward nest
        elif self.state == TO_HOME and at_nest:
            self.food_delivered += 1
            self.state = TO_FOOD
            self.tau = 0
            self.heading = m.random.uniform(0, 2 * math.pi)

    # -- main step -------------------------------------------------------- #
    def step(self) -> None:
        self.heading = self._choose_heading()
        self._step_forward()
        self.tau += 1
        if self.role == "detractor":
            self.tau_d += 1
        elif self.state == TO_FOOD and self.model.p.cautionary_on:
            self.patience = max(0.0, self.patience - 1.0)  # caution grows while searching
        self.write_policy.deposit(self, self.model)
        self._handle_landmarks()
