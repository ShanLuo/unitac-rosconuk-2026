#!/usr/bin/env python3

import time

from unitac_collection.genforce_trajectory import interpolate_pose


SAMPLE_SETTLE_TIME = 0.10


def run_phase(
    robot,
    phase,
    start_pose,
    end_pose,
    n_samples,
    capture_fn=None,
    settle_time=SAMPLE_SETTLE_TIME,
):
    """
    Execute one GenForce phase using the same ordering as the
    validated production collector:

        move -> settle -> capture
    """

    trajectory = interpolate_pose(
        start_pose,
        end_pose,
        n_samples,
    )

    for frame_idx, target in enumerate(trajectory):

        progress = (
            frame_idx / (n_samples - 1)
            if n_samples > 1
            else 1.0
        )

        # Same blocking movement semantics as the original collector.
        robot.move_linear(target)

        # Configurable, with the validated 0.10 s as the default.
        time.sleep(settle_time)

        actual_pose = robot.pose

        if capture_fn is not None:
            capture_fn(
                phase=phase,
                frame_idx=frame_idx,
                progress=progress,
                target_pose=target.copy(),
                actual_pose=actual_pose.copy(),
            )