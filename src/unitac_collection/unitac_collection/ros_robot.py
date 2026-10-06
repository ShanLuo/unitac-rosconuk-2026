import threading

import rclpy
from unitac_interfaces.srv import MoveLinear


class ROSRobot:
    """
    ROS 2 adapter providing a blocking robot.move_linear(target) API.

    This deliberately resembles the subset of SyncRobot used by the
    validated GenForce collector.
    """

    def __init__(
        self,
        node,
        service_name="/unitac/mg400/move_linear_srv",
    ):
        self.node = node

        self.client = self.node.create_client(
            MoveLinear,
            service_name,
        )

        self._pose = None
        self._lock = threading.Lock()

        self.node.get_logger().info(
            f"Waiting for MG400 service: {service_name}"
        )

        while not self.client.wait_for_service(timeout_sec=1.0):
            self.node.get_logger().info(
                "MG400 MoveLinear service not available yet..."
            )

        self.node.get_logger().info(
            "MG400 MoveLinear service available"
        )

    @property
    def pose(self):
        """
        Return the actual pose reported after the most recently
        completed move.
        """
        with self._lock:
            if self._pose is None:
                raise RuntimeError(
                    "No MG400 pose is available yet. "
                    "Execute move_linear() first."
                )

            return self._pose.copy()

    def move_linear(self, target):
        """
        Execute a blocking Cartesian move.

        target:
            [x, y, z, rx, ry, rz]

        Returns only after the MG400 service reports completion.
        """

        target = [float(value) for value in target]

        if len(target) != 6:
            raise ValueError(
                "move_linear target must contain exactly six values: "
                "[x, y, z, rx, ry, rz]"
            )

        request = MoveLinear.Request()
        request.target_pose = target

        self.node.get_logger().info(
            "Requesting MG400 move: "
            f"{[round(v, 4) for v in target]}"
        )

        future = self.client.call_async(request)

        # The collection node itself will not be spinning elsewhere
        # while executing the sequential GenForce trajectory, so spin
        # here until this service request completes.
        rclpy.spin_until_future_complete(
            self.node,
            future,
        )

        if not future.done():
            raise RuntimeError(
                "MG400 MoveLinear service did not complete"
            )

        exception = future.exception()

        if exception is not None:
            raise RuntimeError(
                f"MG400 MoveLinear service call failed: {exception}"
            )

        response = future.result()

        if response is None:
            raise RuntimeError(
                "MG400 MoveLinear service returned no response"
            )

        actual_pose = [
            float(value)
            for value in response.actual_pose
        ]

        if not response.success:
            raise RuntimeError(
                "MG400 movement failed: "
                f"{response.message}; "
                f"actual_pose={actual_pose}"
            )

        with self._lock:
            self._pose = actual_pose

        self.node.get_logger().info(
            "MG400 move completed: "
            f"{[round(v, 4) for v in actual_pose]}"
        )

        return actual_pose