# UniTac @ ROSCon UK 2026

**UniTac: A ROS 2 Framework for Unified Tactile Sensing and Cross-Sensor Robot Learning**

Workshop repository for ROSCon UK 2026. UniTac provides a ROS 2 Humble workflow for tactile sensing and robot data collection. The workshop implementation includes a validated Dobot MG400 + GelSight pipeline, configurable experiment trajectories, and reusable tactile-learning examples.

## Developers and contributors

- **Prof. Shan Luo** (shan.luo@kcl.ac.uk) — main developer and project lead.
- **Prof. Nathan Lepora** (n.lepora@bristol.ac.uk) — contributor through `tactile-bench`, including the MG400 robot interface and TacTip sensor support.
- **Dr Jack Rome**, TouchLab — contributor.
- **Dr Vladimir Ivan**, TouchLab — contributor.

## ROS 2 packages

- `unitac_gelsight` — GelSight camera publisher.
- `unitac_mg400` — MG400 interface, calibrated pose publisher and blocking Cartesian MoveLinear service.
- `unitac_interfaces` — UniTac ROS 2 service definitions.
- `unitac_collection` — GenForce-style tactile trajectory and synchronized image/pose collection.
- `unitac_bringup` — YAML configuration and launch files for the complete system.

The validated workshop experiment contains 40 cycles, 1,760 trajectory samples and one reference image. Physical execution is deliberately opt-in; the collection launch defaults to `execute_motion:=false`.

## Repository structure

```text
.
├── assets/                    # CAD/rig asset index and permitted workshop assets
├── config/                    # hardware/experiment records
├── docker/                    # ROS 2 Humble workshop image
├── docs/                      # participant, hardware, provenance and data docs
├── examples/                  # hands-on tutorial examples
├── scripts/                   # collection/environment helpers
└── src/                       # UniTac ROS 2 packages and workshop utilities
```

## Quick start

The workshop image uses ROS 2 Humble on Ubuntu 22.04 and builds the UniTac ROS 2 packages with `colcon`. The MG400 backend is provided by the external [Common Robot Interface (CRI)](https://github.com/robot-dexterity/common-robot-interface), pinned in the Docker image for reproducibility.

```bash
git clone https://github.com/ShanLuo/unitac-rosconuk-2026.git
cd unitac-rosconuk-2026
docker compose build
docker compose run --rm workshop
```

The image already contains a built ROS 2 workspace and sources both ROS 2 Humble and the UniTac overlay for interactive shells. If you edit files under `src/`, rebuild the overlay inside the container with:

```bash
cd /ros2_ws
colcon build --symlink-install
source install/setup.bash
```

By default, Docker Compose maps host `/dev/video2` to the GelSight device expected by the validated configuration. If the tactile camera has a different host device, set it explicitly, for example:

```bash
GELSIGHT_DEVICE=/dev/video3 docker compose run --rm workshop
```

The container uses host networking so it can communicate with the MG400 over Ethernet. Verify the robot IP and camera device before hardware bringup.

## MG400 + GelSight workshop workflow

Only one MG400 connection owner and one GelSight camera owner should be running.

### 1. Hardware bringup

```bash
ros2 launch unitac_bringup hardware.launch.py
```

This starts the MG400 interface and GelSight publisher. It does not command robot motion.

Useful checks from a second terminal:

```bash
ros2 topic echo /unitac/mg400/pose --once
ros2 topic hz /unitac/gelsight/image_raw
```

### 2. Safe dry run

```bash
ros2 launch unitac_bringup collect_genforce.launch.py
```

The default is `execute_motion:=false`: the experiment plan is printed and no MG400 or GelSight connection is made by the collector.

### 3. Physical collection

Physical execution should only be used with the workshop hardware after the setup and calibration have been checked.

```bash
ros2 launch unitac_bringup collect_genforce.launch.py \
  execute_motion:=true \
  output_dir:=/ros2_ws/test_output/<run_name>
```

The workshop calibration and trajectory are configured in the YAML files under `unitac_bringup/config`.

## Hardware assets

See `assets/README.md`. The repository now documents the 18-indenter GenForce STL set (originating from the earlier 21-shape GelSight sim2real work), the four UniTac workshop mounting parts stored under `assets/mg400/`, and Nathan Lepora's public `tactile-bench` MG400 rig resources. Third-party CAD files are not automatically relicensed by this repository's MIT licence; their upstream terms must be respected.

## Funding

This work was supported by the Advanced Research + Invention Agency (ARIA) through the **“UniTac: Unifying Tactile Sensing through a Shared Latent Representation”** project, as part of the **Robot Dexterity programme**.

## Licence

UniTac workshop-authored code and documentation are released under the MIT License; see `LICENSE`.

Third-party code, models, CAD files and other assets remain subject to their respective upstream licences or permissions. The Common Robot Interface is an external GPLv3 dependency and is not vendored or relicensed as MIT by this repository. See `docs/ACKNOWLEDGEMENTS.md` and `assets/README.md`.
