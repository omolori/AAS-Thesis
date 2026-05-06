"""RTDE client wrapper.

Wraps the `ur_rtde` library so the rest of the codebase doesn't depend on it
directly. Works identically for URSim and a physical UR3 -- only the host IP
differs.

Reference data fields exposed by RTDE on UR controllers:
- actual_q             (6-vector, joint positions, rad)
- actual_qd            (6-vector, joint velocities, rad/s)
- actual_TCP_pose      (6-vector, [x, y, z, rx, ry, rz] in m / axis-angle rad)
- actual_TCP_speed     (6-vector)
- actual_current       (6-vector, joint currents, A)
- target_q             (6-vector, commanded joint positions, rad)
- runtime_state        (int: 0=stopped, 1=playing, 2=paused)
- timestamp            (float, controller-side seconds)

We expose a simple `sample()` method that returns one snapshot as a dict,
plus a `stream(duration_s)` generator for continuous recording.
"""
from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field, asdict
from typing import Any

try:
    from rtde_receive import RTDEReceiveInterface
    _RTDE_AVAILABLE = True
except ImportError:
    RTDEReceiveInterface = None  # type: ignore[assignment,misc]
    _RTDE_AVAILABLE = False


@dataclass
class RobotSample:
    """One snapshot of robot state."""
    wall_time: float                 # host-side time.time()
    controller_timestamp: float      # robot's own clock
    actual_q: list[float] = field(default_factory=list)
    actual_qd: list[float] = field(default_factory=list)
    actual_tcp_pose: list[float] = field(default_factory=list)
    actual_tcp_speed: list[float] = field(default_factory=list)
    actual_current: list[float] = field(default_factory=list)
    target_q: list[float] = field(default_factory=list)
    runtime_state: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RTDEClient:
    """Thin wrapper over ur_rtde's RTDEReceiveInterface.

    Use as a context manager:

        with RTDEClient("192.168.1.100") as client:
            for sample in client.stream(duration_s=5.0):
                print(sample.actual_q)
    """

    def __init__(self, host: str, frequency_hz: float = 125.0) -> None:
        self.host = host
        self.frequency_hz = frequency_hz
        self._receiver: RTDEReceiveInterface | None = None

    # -- context manager ----------------------------------------------------
    def __enter__(self) -> RTDEClient:
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.disconnect()

    # -- connection lifecycle ----------------------------------------------
    def connect(self) -> None:
        if self._receiver is not None:
            return
        if not _RTDE_AVAILABLE:
            raise ImportError(
                "ur_rtde is not installed. Run: pip install ur_rtde"
            )
        self._receiver = RTDEReceiveInterface(self.host, self.frequency_hz)

    def disconnect(self) -> None:
        if self._receiver is not None:
            try:
                self._receiver.disconnect()
            except Exception:
                pass
            self._receiver = None

    # -- data --------------------------------------------------------------
    def sample(self) -> RobotSample:
        if self._receiver is None:
            raise RuntimeError("RTDEClient is not connected. Call connect() first.")

        return RobotSample(
            wall_time=time.time(),
            controller_timestamp=self._receiver.getTimestamp(),
            actual_q=list(self._receiver.getActualQ()),
            actual_qd=list(self._receiver.getActualQd()),
            actual_tcp_pose=list(self._receiver.getActualTCPPose()),
            actual_tcp_speed=list(self._receiver.getActualTCPSpeed()),
            actual_current=list(self._receiver.getActualCurrent()),
            target_q=list(self._receiver.getTargetQ()),
            runtime_state=int(self._receiver.getRuntimeState()),
        )

    def stream(self, duration_s: float) -> Iterator[RobotSample]:
        """Yield samples for `duration_s` seconds at roughly `frequency_hz`."""
        if self._receiver is None:
            raise RuntimeError("RTDEClient is not connected.")

        period = 1.0 / self.frequency_hz
        t_end = time.time() + duration_s
        next_tick = time.time()
        while time.time() < t_end:
            yield self.sample()
            next_tick += period
            sleep_for = next_tick - time.time()
            if sleep_for > 0:
                time.sleep(sleep_for)
