"""Live tactile displacement estimation and simulated retraction proposals.

SIMULATION ONLY: This node never sends robot motion commands.
"""

import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, Float32MultiArray


class AdaptiveRetractionNode(Node):
    def __init__(self):
        super().__init__('unitac_adaptive_retraction')

        self.declare_parameter(
            'model_path',
            '/ros2_ws/test_output/genforce_full_01/contact_model.npz',
        )
        self.declare_parameter(
            'input_topic',
            '/unitac/representation/embedding',
        )

        model_path = self.get_parameter('model_path').value

        with np.load(model_path, allow_pickle=False) as model:
            self.mu = model['mu']
            self.sd = model['sd']
            self.basis = model['basis']
            self.coef = model['coef']
            self.threshold_low = float(model['threshold_low'])
            self.threshold_high = float(model['threshold_high'])

        self.expected_size = self.mu.size

        self.estimate_pub = self.create_publisher(
            Float32, '/unitac/adaptive/estimated_displacement_mm', 10
        )
        self.proposal_pub = self.create_publisher(
            Float32, '/unitac/adaptive/retraction_proposal_mm', 10
        )

        self.subscription = self.create_subscription(
            Float32MultiArray,
            self.get_parameter('input_topic').value,
            self.on_embedding,
            10,
        )

        self.get_logger().info(
            f'Adaptive inference ready: {self.expected_size}-D embeddings; '
            f'thresholds={self.threshold_low:.2f}, '
            f'{self.threshold_high:.2f} mm. SIMULATION ONLY.'
        )

    def on_embedding(self, msg):
        x = np.asarray(msg.data, dtype=np.float32)

        if x.size != self.expected_size or not np.all(np.isfinite(x)):
            self.get_logger().warning('Invalid embedding; skipping')
            return

        v = ((x - self.mu) / self.sd) @ self.basis
        estimated = max(
            0.0, float(np.r_[1.0, v] @ self.coef)
        )

        if not np.isfinite(estimated):
            self.get_logger().warning('Invalid prediction; skipping')
            return

        if estimated < self.threshold_low:
            retract = 0.0
        elif estimated < self.threshold_high:
            retract = 1.0
        else:
            retract = 2.0

        self.estimate_pub.publish(Float32(data=float(estimated)))
        self.proposal_pub.publish(Float32(data=retract))

        self.get_logger().info(
            f'Estimated displacement: {estimated:.2f} mm | '
            f'Proposed retraction: {retract:.0f} mm '
            '[SIMULATION ONLY]'
        )


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = AdaptiveRetractionNode()
        rclpy.spin(node)
    finally:
        if node is not None:
            node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
