import csv, json, math, random, statistics, time
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class Pipeline3(Node):
    def __init__(self):
        super().__init__("pipeline3_aas_gazebo")

        self.joint_names = [
            "shoulder_pan_joint", "shoulder_lift_joint", "elbow_joint",
            "wrist_1_joint", "wrist_2_joint", "wrist_3_joint"
        ]

        # ===============================
        # Hardcoded AAS: MotionCommand
        # ===============================
        self.target_joint_positions = [-1.4561, -1.6660, -0.2774, -2.0748, 1.6275, -0.1098]
        self.speed_scaling = 1.0
        self.payload_mass = 1.2

        # ===============================
        # Hardcoded AAS: DynamicsParameters
        # ===============================
        self.friction_coefficient = 0.12
        self.current_noise_level = 0.08
        self.control_latency = 0.03
        self.damping_factor = 0.15

        self.base_speed_rad_s = 0.2
        self.base_accel_rad_s2 = 0.15
        self.speed_rad_s = self.base_speed_rad_s * self.speed_scaling
        self.accel_rad_s2 = self.base_accel_rad_s2 * self.speed_scaling

        self.home = self.target_joint_positions
        self.n_cycles = 3

        self.waypoints = [
            ("home", self.home, 0.0),
            ("pre_pick", [-1.3320, -1.8503, -1.7179, -1.1217, 1.5566, 0.2009], 0.0),
            ("pick", [-1.3428, -2.1051, -1.9055, -0.6799, 1.5585, 0.1948], 0.5),
            ("pre_pick", [-1.3320, -1.8503, -1.7179, -1.1217, 1.5566, 0.2009], 0.0),
            ("pre_place", [-1.1077, -1.9063, -1.7017, -1.0908, 1.6046, 0.4865], 0.0),
            ("place", [-1.1074, -2.1273, -1.8539, -0.7185, 1.6065, 0.4822], 0.5),
            ("pre_place", [-1.1077, -1.9063, -1.7017, -1.0908, 1.6046, 0.4865], 0.0),
            ("home", self.home, 0.0),
        ]

        self.pub = self.create_publisher(
            JointTrajectory,
            "/joint_trajectory_controller/joint_trajectory",
            10,
        )

        self.sub = self.create_subscription(
            JointState,
            "/joint_states",
            self.joint_state_cb,
            10,
        )

        ts = time.strftime("%Y%m%d_%H%M%S")
        self.csv_path = Path.home() / "ros2_ws" / f"pipeline3_joint_states_{ts}.csv"
        self.kpi_path = Path.home() / "ros2_ws" / f"pipeline3_kpis_{ts}.json"

        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.writer(self.csv_file)
        self.csv_writer.writerow([
            "time_s", "joint", "position_rad", "velocity_rad_s",
            "effort_raw", "current_proxy"
        ])

        self.sent = False
        self.start_time = None
        self.commanded_cycle_times = []
        self.effort_samples = []
        self.current_proxy_samples = []
        self.position_error_samples = []

        self.print_aas_inputs()
        self.timer = self.create_timer(2.0, self.send_trajectory)

    def print_aas_inputs(self):
        self.get_logger().info("========== MotionCommand ==========")
        self.get_logger().info(f"TargetJointPositions = {self.target_joint_positions}")
        self.get_logger().info(f"SpeedScaling = {self.speed_scaling}")
        self.get_logger().info(f"PayloadMass = {self.payload_mass} kg")
        self.get_logger().info("======= DynamicsParameters ========")
        self.get_logger().info(f"FrictionCoefficient = {self.friction_coefficient}")
        self.get_logger().info(f"CurrentNoiseLevel = {self.current_noise_level} A")
        self.get_logger().info(f"ControlLatency = {self.control_latency} s")
        self.get_logger().info(f"DampingFactor = {self.damping_factor}")
        self.get_logger().info("===================================")

    def single_joint_move_time(self, delta):
        delta = abs(delta)
        v = self.speed_rad_s
        a = self.accel_rad_s2

        t_accel = v / a
        d_accel = 0.5 * a * t_accel * t_accel

        if delta >= 2.0 * d_accel:
            d_cruise = delta - 2.0 * d_accel
            return 2.0 * t_accel + d_cruise / v
        else:
            return 2.0 * math.sqrt(delta / a)

    def move_time(self, q1, q2):
        base_time = max(self.single_joint_move_time(a - b) for a, b in zip(q1, q2))

        friction_factor = 1.0 + 0.15 * self.friction_coefficient
        damping_factor = 1.0 + 0.10 * self.damping_factor
        payload_factor = 1.0 + 0.03 * max(self.payload_mass - 1.0, 0.0)

        return base_time * friction_factor * damping_factor * payload_factor

    def send_trajectory(self):
        if self.sent:
            return

        if self.control_latency > 0:
            self.get_logger().info(f"Applying ControlLatency = {self.control_latency:.3f} s")
            time.sleep(self.control_latency)

        msg = JointTrajectory()
        msg.joint_names = self.joint_names

        t = 1.0
        previous_q = self.waypoints[0][1]

        first = JointTrajectoryPoint()
        first.positions = previous_q
        first.time_from_start.sec = int(t)
        msg.points.append(first)

        cycle_start_t = t

        for cycle in range(self.n_cycles):
            self.get_logger().info(f"Adding cycle {cycle + 1}/{self.n_cycles}")

            for _, q, dwell in self.waypoints[1:]:
                t += self.move_time(previous_q, q)

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

                previous_q = q

            self.commanded_cycle_times.append(t - cycle_start_t)
            cycle_start_t = t

        self.start_time = time.time()
        self.pub.publish(msg)
        self.sent = True

        self.get_logger().info("Pipeline 3 trajectory sent.")
        self.get_logger().info(f"Commanded trajectory duration: {t:.2f} s")
        self.get_logger().info(f"Commanded cycle times: {[round(x, 2) for x in self.commanded_cycle_times]} s")
        self.get_logger().info(f"Recording CSV to: {self.csv_path}")

        self.finish_timer = self.create_timer(t + 2.0, self.finish)

    def joint_error(self, q, target):
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(q, target)))

    def joint_state_cb(self, msg):
        if not self.sent or self.start_time is None:
            return

        elapsed = time.time() - self.start_time
        idx = {name: i for i, name in enumerate(msg.name)}

        try:
            q = [msg.position[idx[j]] for j in self.joint_names]
        except KeyError:
            return

        velocities = []
        efforts = []
        current_proxy = []

        for j in self.joint_names:
            i = idx[j]
            vel = msg.velocity[i] if i < len(msg.velocity) else 0.0
            effort = msg.effort[i] if i < len(msg.effort) else 0.0

            friction_current = self.friction_coefficient * 0.15
            damping_current = self.damping_factor * abs(vel) * 0.10
            payload_current = self.payload_mass * abs(effort) * 0.02
            noise = random.gauss(0.0, self.current_noise_level)

            current = abs(effort) * 0.10 + friction_current + damping_current + payload_current + noise
            current = max(current, 0.0)

            velocities.append(vel)
            efforts.append(effort)
            current_proxy.append(current)

        for j, pos, vel, eff, cur in zip(self.joint_names, q, velocities, efforts, current_proxy):
            self.csv_writer.writerow([elapsed, j, pos, vel, eff, cur])

        self.effort_samples.append(efforts)
        self.current_proxy_samples.append(current_proxy)
        self.position_error_samples.append(self.joint_error(q, self.home))

    def rms_per_joint(self, samples):
        if not samples:
            return [0.0] * 6

        output = []
        for j in range(6):
            vals = [sample[j] for sample in samples]
            output.append(math.sqrt(sum(v * v for v in vals) / len(vals)))
        return output

    def finish(self):
        if not self.sent:
            return

        total_time = sum(self.commanded_cycle_times)
        mean_cycle = statistics.mean(self.commanded_cycle_times)
        std_cycle = statistics.stdev(self.commanded_cycle_times) if len(self.commanded_cycle_times) > 1 else 0.0

        rms_effort = self.rms_per_joint(self.effort_samples)
        rms_current = self.rms_per_joint(self.current_proxy_samples)
        rms_current_mean = statistics.mean(rms_current)

        if self.position_error_samples:
            position_error = math.sqrt(
                sum(e * e for e in self.position_error_samples) / len(self.position_error_samples)
            )
        else:
            position_error = 0.0

        dt = 0.01
        energy_consumption = sum(
            sum(abs(i) for i in sample) * dt
            for sample in self.current_proxy_samples
        )

        kpis = {
            "InputsUsed": {
                "TargetJointPositions": self.target_joint_positions,
                "SpeedScaling": self.speed_scaling,
                "PayloadMass": self.payload_mass,
                "FrictionCoefficient": self.friction_coefficient,
                "CurrentNoiseLevel": self.current_noise_level,
                "ControlLatency": self.control_latency,
                "DampingFactor": self.damping_factor
            },
            "PerformanceKPIs": {
                "CycleTime": mean_cycle,
                "CycleTimes": self.commanded_cycle_times,
                "RMSCurrent": rms_current_mean,
                "RMSCurrentPerJoint": rms_current,
                "EnergyConsumption": energy_consumption,
                "PositionError": position_error
            },
            "Files": {
                "CSV": str(self.csv_path),
                "KPI_JSON": str(self.kpi_path)
            }
        }

        with open(self.kpi_path, "w") as f:
            json.dump(kpis, f, indent=2)

        self.csv_file.close()

        self.get_logger().info("========== PerformanceKPIs ==========")
        self.get_logger().info(f"CycleTime = {mean_cycle:.3f} s")
        self.get_logger().info(f"CycleTimes = {[round(x, 3) for x in self.commanded_cycle_times]} s")
        self.get_logger().info(f"RMSCurrent = {rms_current_mean:.5f} A")
        self.get_logger().info(f"RMSCurrentPerJoint = {[round(x, 5) for x in rms_current]} A")
        self.get_logger().info(f"EnergyConsumption = {energy_consumption:.5f}")
        self.get_logger().info(f"PositionError = {position_error:.6f} rad")
        self.get_logger().info(f"RMSEffortPerJoint = {[round(x, 5) for x in rms_effort]}")
        self.get_logger().info(f"Saved CSV to: {self.csv_path}")
        self.get_logger().info(f"Saved KPI JSON to: {self.kpi_path}")
        self.get_logger().info("====================================")

        rclpy.shutdown()


def main(args=None):
    rclpy.init(args=args)
    node = Pipeline3()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    if not node.csv_file.closed:
        node.csv_file.close()

    node.destroy_node()

    if rclpy.ok():
        rclpy.shutdown()


if __name__ == "__main__":
    main()
