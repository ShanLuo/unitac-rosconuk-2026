# UniTac GenForce tactile representation (CPU and GPU validated)

Read-only ROS 2 Humble pipeline: GelSight camera -> segmented marker image ->
pretrained GenForce SD-Turbo VAE with marker-encoder LoRA -> 4,096-element
`std_msgs/Float32MultiArray` on `/unitac/representation/embedding`.

## CPU validation (17 October 2026)

Validated in the existing `unitac-dev2` ROS 2 Humble Docker container with
a GelSight camera and the genuine GenForce checkpoint:

- Marker segmentation publishes `/unitac/gelsight/marker_image` (`mono8`).
- The pretrained model loads successfully with PEFT direct adapter injection.
- Saved 480 x 640 marker image produces 4,096 finite float32 features.
- Live ROS 2 output produces 4,096 finite values at approximately 0.82 Hz
  **on CPU** with `process_every_n:=10` (observed on one machine, not a guarantee).
- The encoder never commands the MG400 robot.

**Not yet validated:** force estimation accuracy, transfer across sensors,
or downstream closed-loop manipulation.

## Python dependencies

The following versions were tested together **inside the CPU container**;
they have not yet been integrated into a reproducible Docker image build:

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

## GPU validation (19 October 2026)

Validated with an NVIDIA GeForce RTX 2070 Max-Q (8 GB) in a separate
`unitac-gpu` ROS 2 Humble Docker container using NVIDIA Container Toolkit
and `torch==2.2.2+cu121`. The original CPU-validated Docker snapshot was
retained. The CUDA-enabled PyTorch wheel was installed manually in the GPU
container; **the Dockerfile does not yet reproduce this setup**.

Results from this machine:

| Test | Result |
| --- | --- |
| Saved-image GPU inference (5 warm-ups, 20 timed encodes) | 55.51 ms/image; 18.01 Hz |
| Live camera -> segmentation -> GPU encoder | approximately 14.5–14.6 Hz |
| Live setting | `process_every_n:=2` |
| Embedding | 4,096 finite float32 values |
| Offline GPU peak memory reserved | 0.72 GB |

The live measurement was taken from `ros2 topic hz` on
`/unitac/representation/embedding`, with camera FPS requested at 30.
A separate ROS 2 subscriber verified one 4,096-element live embedding
with all finite values. These are observations, **not guaranteed rates**.
The CPU live result (0.82 Hz) used different frame skipping
(`process_every_n:=10`), so it is not a controlled speedup comparison.
The GPU test has **not** yet been repeated with `process_every_n:=1`.
No robot commands were issued.

### Run with CUDA in the GPU-enabled container

Prerequisites: working NVIDIA Container Toolkit GPU access; CUDA-enabled
PyTorch 2.2.2+cu121 and the other dependencies listed above; ROS 2 Humble
environment; installed UniTac workspace; separately downloaded checkpoint.
Use one terminal per node, source the ROS 2 environment in each, and avoid
opening the camera from more than one process.

```bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash
ros2 run unitac_gelsight gelsight_node
```

In a second terminal:

```bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash
ros2 run unitac_representation marker_segmentation
```

In a third terminal:

```bash
source /opt/ros/humble/setup.bash
source /ros2_ws/install/setup.bash
ros2 run unitac_representation genforce_encoder --ros-args \
  -p checkpoint_path:=/ros2_ws/checkpoints/checkpoint.pth \
  -p device:=cuda \
  -p input_is_marker_image:=true \
  -p input_topic:=/unitac/gelsight/marker_image \
  -p process_every_n:=2
```

In another terminal, after sourcing both environments, measure the rate:

```bash
ros2 topic hz /unitac/representation/embedding
```

The `unitac-gpu` container was started with `--gpus all`, host networking,
the GelSight `/dev/video2` device, and the workspace bind-mounted at
`/ros2_ws`. The setup is machine-specific; do not assume that device paths,
GPU driver versions, or installed Python packages will match other hosts.

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

1. Package the validated CUDA environment reproducibly and test `process_every_n:=1` / throughput optimisation.
2. Quantitatively evaluate learned features for force estimation using synchronised ground truth.
3. Develop a safe, opt-in manipulation demonstration using tactile feedback.

The current node publishes **representations, not force predictions**. Do not
interpret the features as calibrated force measurements or claim cross-sensor
generalization without evaluation.
