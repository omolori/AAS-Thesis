"""Weiss Robotics IEG 76-030 gripper control via Tool Digital I/O.

The gripper is wired to the UR3 tool connector digital outputs:
    Tool Digital Out 0 HIGH  →  gripper closes
    Tool Digital Out 0 LOW   →  gripper opens

Controlled via RTDEIOInterface (separate from the control interface).
Simulator runs pass gripper=None and the executor skips all calls silently.
"""
from __future__ import annotations

import logging
import time

log = logging.getLogger(__name__)


class RG2Gripper:
    """Digital I/O wrapper for the Weiss Robotics IEG 76-030.

    Parameters
    ----------
    host:
        Robot IP address — opens its own RTDEIOInterface connection.
    pin:
        Tool digital output pin number (default 0).
    settle_s:
        Sleep after each command to let fingers complete movement.
    """

    def __init__(
        self,
        host: str,
        *,
        pin: int = 0,
        settle_s: float = 1.0,
        # Legacy params accepted but ignored
        grip_width_mm: float = 0.0,
        force_n: float = 20.0,
        open_width_mm: float = 110.0,
        gripper_no: int = 1,
        grip_preset: int = 1,
        release_preset: int = 1,
        monitoring: bool = False,
    ) -> None:
        from rtde_io import RTDEIOInterface
        self._io = RTDEIOInterface(host)
        self.pin = pin
        self.settle_s = settle_s

    def open(self) -> None:
        """Open the gripper — set pin HIGH."""
        log.info("Gripper: open  → tool_digital_out[%d] = True", self.pin)
        self._io.setToolDigitalOut(self.pin, True)
        time.sleep(self.settle_s)

    def close(self) -> None:
        """Close the gripper — set pin LOW."""
        log.info("Gripper: close → tool_digital_out[%d] = False", self.pin)
        self._io.setToolDigitalOut(self.pin, False)
        time.sleep(self.settle_s)
