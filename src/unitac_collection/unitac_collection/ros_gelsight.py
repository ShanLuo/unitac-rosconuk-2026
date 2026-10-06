#!/usr/bin/env python3

import threading
import time

import cv2
import rclpy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image


class ROSGelSight:
    """
    ROS 2 adapter for the UniTac GelSight camera.
    """

    def __init__(
        self,
        node,
        topic="/unitac/gelsight/image_raw",
    ):
        self.node = node
        self.topic = topic

        self.bridge = CvBridge()

        self._lock = threading.Lock()
        self._latest_frame = None
        self._latest_stamp = None
        self._frame_counter = 0

        self.subscription = self.node.create_subscription(
            Image,
            self.topic,
            self._image_callback,
            10,
        )

        self.node.get_logger().info(
            f"Subscribed to GelSight topic: {self.topic}"
        )

    def _image_callback(self, msg):
        frame = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="bgr8",
        )

        with self._lock:
            self._latest_frame = frame.copy()
            self._latest_stamp = (
                int(msg.header.stamp.sec),
                int(msg.header.stamp.nanosec),
            )
            self._frame_counter += 1

    @property
    def frame(self):
        with self._lock:
            if self._latest_frame is None:
                raise RuntimeError(
                    "No GelSight frame has been received yet."
                )

            return self._latest_frame.copy()

    @property
    def stamp(self):
        with self._lock:
            if self._latest_stamp is None:
                raise RuntimeError(
                    "No GelSight frame has been received yet."
                )

            return self._latest_stamp

    @property
    def has_frame(self):
        with self._lock:
            return self._latest_frame is not None

    @property
    def frame_counter(self):
        with self._lock:
            return self._frame_counter

    def wait_for_new_frame(
        self,
        after_counter=None,
        timeout=2.0,
    ):
        """
        Wait until a GelSight frame newer than after_counter arrives.

        Returns:
            frame, stamp, frame_counter
        """

        if after_counter is None:
            after_counter = self.frame_counter

        start_time = time.time()

        while time.time() - start_time < timeout:

            rclpy.spin_once(
                self.node,
                timeout_sec=0.05,
            )

            with self._lock:
                if (
                    self._latest_frame is not None
                    and self._frame_counter > after_counter
                ):
                    return (
                        self._latest_frame.copy(),
                        self._latest_stamp,
                        self._frame_counter,
                    )

        raise RuntimeError(
            f"No new GelSight frame received within {timeout:.1f} seconds"
        )

    def save(self, filename):
        frame = self.frame

        success = cv2.imwrite(
            str(filename),
            frame,
        )

        if not success:
            raise RuntimeError(
                f"Failed to save GelSight image: {filename}"
            )

        return filename