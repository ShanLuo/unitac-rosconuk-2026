# UniTac hardware assets

This directory contains the physical CAD resources used for the UniTac ROSCon UK 2026 workshop.

## Indenters

The workshop indenter set comes from the public GenForce repository:

https://github.com/Zhuochenn/GenForce_Code/tree/main/sim/assets/indenters/input/stl

The GenForce repository currently contains 18 STL indenter models:

- cone.stl
- cylinder.stl
- cylinder_sh.stl
- cylinder_si.stl
- dotin.stl
- dots.stl
- hemisphere.stl
- hexagon.stl
- line.stl
- moon.stl
- pacman.stl
- prism.stl
- random.stl
- sphere.stl
- sphere_s.stl
- torus.stl
- triangle.stl
- wave.stl

These shapes originate from the tactile-simulation work reported in:

Gomes, D. F., Paoletti, P. and Luo, S. (2021). “Generation of GelSight tactile images for sim2real learning.” *IEEE Robotics and Automation Letters*, 6(2), 4177–4184.

That earlier work used 21 indenter geometries; the later GenForce work retained a subset of 18.

The intended destination in this repository is:

```text
assets/
└── indenters/
```

## Workshop mounts

The following workshop-specific mounting CAD files are provided directly for this repository and should be stored under:

```text
assets/
└── mount/
```

- `backpanel gelsight.stl` — back panel for attaching the customised GelSight sensor to the MG400 tooling.
- `MG400 End Flange.stl` — mount between the tactile sensor assembly and the MG400 end effector.
- `indenter_mount.stl` — fixture for fixing an indenter to the breadboard.
- `MG400_adapter.step_9826.stl` — adapter for mounting the MG400 robot to the breadboard.

## Additional MG400 rig reference

Nathan Lepora's public tactile-bench repository also contains MG400 rig resources:

https://github.com/robot-dexterity/tactile-bench/tree/main/assets/Dobot%20MG400%20rig

At the time of this update, the upstream tactile-bench `LICENSE` still contains proprietary/confidentiality restrictions, so those additional CAD files are linked rather than copied into UniTac.

## Licensing

The repository-level MIT licence covers UniTac workshop-authored code and documentation. Third-party files and previously published CAD should retain their applicable provenance, notices and permissions.
