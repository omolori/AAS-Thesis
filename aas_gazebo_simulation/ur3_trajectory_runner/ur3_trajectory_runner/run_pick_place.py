import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class UR3PickPlaceRunner(Node):
    def __init__(self):
        super().__init__("ur3_pick_place_runner")

        self.publisher = self.create_publisher(
            JointTrajectory,
            "/joint_trajectory_controller/joint_trajectory",
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

        self.speed_rad_s = 0.2
        self.dwell_s = 0.5
        self.n_cycles = 3

        self.waypoints = [
            ("home",      [-1.4561, -1.6660, -0.2774, -2.0748,  1.6275, -0.1098], 0.0),
            ("pre_pick",  [-1.3320, -1.8503, -1.7179, -1.1217,  1.5566,  0.2009], 0.0),
            ("pick",      [-1.3428, -2.1051, -1.9055, -0.6799,  1.5585,  0.1948], 0.5),
            ("pre_pick",  [-1.3320, -1.8503, -1.7179, -1.1217,  1.5566,  0.2009], 0.0),
            ("pre_place", [-1.1077, -1.9063, -1.7017, -1.0908,  1.6046,  0.4865], 0.0),
            ("place",     [-1.1074, -2.1273, -1.8539, -0.7185,  1.6065,  0.4822], 0.5),
            ("pre_place", [-1.1077, -1.9063, -1.7017, -1.0908,  1.6046,  0.4865], 0.0),
            ("home",      [-1.4561, -1.6660, -0.2774, -2.0748,  1.6275, -0.1098], 0.0),
        ]

        self.timer = self.create_timer(2.0, self.send_trajectory)
        self.sent = False

    def estimate_move_time(self, q1, q2):
        max_delta = max(abs(a - b) for a, b in zip(q1, q2))
        return max(max_delta / self.speed_rad_s, 1.0)

    def send_trajectory(self):
        if self.sent:
            return

        msg = JointTrajectory()
        msg.joint_names = self.joint_names

        current_time = 0.0
        previous_q = self.waypoints[0][1]

        point = JointTrajectoryPoint()
        point.positions = previous_q
        point.time_from_start.sec = 1
        msg.points.append(point)
        current_time = 1.0

        for cycle in range(self.n_cycles):
            self.get_logger().info(f"Adding cycle {cycle + 1}/{self.n_cycles}")

            for name, q, dwell in self.waypoints[1:]:
                move_time = self.estimate_move_time(previous_q, q)
                current_time += move_time

                point = JointTrajectoryPoint()
                point.positions = q
                point.time_from_start.sec = int(current_time)
                point.time_from_start.nanosec = int((current_time % 1) * 1e9)
                msg.points.append(point)

                if dwell > 0:
                    current_time += dwell
                    dwell_point = JointTrajectoryPoint()
                    dwell_point.positions = q
                    dwell_point.time_from_start.sec = int(current_time)
                    dwell_point.time_from_start.nanosec = int((current_time % 1) * 1e9)
                    msg.points.append(dwell_point)

                previous_q = q

        self.publisher.publish(msg)
        self.get_logger().info("Pick-and-place trajectory sent.")
        self.sent = True


def main(args=None):
    rclpy.init(args=args)
    node = UR3PickPlaceRunner()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
