"""OnRobot RG2 gripper control via URScript.

The RG2 communicates through the robot's tool connector (RS-485).  After the
OnRobot URCap is installed on the UR controller, two URScript functions become
available inside the robot's script environment:

    rg_grip(width_mm, force_n)   — close to width_mm with force_n Newtons
    rg_release(width_mm)         — open to width_mm

We call them by injecting a one-line URScript via RTDEControlInterface.
The gripper is only instantiated for real-robot runs; simulator runs pass
gripper=None and the executor skips all gripper calls silently.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)

# RG2 physical limits
RG2_MAX_WIDTH_MM = 110.0
RG2_MIN_WIDTH_MM = 0.0
RG2_MAX_FORCE_N  = 40.0
RG2_MIN_FORCE_N  = 3.0


class RG2Gripper:
    """Thin wrapper around RTDEControlInterface for the OnRobot RG2.

    Parameters
    ----------
    control:
        An already-connected RTDEControlInterface instance.
    open_width_mm:
        How far to open when releasing (default = full open, 110 mm).
    grip_width_mm:
        Target width when gripping (0 = fully closed; tune per object).
    force_n:
        Gripping force in Newtons (3–40 N).
    settle_s:
        Extra sleep after each gripper command to let fingers settle.
    """

    def __init__(
        self,
        control,
        *,
        open_width_mm: float = 110.0,
        grip_width_mm: float = 0.0,
        force_n: float = 20.0,
        settle_s: float = 0.3,
    ) -> None:
        self._ctrl = control
        self.open_width_mm = float(open_width_mm)
        self.grip_width_mm = float(grip_width_mm)
        self.force_n = float(force_n)
        self.settle_s = float(settle_s)

    def open(self) -> None:
        """Open the gripper to open_width_mm."""
        script = f"rg_release({self.open_width_mm})"
        log.info("Gripper: open  → rg_release(%.1f mm)", self.open_width_mm)
        self._ctrl.sendCustomScript(script)
        time.sleep(self.settle_s)

    def close(self) -> None:
        """Close the gripper to grip_width_mm with force_n."""
        script = f"rg_grip({self.grip_width_mm}, {self.force_n})"
        log.info(
            "Gripper: close → rg_grip(%.1f mm, %.1f N)",
            self.grip_width_mm,
            self.force_n,
        )
        self._ctrl.sendCustomScript(script)
        time.sleep(self.settle_s)
