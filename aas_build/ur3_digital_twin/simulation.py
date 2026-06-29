import numpy as np
import time


def simulate_motion(target_joints,
                    speed_scaling,
                    friction,
                    noise_level):

    # Simulated execution time
    cycle_time = 100 / speed_scaling

    # Simulated joint positions
    joint_positions = target_joints

    # Fake TCP pose
    tcp_pose = [
        0.4,
        -0.2,
        0.3,
        3.14,
        0.0,
        0.0
    ]

    # Simulated joint currents
    joint_currents = []

    for joint in target_joints:

        current = (
            abs(joint) * friction
            + np.random.normal(0, noise_level)
        )

        joint_currents.append(round(current, 3))

    return {
        "joint_positions": joint_positions,
        "tcp_pose": tcp_pose,
        "joint_currents": joint_currents,
        "cycle_time": cycle_time
    }