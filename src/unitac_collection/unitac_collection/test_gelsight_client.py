#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node

from unitac_collection.ros_gelsight import ROSGelSight


class TestGelSightClient(Node):

    def __init__(self):
        super().__init__("unitac_test_gelsight_client")

        self.gelsight = ROSGelSight(self)


def main(args=None):
    rclpy.init(args=args)

    node = TestGelSightClient()

    try:
        node.get_logger().info(
            "Waiting for first GelSight frame..."
        )

        timeout = 10.0
        start_time = time.time()

        while (
            not node.gelsight.has_frame
            and time.time() - start_time < timeout
        ):
            rclpy.spin_once(
                node,
                timeout_sec=0.1,
            )

        if not node.gelsight.has_frame:
            raise RuntimeError(
                "No GelSight frame received within 10 seconds"
            )

        frame = node.gelsight.frame
        stamp = node.gelsight.stamp

        node.get_logger().info(
            f"GelSight frame received: "
            f"shape={frame.shape}, "
            f"stamp={stamp}"
        )

        output = "/ros2_ws/test_output/gelsight_adapter_test.png"

        node.gelsight.save(output)

        node.get_logger().info(
            f"Saved GelSight frame to: {output}"
        )

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()