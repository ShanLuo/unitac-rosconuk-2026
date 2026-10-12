"""ROS 2 adapter for the GenForce pretrained marker VAE.

The GenForce LoRA checkpoint must be supplied separately. This module does
not perform marker segmentation; input must already be a marker image.
"""
from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from std_msgs.msg import Float32MultiArray


class GenForceVAE:
    """SD-Turbo VAE plus GenForce's LoRA weights, with deterministic output."""

    TARGET_MODULES = [
        'conv1', 'conv2', 'conv_in', 'conv_shortcut', 'conv',
        'conv_out', 'to_k', 'to_q', 'to_v', 'to_out.0',
    ]

    def __init__(self, checkpoint_path, device='cpu'):
        import torch
        from diffusers import AutoencoderKL
        from peft import LoraConfig

        self.torch = torch
        self.device = torch.device(device)
        path = Path(checkpoint_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f'GenForce checkpoint not found: {path}')

        # Official GenForce training uses stabilityai/sd-turbo/vae.
        self.vae = AutoencoderKL.from_pretrained(
            'stabilityai/sd-turbo', subfolder='vae'
        )
        checkpoint = torch.load(str(path), map_location='cpu', weights_only=True)
        if not isinstance(checkpoint, dict) or 'state_dict_vae' not in checkpoint:
            raise ValueError('Expected GenForce LoRA checkpoint with state_dict_vae')

        rank = int(checkpoint.get('rank_vae', 4))
        targets = checkpoint.get('vae_lora_target_modules', self.TARGET_MODULES)
        self.vae.add_adapter(
            LoraConfig(r=rank, init_lora_weights='gaussian',
                       target_modules=targets),
            adapter_name='marker_encoder',
        )
        current = self.vae.state_dict()
        weights = checkpoint['state_dict_vae']
        unknown = set(weights) - set(current)
        if unknown:
            raise ValueError(f'Checkpoint has {len(unknown)} unexpected keys')
        current.update(weights)
        self.vae.load_state_dict(current, strict=True)
        self.vae.to(self.device).eval()
        for parameter in self.vae.parameters():
            parameter.requires_grad_(False)

    def encode(self, marker_bgr):
        """Return flattened posterior mean (not sampled), float32 numpy array."""
        if marker_bgr.ndim == 2:
            rgb = cv2.cvtColor(marker_bgr, cv2.COLOR_GRAY2RGB)
        elif marker_bgr.ndim == 3 and marker_bgr.shape[2] == 3:
            rgb = cv2.cvtColor(marker_bgr, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError('Expected mono8 or 3-channel marker image')
        rgb = cv2.resize(rgb, (256, 256), interpolation=cv2.INTER_LINEAR)
        tensor = self.torch.from_numpy(
            np.ascontiguousarray(rgb.transpose(2, 0, 1))
        ).unsqueeze(0).to(self.device, dtype=self.torch.float32) / 255.0
        # Match the original GenForce marker encoder ToTensor() [0,1].
        with self.torch.inference_mode():
            posterior = self.vae.encode(tensor).latent_dist
            latent = posterior.mean * self.vae.config.scaling_factor
        result = latent.reshape(-1).cpu().numpy().astype(np.float32)
        if not np.isfinite(result).all():
            raise ValueError('Non-finite GenForce embedding')
        return result


class GenForceEncoderNode(Node):
    def __init__(self):
        super().__init__('unitac_genforce_encoder')
        self.declare_parameter('checkpoint_path', '')
        self.declare_parameter('device', 'cpu')
        self.declare_parameter('input_topic', '/unitac/gelsight/image_raw')
        self.declare_parameter('output_topic', '/unitac/representation/embedding')
        self.declare_parameter('input_is_marker_image', False)
        self.declare_parameter('process_every_n', 1)

        if not self.get_parameter('input_is_marker_image').value:
            raise ValueError(
                'Input is raw GelSight RGB. Segment markers first, then set '
                'input_is_marker_image:=true. Refusing to publish misleading latents.'
            )
        every = int(self.get_parameter('process_every_n').value)
        if every < 1:
            raise ValueError('process_every_n must be >= 1')
        self.every = every
        self.count = 0
        self.bridge = CvBridge()
        self.encoder = GenForceVAE(
            self.get_parameter('checkpoint_path').value,
            self.get_parameter('device').value,
        )
        self.publisher = self.create_publisher(
            Float32MultiArray, self.get_parameter('output_topic').value, 10
        )
        self.subscription = self.create_subscription(
            Image, self.get_parameter('input_topic').value, self.on_image, 10
        )
        self.get_logger().info('GenForce marker encoder ready (read-only; no robot commands)')

    def on_image(self, msg):
        self.count += 1
        if self.count % self.every:
            return
        try:
            image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            embedding = self.encoder.encode(image)
            output = Float32MultiArray()
            output.data = embedding.tolist()
            self.publisher.publish(output)
        except Exception as exc:
            self.get_logger().error(f'Encoding failed: {exc}')


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = GenForceEncoderNode()
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
