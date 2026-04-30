"""Canonical UR3 task definition used for all three pipeline comparisons.

Maps to thesis §3.x (experiment design): a pick-and-place cycle is the
canonical motion used to compare real UR3, URSim-default, and URSim-AAS
pipelines. Defining the trajectory as Python data (not a .urp file) keeps
it version-controlled and readable by every component.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Waypoint:
    name: str
    joint_positions_rad: tuple[float, float, float, float, float, float]
    dwell_s: float = 0.0


@dataclass(frozen=True)
class Trajectory:
    name: str
    waypoints: tuple[Waypoint, ...]
    speed_rad_s: float
    accel_rad_s2: float
    n_cycles: int


def pick_and_place_trajectory() -> Trajectory:
    """The canonical 6-waypoint pick-and-place task used for the thesis comparison.

    Waypoints are chosen to stay well inside the UR3 workspace, avoid
    singularities, and create clear cycle boundaries via dwells at pick/place.
    """
    return Trajectory(
        name="pick_and_place",
        waypoints=(
            Waypoint("home",      (0.0,   -1.57,  0.0,   -1.57,  0.0,  0.0), dwell_s=0.0),
            Waypoint("pre_pick",  (-0.78, -1.20, -1.00,  -1.50,  1.57, 0.0), dwell_s=0.0),
            Waypoint("pick",      (-0.78, -1.40, -1.20,  -1.30,  1.57, 0.0), dwell_s=0.5),
            Waypoint("pre_place", (0.78,  -1.20, -1.00,  -1.50,  1.57, 0.0), dwell_s=0.0),
            Waypoint("place",     (0.78,  -1.40, -1.20,  -1.30,  1.57, 0.0), dwell_s=0.5),
            Waypoint("home",      (0.0,   -1.57,  0.0,   -1.57,  0.0,  0.0), dwell_s=0.0),
        ),
        speed_rad_s=0.6,
        accel_rad_s2=0.5,
        n_cycles=3,
    )
