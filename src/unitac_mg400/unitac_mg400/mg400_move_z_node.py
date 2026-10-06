#!/usr/bin/env python3

import sys

import rclpy
from rclpy.node import Node

from std_msgs.msg import Float64
from std_msgs.msg import Float64MultiArray

from unitac_interfaces.srv import MoveLinear


# Existing CRI repository is mounted read-only in Docker.
CRI_PATH = "/common-robot-interface"

if CRI_PATH not in sys.path:
    sys.path.insert(0, CRI_PATH)

from cri.robot import SyncRobot
from cri.dobot.mg400_controller import MG400Controller


# ---------------------------------------------------------------------
# Validated UniTac / GenForce MG400 defaults
#
# These defaults reproduce the configuration used for the validated
# 1761-sample physical GenForce collection.
# ---------------------------------------------------------------------

DEFAULT_ROBOT_IP = "192.168.1.6"

DEFAULT_WORK_FRAME = [
    266.19491577,
    41.40279007,
    -115.76152039,
    0.0,
    0.0,
    0.0,
]

DEFAULT_TCP = [
    0.0,
    0.0,
    -50.0,
    0.0,
    0.0,
    0.0,
]


class MG400MoveNode(Node):

    def __init__(self):
        super().__init__("mg400_move_z_node")

        # -------------------------------------------------------------
        # Parameters
        # -------------------------------------------------------------

        self.declare_parameter("robot_ip", DEFAULT_ROBOT_IP)
        self.declare_parameter("speed", 10.0)

        self.declare_parameter(
            "work_frame",
            DEFAULT_WORK_FRAME,
        )

        self.declare_parameter(
            "tcp",
            DEFAULT_TCP,
        )

        self.declare_parameter("max_z_step_mm", 2.0)
        self.declare_parameter("publish_rate", 10.0)

        self.robot_ip = (
            self.get_parameter("robot_ip")
            .get_parameter_value()
            .string_value
        )

        self.speed = (
            self.get_parameter("speed")
            .get_parameter_value()
            .double_value
        )

        self.work_frame = [
            float(value)
            for value in self.get_parameter("work_frame").value
        ]

        self.tcp = [
            float(value)
            for value in self.get_parameter("tcp").value
        ]

        self.max_z_step = (
            self.get_parameter("max_z_step_mm")
            .get_parameter_value()
            .double_value
        )

        self.publish_rate = (
            self.get_parameter("publish_rate")
            .get_parameter_value()
            .double_value
        )

        # -------------------------------------------------------------
        # Validate parameters before connecting to hardware
        # -------------------------------------------------------------

        if not self.robot_ip:
            raise ValueError("robot_ip must not be empty")

        if not 1.0 <= self.speed <= 100.0:
            raise ValueError(
                f"speed must be between 1 and 100; got {self.speed}"
            )

        if len(self.work_frame) != 6:
            raise ValueError(
                "work_frame must contain exactly six values: "
                "[x, y, z, rx, ry, rz]"
            )

        if len(self.tcp) != 6:
            raise ValueError(
                "tcp must contain exactly six values: "
                "[x, y, z, rx, ry, rz]"
            )

        if self.max_z_step <= 0.0:
            raise ValueError(
                f"max_z_step_mm must be > 0; got {self.max_z_step}"
            )

        if self.publish_rate <= 0.0:
            raise ValueError(
                f"publish_rate must be > 0; got {self.publish_rate}"
            )

        # -------------------------------------------------------------
        # Connect to MG400
        #
        # IMPORTANT:
        # This node is the single owner of the MG400 connection.
        # Do not run another CRI/MG400 process simultaneously.
        # -------------------------------------------------------------

        self.get_logger().info(
            f"Connecting to MG400 at {self.robot_ip}..."
        )

        controller = MG400Controller(ip=self.robot_ip)
        self.robot = SyncRobot(controller)

        self.robot.coord_frame = self.work_frame
        self.robot.tcp = self.tcp

        self.get_logger().info("MG400 connection established")
        self.get_logger().info(
            f"Work frame: {self.work_frame}"
        )
        self.get_logger().info(
            f"TCP: {self.tcp}"
        )

        self.robot.speed = self.speed

        self.get_logger().info(
            f"MG400 global speed set to {self.speed:.1f}%"
        )

        self.moving = False

        # -------------------------------------------------------------
        # Pose publisher
        # -------------------------------------------------------------

        self.pose_publisher = self.create_publisher(
            Float64MultiArray,
            "/unitac/mg400/pose",
            10,
        )

        self.pose_timer = self.create_timer(
            1.0 / self.publish_rate,
            self.pose_timer_callback,
        )

        # -------------------------------------------------------------
        # Temporary relative-Z topic
        # -------------------------------------------------------------

        self.z_subscription = self.create_subscription(
            Float64,
            "/unitac/mg400/move_z",
            self.move_z_callback,
            10,
        )

        # -------------------------------------------------------------
        # Temporary absolute Cartesian topic
        # -------------------------------------------------------------

        self.linear_subscription = self.create_subscription(
            Float64MultiArray,
            "/unitac/mg400/move_linear",
            self.move_linear_callback,
            10,
        )

        # -------------------------------------------------------------
        # Blocking Cartesian service
        # -------------------------------------------------------------

        self.move_linear_service = self.create_service(
            MoveLinear,
            "/unitac/mg400/move_linear_srv",
            self.move_linear_service_callback,
        )

        self.get_logger().info(
            "Publishing calibrated pose on /unitac/mg400/pose"
        )

        self.get_logger().info(
            "Ready for relative Z commands on /unitac/mg400/move_z"
        )

        self.get_logger().info(
            f"Maximum allowed Z step: +/-{self.max_z_step:.2f} mm"
        )

        self.get_logger().info(
            "Ready for Cartesian topic commands on "
            "/unitac/mg400/move_linear"
        )

        self.get_logger().info(
            "Ready for blocking Cartesian service on "
            "/unitac/mg400/move_linear_srv"
        )

    # -----------------------------------------------------------------
    # Pose
    # -----------------------------------------------------------------

    def get_actual_pose(self):
        return [
            float(value)
            for value in self.robot.pose
        ]

    def publish_pose(self, pose):
        msg = Float64MultiArray()
        msg.data = [float(value) for value in pose]
        self.pose_publisher.publish(msg)

    def pose_timer_callback(self):
        if self.moving:
            return

        try:
            self.publish_pose(self.get_actual_pose())

        except Exception as exc:
            self.get_logger().error(
                f"Failed to read MG400 pose: {exc}"
            )

    # -----------------------------------------------------------------
    # Shared blocking Cartesian execution
    # -----------------------------------------------------------------

    def execute_linear_move(self, target_pose):
        """
        Execute one blocking Cartesian move.

        target_pose:
            [x, y, z, rx, ry, rz]
            expressed in the configured UniTac work frame / TCP.

        Returns:
            actual_pose
        """

        target_pose = [
            float(value)
            for value in target_pose
        ]

        current_pose = self.get_actual_pose()

        self.get_logger().info(
            "Current work-frame pose: "
            f"{[round(v, 4) for v in current_pose]}"
        )

        self.get_logger().info(
            "Target work-frame pose: "
            f"{[round(v, 4) for v in target_pose]}"
        )

        self.robot.move_linear(target_pose)

        actual_pose = self.get_actual_pose()

        error = [
            actual_pose[i] - target_pose[i]
            for i in range(6)
        ]

        self.get_logger().info("Movement completed")

        self.get_logger().info(
            "Actual work-frame pose: "
            f"{[round(v, 4) for v in actual_pose]}"
        )

        self.get_logger().info(
            "Target error [x,y,z,rx,ry,rz]: "
            f"{[round(v, 4) for v in error]}"
        )

        self.publish_pose(actual_pose)

        return actual_pose

    # -----------------------------------------------------------------
    # Blocking MoveLinear service
    # -----------------------------------------------------------------

    def move_linear_service_callback(self, request, response):

        if self.moving:
            response.success = False
            response.actual_pose = [0.0] * 6
            response.message = "Robot is already executing another move"

            self.get_logger().warning(response.message)
            return response

        target_pose = [
            float(value)
            for value in request.target_pose
        ]

        self.get_logger().info(
            "MoveLinear service request received: "
            f"{[round(v, 4) for v in target_pose]}"
        )

        self.moving = True

        try:
            actual_pose = self.execute_linear_move(target_pose)

            response.success = True
            response.actual_pose = actual_pose
            response.message = "Movement completed"

        except Exception as exc:
            self.get_logger().error(
                f"MoveLinear service failed: {exc}"
            )

            response.success = False

            try:
                response.actual_pose = self.get_actual_pose()
            except Exception:
                response.actual_pose = [0.0] * 6

            response.message = str(exc)

        finally:
            self.moving = False

        return response

    # -----------------------------------------------------------------
    # Temporary absolute Cartesian topic
    # -----------------------------------------------------------------

    def move_linear_callback(self, msg):

        if self.moving:
            self.get_logger().warning(
                "Robot is already moving; Cartesian command ignored"
            )
            return

        if len(msg.data) != 6:
            self.get_logger().error(
                "move_linear requires exactly six values: "
                "[x, y, z, rx, ry, rz]"
            )
            return

        target_pose = [
            float(value)
            for value in msg.data
        ]

        self.get_logger().info(
            "Requested Cartesian topic target: "
            f"{[round(v, 4) for v in target_pose]}"
        )

        self.moving = True

        try:
            self.execute_linear_move(target_pose)

        except Exception as exc:
            self.get_logger().error(
                f"Cartesian movement failed: {exc}"
            )

        finally:
            self.moving = False

    # -----------------------------------------------------------------
    # Existing relative-Z topic
    # -----------------------------------------------------------------

    def move_z_callback(self, msg):

        if self.moving:
            self.get_logger().warning(
                "Robot is already moving; Z command ignored"
            )
            return

        dz = float(msg.data)

        if abs(dz) > self.max_z_step:
            self.get_logger().error(
                f"Requested Z step {dz:+.3f} mm exceeds "
                f"maximum allowed +/-{self.max_z_step:.3f} mm"
            )
            return

        self.moving = True

        try:
            current_pose = self.get_actual_pose()

            target_pose = current_pose.copy()
            target_pose[2] += dz

            self.get_logger().info(
                f"Requested relative Z move: {dz:+.3f} mm"
            )

            actual_pose = self.execute_linear_move(target_pose)

            actual_dz = (
                actual_pose[2] - current_pose[2]
            )

            self.get_logger().info(
                f"Actual Z displacement: {actual_dz:+.3f} mm"
            )

        except Exception as exc:
            self.get_logger().error(
                f"Relative Z movement failed: {exc}"
            )

        finally:
            self.moving = False


def main(args=None):

    rclpy.init(args=args)

    node = None

    try:
        node = MG400MoveNode()
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        # Deliberately do NOT call robot.close().
        #
        # The current CRI implementation performs Sync(),
        # ClearError(), and DisableRobot() during close(), so it is not
        # appropriate as passive ROS node cleanup.
        if node is not None:
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()