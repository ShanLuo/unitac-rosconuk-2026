# UniTac GenForce tactile representation (CPU-validated)

Read-only ROS 2 Humble pipeline: GelSight camera -> segmented marker image ->
pretrained GenForce SD-Turbo VAE with marker-encoder LoRA -> 4,096-element
`std_msgs/Float32MultiArray` on `/unitac/representation/embedding`.

## Validation (17 October 2026)

Validated in the existing `unitac-dev2` ROS 2 Humble Docker container with
a GelSight camera and the genuine GenForce checkpoint:

- Marker segmentation publishes `/unitac/gelsight/marker_image` (`mono8`).
- The pretrained model loads successfully with PEFT direct adapter injection.
- Saved 480 x 640 marker image produces 4,096 finite float32 features.
- Live ROS 2 output produces 4,096 finite values at approximately 0.82 Hz
  **on CPU** with `process_every_n:=10` (observed on one machine, not a guarantee).
- The encoder never commands the MG400 robot.

**Not yet validated:** GPU performance, force estimation accuracy, transfer
across sensors, or downstream closed-loop manipulation.

## Python dependencies

The following versions were tested together **inside the active container**;
they have not yet been integrated into the Docker image build:

```text
torch==2.2.2+cpu
diffusers==0.27.2
peft==0.10.0
transformers==4.39.3
huggingface-hub==0.25.2
accelerate==0.28.0
safetensors==0.4.3
```

Torch 2.2.2+cpu was installed from the PyTorch CPU wheel index. ROS 2
Humble's existing OpenCV, NumPy and cv_bridge packages were retained.
The SD-Turbo VAE (`stabilityai/sd-turbo`, subfolder `vae`) is downloaded
from Hugging Face on first use, requiring internet access and sufficient disk
space. Check upstream model and dataset terms before redistributing weights.

## Checkpoint (download separately; do not commit weights)

The actual GenForce marker-encoder checkpoint is inside the
[GenForce Hugging Face dataset](https://huggingface.co/datasets/zhuoKCL/genforce),
archive `ckpt.zip`, member
`vae/marker_encoder/checkpoint-70000/checkpoint.pth`.
This is a LoRA checkpoint with `state_dict_vae`, `rank_vae=4`, and
adapter name `marker_encoder`. The checkpoint is **not bundled** in UniTac.

On the **host**, with the workspace mounted into Docker as `/ros2_ws`:

```bash
mkdir -p ~/unitac_ros2/checkpoints
curl -L --fail --retry 3 \
  https://huggingface.co/datasets/zhuoKCL/genforce/resolve/main/ckpt.zip \
  -o ~/unitac_ros2/checkpoints/ckpt.zip
unzip -p ~/unitac_ros2/checkpoints/ckpt.zip \
  vae/marker_encoder/checkpoint-70000/checkpoint.pth \
  > ~/unitac_ros2/checkpoints/checkpoint.pth
```

The archive is approximately 884 MiB; only the marker checkpoint needs to be
extracted. Keep checkpoint files outside the Git repository.

## Run the live pipeline

Build once in the existing ROS 2 Humble workspace:

```bash
cd /ros2_ws
colcon build --symlink-install --packages-select unitac_representation
source /ros2_ws/install/setup.bash
```

Start the GelSight camera publisher and marker segmentation node in separate
terminals (one camera owner only):

```bash
ros2 run unitac_gelsight gelsight_node
ros2 run unitac_representation marker_segmentation
```

Start the encoder in a third terminal:

```bash
source /ros2_ws/install/setup.bash
ros2 run unitac_representation genforce_encoder --ros-args \
  -p checkpoint_path:=/ros2_ws/checkpoints/checkpoint.pth \
  -p input_topic:=/unitac/gelsight/marker_image \
  -p input_is_marker_image:=true \
  -p device:=cpu \
  -p process_every_n:=10
```

Check publication in another terminal:

```bash
ros2 topic hz /unitac/representation/embedding
ros2 topic echo /unitac/representation/embedding --once --full-length
```

The full-length flag matters: the default ROS 2 CLI abbreviates large arrays
with `...`. The encoder deliberately refuses unsegmented raw RGB input.
No MG400 movement is needed.

## Next milestones

1. Optional CUDA backend, profiling and throughput optimization.
2. Quantitative evaluation of learned features for force estimation.
3. A safe, opt-in manipulation demonstration using tactile feedback.

The current node publishes **representations, not force predictions**. Do not
interpret the features as calibrated force measurements or claim cross-sensor
generalization without evaluation.
