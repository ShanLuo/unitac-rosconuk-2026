import sys

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

# Development mount of the existing validated CRI implementation.
CRI_PATH = '/common-robot-interface'
if CRI_PATH not in sys.path:
    sys.path.insert(0, CRI_PATH)

from cri.robot import SyncRobot
from cri.dobot.mg400_controller import MG400Controller
from cri.transforms import quat2euler


class MG400StateNode(Node):

    def __init__(self):
        super().__init__('mg400_state_node')

        # ------------------------------------------------------------
        # ROS parameters
        # ------------------------------------------------------------
        self.declare_parameter('robot_ip', '192.168.1.6')
        self.declare_parameter('publish_rate', 10.0)

        # Validated UniTac / GenForce tactile work frame.
        self.declare_parameter(
            'work_frame',
            [
                265.36090088,
                40.82979202,
                -114.89134216,
                0.0,
                0.0,
                0.0,
            ]
        )

        # Validated TCP used by the tactile collection pipeline.
        self.declare_parameter(
            'tcp',
            [
                0.0,
                0.0,
                -50.0,
                0.0,
                0.0,
                0.0,
            ]
        )

        robot_ip = (
            self.get_parameter('robot_ip')
            .get_parameter_value()
            .string_value
        )

        publish_rate = (
            self.get_parameter('publish_rate')
            .get_parameter_value()
            .double_value
        )

        work_frame = list(
            self.get_parameter('work_frame')
            .get_parameter_value()
            .double_array_value
        )

        tcp = list(
            self.get_parameter('tcp')
            .get_parameter_value()
            .double_array_value
        )

        # ------------------------------------------------------------
        # Publishers
        # ------------------------------------------------------------

        # Raw MG400 pose in the robot base frame.
        #
        # Format:
        # [x_mm, y_mm, z_mm, rx_deg, ry_deg, rz_deg]
        self.raw_pose_publisher = self.create_publisher(
            Float64MultiArray,
            '/unitac/mg400/pose_raw',
            10
        )

        # Pose expressed in the calibrated UniTac tactile work frame
        # with the configured TCP applied.
        #
        # Format:
        # [x_mm, y_mm, z_mm, rx_deg, ry_deg, rz_deg]
        self.pose_publisher = self.create_publisher(
            Float64MultiArray,
            '/unitac/mg400/pose',
            10
        )

        # ------------------------------------------------------------
        # Robot connection
        # ------------------------------------------------------------
        self.get_logger().info(
            f'Connecting to MG400 at {robot_ip}...'
        )

        self.robot = SyncRobot(
            MG400Controller(ip=robot_ip)
        )

        self.get_logger().info(
            'MG400 connection established'
        )

        # Keep a reference to the underlying controller so that the
        # untransformed/base-frame pose can also be published.
        self.controller = self.robot.controller

        # Apply the same coordinate frame and TCP used by the
        # validated UniTac / GenForce data-collection pipeline.
        self.robot.coord_frame = work_frame
        self.robot.tcp = tcp

        self.get_logger().info(
            f'Work frame: {work_frame}'
        )

        self.get_logger().info(
            f'TCP: {tcp}'
        )

        # ------------------------------------------------------------
        # Timer
        # ------------------------------------------------------------
        self.timer = self.create_timer(
            1.0 / publish_rate,
            self.publish_pose
        )

    def publish_pose(self):
        try:
            # --------------------------------------------------------
            # Raw/base-frame pose
            # --------------------------------------------------------
            #
            # MG400Controller.pose returns CRI's internal quaternion
            # representation. Convert it back to the Euler format
            # exposed by SyncRobot.
            raw_pose = quat2euler(
                self.controller.pose,
                self.robot.axes
            )

            raw_msg = Float64MultiArray()
            raw_msg.data = [
                float(value)
                for value in raw_pose[:6]
            ]

            self.raw_pose_publisher.publish(raw_msg)

            # --------------------------------------------------------
            # UniTac calibrated work-frame pose
            # --------------------------------------------------------
            work_pose = self.robot.pose

            pose_msg = Float64MultiArray()
            pose_msg.data = [
                float(value)
                for value in work_pose[:6]
            ]

            self.pose_publisher.publish(pose_msg)

        except Exception as exc:
            self.get_logger().error(
                f'Failed to read MG400 pose: {exc}'
            )


def main(args=None):
    rclpy.init(args=args)

    node = MG400StateNode()

    try:
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        # IMPORTANT:
        #
        # Do NOT call robot.close() here.
        #
        # The current CRI MG400Client.close() performs:
        #   Sync()
        #   ClearError()
        #   DisableRobot()
        #
        # This is inappropriate for a read-only ROS state publisher
        # and previously caused shutdown to block.
        #
        # When this process exits, the operating system releases the
        # associated sockets without intentionally changing the robot
        # state.
        node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()