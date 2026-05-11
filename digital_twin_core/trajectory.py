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


def pick_and_place_trajectory(
    speed_rad_s: float = 0.4,
    accel_rad_s2: float = 0.3,
    dwell_s: float = 0.5,
    n_cycles: int = 3,
) -> Trajectory:
    """6-waypoint pick-and-place task recorded from the physical UR3 in the lab.

    Waypoints were jogged manually on the pendant and converted from degrees.
    Speed reduced to 0.4 rad/s for safety (robot reaches near table surface).

    Parameters can be overridden by AAS SimulationInputs values so the
    BaSyx server controls the trajectory without code changes.
    """
    return Trajectory(
        name="pick_and_place",
        waypoints=(
            Waypoint("home",      (-1.4144, -1.7048,  0.0340, -2.6787,  1.3570, 0.0625), dwell_s=0.0),
            Waypoint("pre_pick",  (-1.1088, -2.7752, -0.7957, -1.2708,  1.5778, 0.0630), dwell_s=0.0),
            Waypoint("pick",      (-1.1236, -3.4332, -0.3742, -0.8439,  1.6439, 0.0632), dwell_s=dwell_s),
            Waypoint("pre_place", (-1.5509, -2.8140, -0.3740, -1.4996,  1.6013, 0.0628), dwell_s=0.0),
            Waypoint("place",     (-1.5601, -3.4811, -0.1011, -1.1549,  1.5778, 0.0628), dwell_s=dwell_s),
            Waypoint("home",      (-1.4144, -1.7048,  0.0340, -2.6787,  1.3570, 0.0625), dwell_s=0.0),
        ),
        speed_rad_s=speed_rad_s,
        accel_rad_s2=accel_rad_s2,
        n_cycles=n_cycles,
    )
