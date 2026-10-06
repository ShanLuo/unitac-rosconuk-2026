#!/usr/bin/env python3

import math
import time
from pathlib import Path

import numpy as np
import rclpy
from rclpy.node import Node

from unitac_collection.genforce_capture import GenForceCapture
from unitac_collection.genforce_collection import (
    SAMPLE_SETTLE_TIME,
    run_phase,
)
from unitac_collection.genforce_trajectory import (
    ANGLE_N,
    BASE_POINTS,
    DEPTHS,
    NORMAL_SAMPLES,
    RZ,
    SAFE_Z,
    SHEAR_RADIUS,
    SHEAR_SAMPLES,
)
from unitac_collection.ros_gelsight import ROSGelSight
from unitac_collection.ros_robot import ROSRobot


SAFE_SETTLE_TIME = 0.5


class GenForceCollectorNode(Node):

    def __init__(self):
        super().__init__("unitac_genforce_collector")

        # -------------------------------------------------------------
        # General parameters
        # -------------------------------------------------------------

        self.declare_parameter("execute_motion", False)

        self.declare_parameter(
            "output_dir",
            "/ros2_ws/test_output/genforce_ros",
        )

        # -------------------------------------------------------------
        # Validated trajectory parameters
        # -------------------------------------------------------------

        self.declare_parameter("rz", float(RZ))
        self.declare_parameter("safe_z", float(SAFE_Z))

        self.declare_parameter(
            "depths",
            [float(v) for v in DEPTHS],
        )

        self.declare_parameter(
            "shear_radius",
            float(SHEAR_RADIUS),
        )

        self.declare_parameter(
            "angle_n",
            int(ANGLE_N),
        )

        self.declare_parameter(
            "normal_samples",
            int(NORMAL_SAMPLES),
        )

        self.declare_parameter(
            "shear_samples",
            int(SHEAR_SAMPLES),
        )

        self.declare_parameter(
            "sample_settle_time",
            float(SAMPLE_SETTLE_TIME),
        )

        self.declare_parameter(
            "safe_settle_time",
            float(SAFE_SETTLE_TIME),
        )

        # ROS 2 parameters do not directly represent our list of
        # (x, y) tuples, so store it flattened.
        default_base_points = [
            float(value)
            for point in BASE_POINTS
            for value in point
        ]

        self.declare_parameter(
            "base_points",
            default_base_points,
        )

        # -------------------------------------------------------------
        # Read parameters
        # -------------------------------------------------------------

        self.execute_motion = bool(
            self.get_parameter("execute_motion").value
        )

        self.output_dir = Path(
            self.get_parameter("output_dir").value
        )

        self.rz = float(
            self.get_parameter("rz").value
        )

        self.safe_z = float(
            self.get_parameter("safe_z").value
        )

        self.depths = [
            float(v)
            for v in self.get_parameter("depths").value
        ]

        self.shear_radius = float(
            self.get_parameter("shear_radius").value
        )

        self.angle_n = int(
            self.get_parameter("angle_n").value
        )

        self.normal_samples = int(
            self.get_parameter("normal_samples").value
        )

        self.shear_samples = int(
            self.get_parameter("shear_samples").value
        )

        self.sample_settle_time = float(
            self.get_parameter("sample_settle_time").value
        )

        self.safe_settle_time = float(
            self.get_parameter("safe_settle_time").value
        )

        flat_base_points = [
            float(v)
            for v in self.get_parameter("base_points").value
        ]

        if len(flat_base_points) % 2 != 0:
            raise ValueError(
                "base_points must contain an even number of values: "
                "[x0, y0, x1, y1, ...]"
            )

        self.base_points = [
            (
                flat_base_points[i],
                flat_base_points[i + 1],
            )
            for i in range(0, len(flat_base_points), 2)
        ]

        # -------------------------------------------------------------
        # Validate before any hardware connection
        # -------------------------------------------------------------

        if not self.base_points:
            raise ValueError("base_points must not be empty")

        if not self.depths:
            raise ValueError("depths must not be empty")

        if self.angle_n < 1:
            raise ValueError("angle_n must be >= 1")

        if self.shear_radius < 0.0:
            raise ValueError("shear_radius must be >= 0")

        if self.normal_samples < 1:
            raise ValueError("normal_samples must be >= 1")

        if self.shear_samples < 1:
            raise ValueError("shear_samples must be >= 1")

        if self.sample_settle_time < 0.0:
            raise ValueError(
                "sample_settle_time must be >= 0"
            )

        if self.safe_settle_time < 0.0:
            raise ValueError(
                "safe_settle_time must be >= 0"
            )

    # -----------------------------------------------------------------
    # Pose helper using the configured RZ
    # -----------------------------------------------------------------

    def pose(self, x, y, z):
        return np.array(
            [
                x,
                y,
                z,
                0.0,
                0.0,
                self.rz,
            ],
            dtype=float,
        )

    # -----------------------------------------------------------------
    # Dry-run plan
    # -----------------------------------------------------------------

    def print_plan(self):

        total_cycles = (
            len(self.base_points)
            * len(self.depths)
            * self.angle_n
        )

        samples_per_cycle = (
            2 * self.normal_samples
            + 2 * self.shear_samples
        )

        total_samples = (
            total_cycles
            * samples_per_cycle
        )

        self.get_logger().info(
            "GenForce experiment plan"
        )

        self.get_logger().info(
            f"BASE_POINTS={self.base_points}"
        )

        self.get_logger().info(
            f"DEPTHS={self.depths}"
        )

        self.get_logger().info(
            f"ANGLE_N={self.angle_n}"
        )

        self.get_logger().info(
            f"SHEAR_RADIUS={self.shear_radius} mm"
        )

        self.get_logger().info(
            f"SAFE_Z={self.safe_z} mm"
        )

        self.get_logger().info(
            f"RZ={self.rz} deg"
        )

        self.get_logger().info(
            f"NORMAL_SAMPLES={self.normal_samples}"
        )

        self.get_logger().info(
            f"SHEAR_SAMPLES={self.shear_samples}"
        )

        self.get_logger().info(
            f"SAMPLE_SETTLE_TIME="
            f"{self.sample_settle_time} s"
        )

        self.get_logger().info(
            f"SAFE_SETTLE_TIME="
            f"{self.safe_settle_time} s"
        )

        self.get_logger().info(
            f"Cycles: {total_cycles}"
        )

        self.get_logger().info(
            f"Trajectory samples per cycle: "
            f"{samples_per_cycle}"
        )

        self.get_logger().info(
            f"Total trajectory samples: "
            f"{total_samples}"
        )

        self.get_logger().info(
            "Plus 1 reference image"
        )

        self.get_logger().info(
            f"Expected PNG count: "
            f"{total_samples + 1}"
        )

    # -----------------------------------------------------------------
    # Collection
    # -----------------------------------------------------------------

    def run(self):

        if not self.execute_motion:

            self.get_logger().info(
                "SAFE MODE: execute_motion=false"
            )

            self.get_logger().info(
                "No MG400 connection will be made."
            )

            self.get_logger().info(
                "No GelSight connection will be made."
            )

            self.print_plan()
            return

        self.get_logger().warn(
            "PHYSICAL EXECUTION ENABLED"
        )

        robot = ROSRobot(self)
        gelsight = ROSGelSight(self)

        self.get_logger().info(
            "Waiting for first GelSight frame..."
        )

        while not gelsight.has_frame:
            rclpy.spin_once(
                self,
                timeout_sec=0.1,
            )

        capture = GenForceCapture(
            gelsight=gelsight,
            output_dir=self.output_dir,
        )

        try:
            # Initial safe move.
            safe = self.pose(
                0.0,
                0.0,
                self.safe_z,
            )

            robot.move_linear(safe)
            time.sleep(self.safe_settle_time)

            # Reference image.
            reference_target = safe.copy()
            reference_actual = robot.pose

            reference_id = capture.capture(
                phase="reference",
                frame_idx=0,
                progress=0.0,
                target_pose=reference_target,
                actual_pose=reference_actual,
            )

            self.get_logger().info(
                f"Reference captured: "
                f"sample_id={reference_id}"
            )

            # Experiment hierarchy.
            for base_idx, (base_x, base_y) in enumerate(
                self.base_points
            ):

                self.get_logger().info(
                    f"=== Base {base_idx}: "
                    f"({base_x}, {base_y}) ==="
                )

                base_safe = self.pose(
                    base_x,
                    base_y,
                    self.safe_z,
                )

                robot.move_linear(base_safe)
                time.sleep(self.safe_settle_time)

                for depth_idx, depth in enumerate(
                    self.depths
                ):

                    center = self.pose(
                        base_x,
                        base_y,
                        -depth,
                    )

                    for angle_idx in range(
                        self.angle_n
                    ):

                        angle_deg = (
                            360.0
                            * angle_idx
                            / self.angle_n
                        )

                        theta = math.radians(
                            angle_deg
                        )

                        dx = (
                            self.shear_radius
                            * math.cos(theta)
                        )

                        dy = (
                            self.shear_radius
                            * math.sin(theta)
                        )

                        shear = self.pose(
                            base_x + dx,
                            base_y + dy,
                            -depth,
                        )

                        self.get_logger().info(
                            f"Cycle: "
                            f"base={base_idx}, "
                            f"depth={depth_idx}, "
                            f"angle={angle_idx} "
                            f"({angle_deg:.1f} deg)"
                        )

                        run_phase(
                            robot=robot,
                            phase="normal_inc",
                            start_pose=base_safe,
                            end_pose=center,
                            n_samples=self.normal_samples,
                            capture_fn=capture.capture,
                            settle_time=self.sample_settle_time,
                        )

                        run_phase(
                            robot=robot,
                            phase="shear_inc",
                            start_pose=center,
                            end_pose=shear,
                            n_samples=self.shear_samples,
                            capture_fn=capture.capture,
                            settle_time=self.sample_settle_time,
                        )

                        run_phase(
                            robot=robot,
                            phase="shear_dec",
                            start_pose=shear,
                            end_pose=center,
                            n_samples=self.shear_samples,
                            capture_fn=capture.capture,
                            settle_time=self.sample_settle_time,
                        )

                        run_phase(
                            robot=robot,
                            phase="normal_dec",
                            start_pose=center,
                            end_pose=base_safe,
                            n_samples=self.normal_samples,
                            capture_fn=capture.capture,
                            settle_time=self.sample_settle_time,
                        )

                        # Explicit return to safe position.
                        robot.move_linear(base_safe)
                        time.sleep(
                            self.safe_settle_time
                        )

            self.get_logger().info(
                "GenForce collection completed"
            )

            self.get_logger().info(
                f"Samples written: "
                f"{capture.sample_id}"
            )

            self.get_logger().info(
                f"Output: {self.output_dir}"
            )

        finally:
            capture.close()


def main(args=None):

    rclpy.init(args=args)

    node = GenForceCollectorNode()

    try:
        node.run()

    finally:
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()