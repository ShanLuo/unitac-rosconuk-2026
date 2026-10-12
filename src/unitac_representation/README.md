# UniTac GenForce encoder (prototype)

Read-only ROS 2 node: marker image -> GenForce SD-Turbo VAE/LoRA posterior-mean embedding.

**Not yet hardware or checkpoint tested.** No MG400 motion commands. The node
refuses to start with raw RGB images: GenForce expects segmented marker images.

Dependencies beyond ROS Humble: `torch`, `diffusers`, `peft` (compatible
versions must be installed and tested), plus access to the SD-Turbo VAE weights.
The official GenForce LoRA checkpoint is documented as
`checkpoints/m2m/vae/model_70000.pth` in
https://github.com/Zhuochenn/GenForce_Code . Checkpoint not bundled.

```bash
colcon build --symlink-install --packages-select unitac_representation
source install/setup.bash
ros2 run unitac_representation genforce_encoder --ros-args \
  -p checkpoint_path:=/path/to/model_70000.pth \
  -p input_is_marker_image:=true \
  -p input_topic:=/unitac/gelsight/marker_image
```

Output: `/unitac/representation/embedding` (`std_msgs/Float32MultiArray`).
The image must be a 3-channel image of *segmented markers*, matching the
GenForce preprocessing. A marker segmentation node is still needed to
connect the existing `/unitac/gelsight/image_raw` stream correctly.

This node loads the pretrained weights; it does not train a model, estimate
force, or demonstrate closed-loop robot control. Do not call the output
cross-sensor unified until that property has been evaluated.
