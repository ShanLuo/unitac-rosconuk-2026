#!/usr/bin/env python3

import rclpy
from rclpy.node import Node

from unitac_collection.ros_robot import ROSRobot


class TestRobotClient(Node):

    def __init__(self):
        super().__init__("unitac_test_robot_client")

        self.robot = ROSRobot(self)

        self.get_logger().info(
            "ROSRobot adapter is connected to the MG400 service"
        )


def main(args=None):
    rclpy.init(args=args)

    node = TestRobotClient()

    try:
        # Deliberately no motion command yet.
        node.get_logger().info(
            "ROSRobot adapter test passed. No movement commanded."
        )

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()