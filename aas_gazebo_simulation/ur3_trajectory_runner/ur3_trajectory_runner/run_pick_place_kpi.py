import math
import time
import statistics
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from sensor_msgs.msg import JointState


class UR3PickPlaceKPI(Node):
    def __init__(self):
        super().__init__("ur3_pick_place_kpi")

        self.pub = self.create_publisher(
            JointTrajectory,
            "/joint_trajectory_controller/joint_trajectory",
            10
        )

        self.sub = self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_callback,
            10
        )

        self.joint_names = [
            "shoulder_pan_joint",
            "shoulder_lift_joint",
            "elbow_joint",
            "wrist_1_joint",
            "wrist_2_joint",
            "wrist_3_joint",
        ]

        self.home = [-1.4561, -1.6660, -0.2774, -2.0748, 1.6275, -0.1098]

        self.waypoints = [
            ("home",      self.home, 0.0),
            ("pre_pick",  [-1.3320, -1.8503, -1.7179, -1.1217, 1.5566, 0.2009], 0.0),
            ("pick",      [-1.3428, -2.1051, -1.9055, -0.6799, 1.5585, 0.1948], 0.5),
            ("pre_pick",  [-1.3320, -1.8503, -1.7179, -1.1217, 1.5566, 0.2009], 0.0),
            ("pre_place", [-1.1077, -1.9063, -1.7017, -1.0908, 1.6046, 0.4865], 0.0),
            ("place",     [-1.1074, -2.1273, -1.8539, -0.7185, 1.6065, 0.4822], 0.5),
            ("pre_place", [-1.1077, -1.9063, -1.7017, -1.0908, 1.6046, 0.4865], 0.0),
            ("home",      self.home, 0.0),
        ]

        self.speed_rad_s = 0.2
        self.n_cycles = 3
        self.sent = False
        self.start_time = None

        self.expected_cycle_finish = []
        self.actual_cycle_finish = []
        self.effort_samples = []
        self.position_error_samples = []

        self.timer = self.create_timer(2.0, self.send_trajectory)

    def move_time(self, q1, q2):
        max_delta = max(abs(a - b) for a, b in zip(q1, q2))
        return max(max_delta / self.speed_rad_s, 1.0)

    def send_trajectory(self):
        if self.sent:
            return

        msg = JointTrajectory()
        msg.joint_names = self.joint_names

        t = 1.0
        prev = self.waypoints[0][1]

        p = JointTrajectoryPoint()
        p.positions = prev
        p.time_from_start.sec = int(t)
        msg.points.append(p)

        for cycle in range(self.n_cycles):
            self.get_logger().info(f"Adding cycle {cycle + 1}/{self.n_cycles}")

            for _, q, dwell in self.waypoints[1:]:
                t += self.move_time(prev, q)

                p = JointTrajectoryPoint()
                p.positions = q
                p.time_from_start.sec = int(t)
                p.time_from_start.nanosec = int((t % 1) * 1e9)
                msg.points.append(p)

                if dwell > 0:
                    t += dwell
                    p2 = JointTrajectoryPoint()
                    p2.positions = q
                    p2.time_from_start.sec = int(t)
                    p2.time_from_start.nanosec = int((t % 1) * 1e9)
                    msg.points.append(p2)

                prev = q

            self.expected_cycle_finish.append(t)

        self.start_time = time.time()
        self.pub.publish(msg)
        self.sent = True

        self.get_logger().info("Pick-and-place trajectory sent.")
        self.get_logger().info(f"Expected total time: {t:.2f} s")

    def joint_callback(self, msg):
        if not self.sent or self.start_time is None:
            return

        index = {name: i for i, name in enumerate(msg.name)}

        try:
            q = [msg.position[index[j]] for j in self.joint_names]
        except KeyError:
            return

        if len(msg.effort) >= 6:
            efforts = [msg.effort[index[j]] for j in self.joint_names]
            self.effort_samples.append(efforts)

        pos_err = math.sqrt(sum((a - b) ** 2 for a, b in zip(q, self.home)))
        self.position_error_samples.append(pos_err)

        elapsed = time.time() - self.start_time

        while len(self.actual_cycle_finish) < self.n_cycles and elapsed >= self.expected_cycle_finish[len(self.actual_cycle_finish)]:
            self.actual_cycle_finish.append(elapsed)
            cycle_no = len(self.actual_cycle_finish)

            if cycle_no == 1:
                cycle_time = self.actual_cycle_finish[0]
            else:
                cycle_time = self.actual_cycle_finish[-1] - self.actual_cycle_finish[-2]

            self.get_logger().info(f"Cycle {cycle_no} finished: {cycle_time:.2f} s")

            if cycle_no == self.n_cycles:
                self.print_kpis()
                rclpy.shutdown()

    def rms_effort(self):
        if not self.effort_samples:
            return [0.0] * 6

        output = []
        for j in range(6):
            vals = [sample[j] for sample in self.effort_samples]
            output.append(math.sqrt(sum(v * v for v in vals) / len(vals)))
        return output

    def print_kpis(self):
        cycle_times = []
        for i, finish in enumerate(self.actual_cycle_finish):
            if i == 0:
                cycle_times.append(finish)
            else:
                cycle_times.append(finish - self.actual_cycle_finish[i - 1])

        total_time = self.actual_cycle_finish[-1]
        mean_cycle = statistics.mean(cycle_times)
        std_cycle = statistics.stdev(cycle_times) if len(cycle_times) > 1 else 0.0
        rms_effort = self.rms_effort()

        if self.position_error_samples:
            rms_position_error = math.sqrt(
                sum(e * e for e in self.position_error_samples) / len(self.position_error_samples)
            )
        else:
            rms_position_error = 0.0

        energy_proxy = sum(sum(abs(e) for e in sample) for sample in self.effort_samples)

        self.get_logger().info("========== PerformanceKPIs ==========")
        self.get_logger().info(f"CycleTime values: {[round(x, 2) for x in cycle_times]} s")
        self.get_logger().info(f"Total trajectory time: {total_time:.2f} s")
        self.get_logger().info(f"Mean CycleTime: {mean_cycle:.2f} s")
        self.get_logger().info(f"CycleTime Std: {std_cycle:.2f} s")
        self.get_logger().info(f"RMSCurrent proxy / RMS effort: {[round(x, 5) for x in rms_effort]}")
        self.get_logger().info(f"EnergyConsumption proxy: {energy_proxy:.5f}")
        self.get_logger().info(f"PositionError RMS from home: {rms_position_error:.6f} rad")
        self.get_logger().info("====================================")


def main(args=None):
    rclpy.init(args=args)
    node = UR3PickPlaceKPI()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()

    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()