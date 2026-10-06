import math
import numpy as np


# Validated GenForce trajectory parameters
RZ = -34.03894

BASE_POINTS = [
    (0.0, 0.0),
    (-3.0, +4.0),
    (-3.0, -4.0),
    (+3.0, -4.0),
    (+3.0, +4.0),
]

DEPTHS = [0.5]
ANGLE_N = 8
SHEAR_RADIUS = 1.0
SAFE_Z = 1.0

NORMAL_SAMPLES = 11
SHEAR_SAMPLES = 11


def pose(x, y, z):
    return np.array([x, y, z, 0.0, 0.0, RZ], dtype=float)


def interpolate_pose(start, end, n):
    """Generate n equally spaced Cartesian poses, including both endpoints."""
    if n < 1:
        raise ValueError("Number of samples must be >= 1")

    start = np.asarray(start, dtype=float)
    end = np.asarray(end, dtype=float)

    if n == 1:
        return [end.copy()]

    return [
        start + alpha * (end - start)
        for alpha in np.linspace(0.0, 1.0, n)
    ]


def generate_cycle(base_x, base_y, depth, angle_idx):
    """Generate one validated GenForce cycle."""

    angle_deg = 360.0 * angle_idx / ANGLE_N
    theta = math.radians(angle_deg)

    dx = SHEAR_RADIUS * math.cos(theta)
    dy = SHEAR_RADIUS * math.sin(theta)

    base_safe = pose(base_x, base_y, SAFE_Z)
    center = pose(base_x, base_y, -depth)
    shear = pose(base_x + dx, base_y + dy, -depth)

    phases = [
        ("normal_inc", base_safe, center, NORMAL_SAMPLES),
        ("shear_inc", center, shear, SHEAR_SAMPLES),
        ("shear_dec", shear, center, SHEAR_SAMPLES),
        ("normal_dec", center, base_safe, NORMAL_SAMPLES),
    ]

    trajectory = []

    for phase, start, end, n_samples in phases:
        for frame_idx, target in enumerate(
            interpolate_pose(start, end, n_samples)
        ):
            trajectory.append(
                (phase, frame_idx, target.copy())
            )

    return trajectory