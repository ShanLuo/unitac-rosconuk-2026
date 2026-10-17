"""Lightweight marker-mask adapter based on GenForce's find_marker heuristic.

Unlike the original GenForce production segmentation, this deliberately omits
EfficientSAM refinement. Verify the resulting mask visually before inference.
"""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image


def segment_markers(bgr, contrast_threshold=150, dark_threshold=70,
                    min_area=8, max_area=2000):
    """Return uint8 mono8 mask: white markers, black background."""
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (15, 15), 5)
    # Use signed arithmetic: uint8 subtraction would wrap around.
    contrast = blurred.astype(np.int16) - gray.astype(np.int16) + 128
    hsv_value = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 2]
    mask = np.uint8(((contrast >= contrast_threshold) |
                     (hsv_value < dark_threshold)) * 255)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask)
    result = np.zeros_like(mask)
    for index in range(1, count):
        area = int(stats[index, cv2.CC_STAT_AREA])
        if min_area <= area <= max_area:
            result[labels == index] = 255
    return result


class MarkerSegmentationNode(Node):
    def __init__(self):
        super().__init__('unitac_marker_segmentation')
        self.declare_parameter('input_topic', '/unitac/gelsight/image_raw')
        self.declare_parameter('output_topic', '/unitac/gelsight/marker_image')
        self.declare_parameter('contrast_threshold', 150)
        self.declare_parameter('dark_threshold', 70)
        self.declare_parameter('min_area', 8)
        self.declare_parameter('max_area', 2000)
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(
            Image, self.get_parameter('output_topic').value, 10)
        self.subscription = self.create_subscription(
            Image, self.get_parameter('input_topic').value, self.callback, 10)
        self.get_logger().info('Marker segmentation adapter ready (no robot control)')

    def callback(self, msg):
        try:
            bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            mask = segment_markers(
                bgr,
                self.get_parameter('contrast_threshold').value,
                self.get_parameter('dark_threshold').value,
                self.get_parameter('min_area').value,
                self.get_parameter('max_area').value)
            out = self.bridge.cv2_to_imgmsg(mask, encoding='mono8')
            out.header = msg.header
            self.publisher.publish(out)
        except Exception as exc:
            self.get_logger().error(f'Marker segmentation failed: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = MarkerSegmentationNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
