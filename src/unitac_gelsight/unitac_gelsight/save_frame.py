import os

import cv2
import rclpy

from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class SaveFrameNode(Node):

    def __init__(self):
        super().__init__('save_frame')

        self.declare_parameter(
            'output_path',
            '/ros2_ws/test_output/gelsight_frame.png'
        )

        self.output_path = (
            self.get_parameter('output_path')
            .get_parameter_value()
            .string_value
        )

        self.bridge = CvBridge()

        self.subscription = self.create_subscription(
            Image,
            '/unitac/gelsight/image_raw',
            self.image_callback,
            10
        )

        self.saved = False

        self.get_logger().info(
            'Waiting for one GelSight image...'
        )

    def image_callback(self, msg):
        if self.saved:
            return

        frame = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding='bgr8'
        )

        os.makedirs(
            os.path.dirname(self.output_path),
            exist_ok=True
        )

        success = cv2.imwrite(
            self.output_path,
            frame
        )

        if not success:
            self.get_logger().error(
                f'Failed to save image: {self.output_path}'
            )
            return

        self.saved = True

        self.get_logger().info(
            f'Saved GelSight image: {self.output_path}'
        )

        self.get_logger().info(
            f'Image size: {frame.shape[1]}x{frame.shape[0]}'
        )


def main(args=None):
    rclpy.init(args=args)

    node = SaveFrameNode()

    while rclpy.ok() and not node.saved:
        rclpy.spin_once(node)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()