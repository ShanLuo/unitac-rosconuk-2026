import cv2
import rclpy

from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


class GelSightNode(Node):

    def __init__(self):
        super().__init__('gelsight_node')

        # -------------------------------------------------------------
        # Parameters
        # -------------------------------------------------------------

        self.declare_parameter('camera_device', 2)
        self.declare_parameter('frame_id', 'gelsight_camera')
        self.declare_parameter('fps', 30.0)
        self.declare_parameter(
            'image_topic',
            '/unitac/gelsight/image_raw'
        )

        self.camera_device = self.get_parameter(
            'camera_device'
        ).get_parameter_value().integer_value

        self.frame_id = self.get_parameter(
            'frame_id'
        ).get_parameter_value().string_value

        self.fps = self.get_parameter(
            'fps'
        ).get_parameter_value().double_value

        self.image_topic = self.get_parameter(
            'image_topic'
        ).get_parameter_value().string_value

        # -------------------------------------------------------------
        # Validate parameters
        # -------------------------------------------------------------

        if self.camera_device < 0:
            raise ValueError(
                f'camera_device must be >= 0; got {self.camera_device}'
            )

        if self.fps <= 0.0:
            raise ValueError(
                f'fps must be > 0; got {self.fps}'
            )

        if not self.frame_id:
            raise ValueError('frame_id must not be empty')

        if not self.image_topic:
            raise ValueError('image_topic must not be empty')

        # -------------------------------------------------------------
        # ROS publisher
        # -------------------------------------------------------------

        self.publisher_ = self.create_publisher(
            Image,
            self.image_topic,
            10
        )

        # -------------------------------------------------------------
        # Camera
        # -------------------------------------------------------------

        self.bridge = CvBridge()

        self.cap = cv2.VideoCapture(
            self.camera_device
        )

        if not self.cap.isOpened():
            raise RuntimeError(
                'Could not open GelSight camera '
                f'/dev/video{self.camera_device}'
            )

        self.get_logger().info(
            'GelSight camera opened: '
            f'/dev/video{self.camera_device}'
        )

        self.get_logger().info(
            f'Publishing: {self.image_topic}'
        )

        self.get_logger().info(
            f'Frame ID: {self.frame_id}'
        )

        self.get_logger().info(
            f'Requested FPS: {self.fps:.1f}'
        )

        # -------------------------------------------------------------
        # Publishing timer
        # -------------------------------------------------------------

        self.timer = self.create_timer(
            1.0 / self.fps,
            self.publish_frame
        )

    def publish_frame(self):

        success, frame = self.cap.read()

        if not success:
            self.get_logger().warning(
                'Failed to read GelSight frame'
            )
            return

        msg = self.bridge.cv2_to_imgmsg(
            frame,
            encoding='bgr8'
        )

        msg.header.stamp = (
            self.get_clock().now().to_msg()
        )

        msg.header.frame_id = self.frame_id

        self.publisher_.publish(msg)

    def destroy_node(self):

        if self.cap is not None:
            self.cap.release()

        super().destroy_node()


def main(args=None):

    rclpy.init(args=args)

    node = None

    try:
        node = GelSightNode()
        rclpy.spin(node)

    except KeyboardInterrupt:
        pass

    finally:
        if node is not None:
            node.destroy_node()

        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()