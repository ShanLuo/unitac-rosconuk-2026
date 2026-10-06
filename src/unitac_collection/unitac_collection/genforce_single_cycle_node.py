import os
import time

import rclpy
from rclpy.node import Node

from unitac_collection.ros_robot import ROSRobot
from unitac_collection.ros_gelsight import ROSGelSight
from unitac_collection.genforce_capture import GenForceCapture
from unitac_collection.genforce_collection import run_phase
from unitac_collection.genforce_trajectory import (
    pose,
    SAFE_Z,
    NORMAL_SAMPLES,
    SHEAR_SAMPLES,
    SHEAR_RADIUS,
)


class GenForceSingleCycle(Node):

    def __init__(self):
        super().__init__("unitac_genforce_single_cycle")


def main(args=None):
    rclpy.init(args=args)
    node = GenForceSingleCycle()

    # Deliberately fixed for the first physical validation.
    base_x = 0.0
    base_y = 0.0
    depth = 0.5
    angle_idx = 0

    output_dir = "/ros2_ws/test_output/genforce_single_cycle"

    robot = None
    capture = None

    try:
        node.get_logger().info(
            "PHYSICAL SINGLE-CYCLE TEST: "
            "base=(0,0), depth=0.5 mm, angle=0 deg"
        )

        robot = ROSRobot(node)
        gelsight = ROSGelSight(node)

        node.get_logger().info("Waiting for first GelSight frame...")

        if not gelsight.wait_for_new_frame(timeout=5.0):
            raise RuntimeError("No GelSight frame received")

        capture = GenForceCapture(gelsight, output_dir)

        base_safe = pose(base_x, base_y, SAFE_Z)
        base_contact = pose(base_x, base_y, -depth)

        shear_target = pose(
            base_x + SHEAR_RADIUS,
            base_y,
            -depth,
        )

        # Start from a known safe pose.
        node.get_logger().info(
            f"Moving to SAFE pose: {base_safe.tolist()}"
        )
        robot.move_linear(base_safe)
        time.sleep(0.5)

        node.get_logger().info("Starting normal_inc")
        run_phase(
            robot,
            "normal_inc",
            base_safe,
            base_contact,
            NORMAL_SAMPLES,
            capture.capture,
        )

        node.get_logger().info("Starting shear_inc")
        run_phase(
            robot,
            "shear_inc",
            base_contact,
            shear_target,
            SHEAR_SAMPLES,
            capture.capture,
        )

        node.get_logger().info("Starting shear_dec")
        run_phase(
            robot,
            "shear_dec",
            shear_target,
            base_contact,
            SHEAR_SAMPLES,
            capture.capture,
        )

        node.get_logger().info("Starting normal_dec")
        run_phase(
            robot,
            "normal_dec",
            base_contact,
            base_safe,
            NORMAL_SAMPLES,
            capture.capture,
        )

        # Explicit final safe pose.
        node.get_logger().info("Returning explicitly to SAFE pose")
        robot.move_linear(base_safe)
        time.sleep(0.5)

        node.get_logger().info(
            "SINGLE-CYCLE TEST COMPLETE: 44 trajectory samples expected"
        )
        node.get_logger().info(
            f"Output: {output_dir}"
        )

    except Exception as exc:
        node.get_logger().error(f"Single-cycle test failed: {exc}")

        # Deliberately DO NOT command recovery motion automatically.
        # We inspect the robot state first if anything fails.
        raise

    finally:
        if capture is not None:
            capture.close()

        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()