#!/usr/bin/env python3

import csv
from pathlib import Path

import cv2


class GenForceCapture:
    """
    Save synchronized GelSight images and GenForce trajectory metadata.
    """

    def __init__(
        self,
        gelsight,
        output_dir,
    ):
        self.gelsight = gelsight

        self.output_dir = Path(output_dir)
        self.image_dir = self.output_dir / "images"

        self.image_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.csv_path = self.output_dir / "samples.csv"

        self.sample_id = 0

        self._csv_file = open(
            self.csv_path,
            "w",
            newline="",
        )

        self._writer = csv.writer(self._csv_file)

        self._writer.writerow([
            "sample_id",
            "image",
            "phase",
            "frame_idx",
            "progress",
            "target_x",
            "target_y",
            "target_z",
            "target_rx",
            "target_ry",
            "target_rz",
            "actual_x",
            "actual_y",
            "actual_z",
            "actual_rx",
            "actual_ry",
            "actual_rz",
            "image_stamp_sec",
            "image_stamp_nanosec",
            "image_frame_counter",
        ])

        self._csv_file.flush()

    def capture(
        self,
        phase,
        frame_idx,
        progress,
        target_pose,
        actual_pose,
    ):
        """
        Wait for a new GelSight frame, then save that exact frame
        together with its matching timestamp and robot metadata.
        """

        sample_id = self.sample_id

        # Record which frame is current before waiting.
        previous_counter = self.gelsight.frame_counter

        frame, stamp, frame_counter = (
            self.gelsight.wait_for_new_frame(
                after_counter=previous_counter,
                timeout=2.0,
            )
        )

        image_name = f"{sample_id:06d}.png"
        image_path = self.image_dir / image_name

        success = cv2.imwrite(
            str(image_path),
            frame,
        )

        if not success:
            raise RuntimeError(
                f"Failed to save GelSight image: {image_path}"
            )

        stamp_sec, stamp_nanosec = stamp

        target_pose = [
            float(value)
            for value in target_pose
        ]

        actual_pose = [
            float(value)
            for value in actual_pose
        ]

        self._writer.writerow([
            sample_id,
            image_name,
            phase,
            frame_idx,
            float(progress),
            *target_pose,
            *actual_pose,
            stamp_sec,
            stamp_nanosec,
            frame_counter,
        ])

        self._csv_file.flush()

        self.sample_id += 1

        return sample_id

    def close(self):
        if not self._csv_file.closed:
            self._csv_file.flush()
            self._csv_file.close()