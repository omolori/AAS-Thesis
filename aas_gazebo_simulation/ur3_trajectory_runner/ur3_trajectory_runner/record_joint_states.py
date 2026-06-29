import csv
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class JointStateRecorder(Node):
    def __init__(self):
        super().__init__("joint_state_recorder")

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.output_path = Path.home() / "ros2_ws" / f"gazebo_joint_states_{timestamp}.csv"

        self.file = open(self.output_path, "w", newline="")
        self.writer = csv.writer(self.file)

        self.writer.writerow([
            "time_s",
            "joint_name",
            "position_rad",
            "velocity_rad_s",
            "effort"
        ])

        self.start_time = None

        self.subscriber = self.create_subscription(
            JointState,
            "/joint_states",
            self.callback,
            10
        )

        self.get_logger().info(f"Recording /joint_states to {self.output_path}")

    def callback(self, msg):
        now = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9

        if self.start_time is None:
            self.start_time = now

        t = now - self.start_time

        for i, name in enumerate(msg.name):
            position = msg.position[i] if i < len(msg.position) else ""
            velocity = msg.velocity[i] if i < len(msg.velocity) else ""
            effort = msg.effort[i] if i < len(msg.effort) else ""

            self.writer.writerow([t, name, position, velocity, effort])

    def destroy_node(self):
        self.file.close()
        self.get_logger().info(f"Saved CSV to {self.output_path}")
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = JointStateRecorder()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
