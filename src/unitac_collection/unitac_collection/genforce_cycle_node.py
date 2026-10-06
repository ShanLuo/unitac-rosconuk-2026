#!/usr/bin/env python3

import time

import rclpy
from rclpy.node import Node

from unitac_collection.ros_robot import ROSRobot
from unitac_collection.genforce_trajectory import generate_cycle


SAMPLE_SETTLE_TIME = 0.10


class GenForceCycleNode(Node):

    def __init__(self):
        super().__init__("unitac_genforce_cycle")

        self.declare_parameter("base_x", 0.0)
        self.declare_parameter("base_y", 0.0)
        self.declare_parameter("depth", 0.5)
        self.declare_parameter("angle_idx", 0)
        self.declare_parameter("dry_run", True)

        self.base_x = self.get_parameter("base_x").value
        self.base_y = self.get_parameter("base_y").value
        self.depth = self.get_parameter("depth").value
        self.angle_idx = self.get_parameter("angle_idx").value
        self.dry_run = self.get_parameter("dry_run").value

    def execute(self):

        trajectory = generate_cycle(
            base_x=self.base_x,
            base_y=self.base_y,
            depth=self.depth,
            angle_idx=self.angle_idx,
        )

        self.get_logger().info(
            f"Generated {len(trajectory)} GenForce waypoints"
        )

        self.get_logger().info(
            f"base=({self.base_x:.3f}, {self.base_y:.3f}) mm, "
            f"depth={self.depth:.3f} mm, "
            f"angle_idx={self.angle_idx}"
        )

        if self.dry_run:
            self.get_logger().info(
                "DRY RUN: no MG400 connection and no robot movement"
            )

            for waypoint_idx, (phase, frame_idx, target) in enumerate(
                trajectory
            ):
                self.get_logger().info(
                    f"{waypoint_idx:02d} "
                    f"{phase}[{frame_idx:02d}] -> "
                    f"{[round(float(v), 4) for v in target]}"
                )

            return

        # Only connect to MG400 when physical execution is requested.
        robot = ROSRobot(self)

        self.get_logger().info(
            "Beginning physical GenForce cycle"
        )

        current_phase = None

        for waypoint_idx, (phase, frame_idx, target) in enumerate(
            trajectory
        ):
            if phase != current_phase:
                current_phase = phase
                self.get_logger().info(
                    f"--- {phase} ---"
                )

            self.get_logger().info(
                f"Waypoint {waypoint_idx + 1}/{len(trajectory)}: "
                f"{phase}[{frame_idx:02d}]"
            )

            robot.move_linear(target)

            time.sleep(SAMPLE_SETTLE_TIME)

        self.get_logger().info(
            "GenForce cycle completed"
        )


def main(args=None):
    rclpy.init(args=args)

    node = GenForceCycleNode()

    try:
        node.execute()

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()