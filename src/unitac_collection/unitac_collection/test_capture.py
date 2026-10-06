#!/usr/bin/env python3

import shutil
from pathlib import Path

import rclpy
from rclpy.node import Node

from unitac_collection.ros_gelsight import ROSGelSight
from unitac_collection.genforce_capture import GenForceCapture


OUTPUT_DIR = Path(
    "/ros2_ws/test_output/genforce_capture_test"
)


class TestCaptureNode(Node):

    def __init__(self):
        super().__init__("unitac_test_capture")

        self.gelsight = ROSGelSight(self)


def main(args=None):
    rclpy.init(args=args)

    node = TestCaptureNode()
    capture = None

    try:
        # Start with a clean test directory.
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)

        node.get_logger().info(
            "Waiting for initial GelSight frame..."
        )

        while not node.gelsight.has_frame:
            rclpy.spin_once(
                node,
                timeout_sec=0.1,
            )

        node.get_logger().info(
            "Initial GelSight frame received"
        )

        capture = GenForceCapture(
            gelsight=node.gelsight,
            output_dir=OUTPUT_DIR,
        )

        # Synthetic metadata only.
        # No MG400 is connected or commanded.
        target_pose = [
            0.0,
            0.0,
            1.0,
            0.0,
            0.0,
            -31.3,
        ]

        actual_pose = [
            0.01,
            -0.01,
            1.002,
            0.0,
            0.0,
            -31.29,
        ]

        node.get_logger().info(
            "Capturing synchronized GelSight test sample..."
        )

        sample_id = capture.capture(
            phase="test_phase",
            frame_idx=0,
            progress=0.0,
            target_pose=target_pose,
            actual_pose=actual_pose,
        )

        node.get_logger().info(
            f"Captured sample_id={sample_id}"
        )

        node.get_logger().info(
            f"Test data saved to: {OUTPUT_DIR}"
        )

    finally:
        if capture is not None:
            capture.close()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()