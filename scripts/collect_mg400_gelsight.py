import os
import csv
import time
import math
import json
import traceback
import argparse
from datetime import datetime

import cv2
import numpy as np

from cri.controller import Controller
from cri.robot import SyncRobot
from unitac_workshop.tactile_bench.data.utils.sensors import RealSensor


# ============================================================
# CALIBRATED MG400 / GELSIGHT SETUP
# ============================================================

WORK_FRAME = [
    265.36090088,
    40.82979202,
    -114.89134216,
    0, 0, 0,
]

TCP = [0, 0, -50, 0, 0, 0]
RZ = -31.3
CAMERA = 2


# ============================================================
# VALIDATED GENFORCE TRAJECTORY PARAMETERS
# ============================================================

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


# ============================================================
# TEMPORAL SAMPLING
# ============================================================

NORMAL_SAMPLES = 11
SHEAR_SAMPLES = 11
SAMPLE_SETTLE_TIME = 0.10
SAFE_SETTLE_TIME = 0.5

BASE_OUTPUT_ROOT = "tactile_data/gelsight/genforce"

VALID_INDENTERS = [
    "cone", "cylinder_sh", "cylinder_si", "cylinder", "dotin", "dots",
    "hemisphere", "hexagon", "line", "moon", "pacman", "prism",
    "random", "sphere_s", "sphere", "torus", "triangle", "wave",
]

INDENTER_ID = None
OUTPUT_ROOT = None

VERIFY_SAVED_IMAGES = True
FLUSH_METADATA_EVERY_FRAME = True


METADATA_FIELDS = [
    "run_id", "indenter_id", "sample_id", "capture_start_timestamp",
    "capture_end_timestamp", "datetime", "cycle", "base_idx", "depth_idx",
    "angle_idx", "phase", "frame_idx", "phase_progress", "image",
    "base_x_mm", "base_y_mm", "depth_mm", "angle_deg",
    "cmd_x", "cmd_y", "cmd_z", "cmd_Rx", "cmd_Ry", "cmd_Rz",
    "actual_x", "actual_y", "actual_z", "actual_Rx", "actual_Ry", "actual_Rz",
    "err_x_mm", "err_y_mm", "err_z_mm", "err_xyz_mm",
]


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
    return [start + alpha * (end - start) for alpha in np.linspace(0.0, 1.0, n)]


def atomic_write_json(path, data):
    """Write JSON via a temporary file, then atomically replace destination."""
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def expected_counts():
    cycles = len(BASE_POINTS) * len(DEPTHS) * ANGLE_N
    samples_per_cycle = 2 * NORMAL_SAMPLES + 2 * SHEAR_SAMPLES
    trajectory_samples = cycles * samples_per_cycle
    total_samples = trajectory_samples + 1
    return cycles, samples_per_cycle, trajectory_samples, total_samples


def experiment_config(run_id):
    cycles, samples_per_cycle, trajectory_samples, total_samples = expected_counts()
    return {
        "run_id": run_id,
        "indenter_id": INDENTER_ID,
        "indenter_stl": f"{INDENTER_ID}.stl",
        "dataset_type": "GenForce-style GelSight trajectory",
        "robot": "Dobot MG400",
        "sensor": "GelSight",
        "force_sensor": False,
        "work_frame": WORK_FRAME,
        "tcp": TCP,
        "rz_deg": RZ,
        "camera_source": CAMERA,
        "base_points_mm": [list(p) for p in BASE_POINTS],
        "depths_mm": DEPTHS,
        "angle_n": ANGLE_N,
        "shear_radius_mm": SHEAR_RADIUS,
        "safe_z_mm": SAFE_Z,
        "normal_samples": NORMAL_SAMPLES,
        "shear_samples": SHEAR_SAMPLES,
        "sample_settle_time_s": SAMPLE_SETTLE_TIME,
        "safe_settle_time_s": SAFE_SETTLE_TIME,
        "expected_cycles": cycles,
        "samples_per_cycle": samples_per_cycle,
        "expected_trajectory_samples": trajectory_samples,
        "expected_total_samples_including_reference": total_samples,
        "trajectory_note": (
            "Validated quasi-static waypoint trajectory: safe -> normal indentation -> "
            "lateral shear -> shear return -> normal release."
        ),
    }


def verify_image(path):
    """Fail immediately if an expected image was not written/readable."""
    if not os.path.isfile(path):
        raise RuntimeError(f"Image was not created: {path}")
    if os.path.getsize(path) <= 0:
        raise RuntimeError(f"Image file is empty: {path}")
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None or img.size == 0:
        raise RuntimeError(f"Saved image is unreadable: {path}")


def preflight_camera(sensor):
    """Verify the camera can provide a non-empty frame before any robot motion."""
    frame = sensor.read()
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        raise RuntimeError("GelSight camera preflight failed: empty frame")
    print(f"Camera preflight OK: shape={frame.shape}, dtype={frame.dtype}", flush=True)


def capture(
    sensor, robot, image_path, writer, metadata_handle, run_id, sample_id,
    cycle, base_idx, depth_idx, angle_idx, phase, frame_idx, phase_progress,
    base_x, base_y, depth, angle_deg, command_pose,
):
    os.makedirs(os.path.dirname(image_path), exist_ok=True)
    t_capture_start = time.time()
    sensor.process(image_path)
    t_capture_end = time.time()

    if VERIFY_SAVED_IMAGES:
        verify_image(image_path)

    actual = np.asarray(robot.pose, dtype=float)
    command_pose = np.asarray(command_pose, dtype=float)
    if actual.shape[0] < 6:
        raise RuntimeError(f"Unexpected robot pose returned: {actual}")

    err = actual[:3] - command_pose[:3]
    err_xyz = float(np.linalg.norm(err))
    run_root = os.path.join(OUTPUT_ROOT, run_id)
    image_rel = os.path.relpath(image_path, run_root)

    writer.writerow([
        run_id, INDENTER_ID, sample_id, t_capture_start, t_capture_end,
        datetime.now().isoformat(), cycle, base_idx, depth_idx, angle_idx,
        phase, frame_idx, phase_progress, image_rel, base_x, base_y, depth,
        angle_deg, *command_pose.tolist(), *actual.tolist(),
        float(err[0]), float(err[1]), float(err[2]), err_xyz,
    ])

    if FLUSH_METADATA_EVERY_FRAME:
        metadata_handle.flush()

    print(
        f"  {phase:10s} {frame_idx:03d} progress={phase_progress:5.2f} "
        f"cmd=({command_pose[0]:6.3f},{command_pose[1]:6.3f},{command_pose[2]:6.3f}) "
        f"actual=({actual[0]:6.3f},{actual[1]:6.3f},{actual[2]:6.3f}) "
        f"err_xyz={err_xyz:.4f} mm",
        flush=True,
    )
    return sample_id + 1


def run_phase(
    sensor, robot, writer, metadata_handle, save_root, run_id, sample_id,
    cycle, base_idx, depth_idx, angle_idx, phase, start_pose, end_pose,
    n_samples, base_x, base_y, depth, angle_deg,
):
    """Execute one validated phase and capture one frame per waypoint."""
    phase_dir = os.path.join(save_root, f"cycle_{cycle:03d}", phase)
    os.makedirs(phase_dir, exist_ok=True)
    trajectory = interpolate_pose(start_pose, end_pose, n_samples)
    print(f"\n{phase}: {n_samples} temporal samples", flush=True)

    for frame_idx, target in enumerate(trajectory):
        progress = frame_idx / (n_samples - 1) if n_samples > 1 else 1.0
        robot.move_linear(target)
        time.sleep(SAMPLE_SETTLE_TIME)
        image_path = os.path.join(phase_dir, f"{frame_idx:04d}.png")
        sample_id = capture(
            sensor=sensor, robot=robot, image_path=image_path, writer=writer,
            metadata_handle=metadata_handle, run_id=run_id, sample_id=sample_id,
            cycle=cycle, base_idx=base_idx, depth_idx=depth_idx,
            angle_idx=angle_idx, phase=phase, frame_idx=frame_idx,
            phase_progress=progress, base_x=base_x, base_y=base_y, depth=depth,
            angle_deg=angle_deg, command_pose=target,
        )
    return sample_id


def count_pngs(root):
    count = 0
    for dirpath, _, filenames in os.walk(root):
        count += sum(name.lower().endswith(".png") for name in filenames)
    return count


def count_cycle_dirs(root):
    return sum(
        1 for name in os.listdir(root)
        if name.startswith("cycle_") and os.path.isdir(os.path.join(root, name))
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Production GenForce MG400 + GelSight data collector"
    )
    parser.add_argument(
        "--indenter", required=True, choices=VALID_INDENTERS,
        help="Indenter identity (STL filename stem).",
    )
    return parser.parse_args()


def main():
    global INDENTER_ID, OUTPUT_ROOT

    args = parse_args()
    INDENTER_ID = args.indenter
    OUTPUT_ROOT = os.path.join(BASE_OUTPUT_ROOT, INDENTER_ID)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_root = os.path.join(OUTPUT_ROOT, run_id)

    os.makedirs(OUTPUT_ROOT, exist_ok=True)
    os.mkdir(save_root)

    metadata_file = os.path.join(save_root, "metadata.csv")
    config_file = os.path.join(save_root, "experiment_config.json")
    manifest_file = os.path.join(save_root, "manifest.json")
    completed_flag = os.path.join(save_root, "completed.flag")
    failed_file = os.path.join(save_root, "FAILED.txt")

    config = experiment_config(run_id)
    atomic_write_json(config_file, config)
    expected_cycles, samples_per_cycle, expected_trajectory, expected_total = expected_counts()

    manifest = {
        "run_id": run_id,
        "indenter_id": INDENTER_ID,
        "indenter_stl": f"{INDENTER_ID}.stl",
        "status": "initialising",
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "expected_cycles": expected_cycles,
        "samples_per_cycle": samples_per_cycle,
        "expected_trajectory_samples": expected_trajectory,
        "expected_total_samples_including_reference": expected_total,
        "completed_cycles": 0,
        "metadata_rows": 0,
        "png_files": 0,
        "last_completed_cycle": 0,
    }
    atomic_write_json(manifest_file, manifest)

    print("=" * 65)
    print("Production GenForce temporal MG400 + GelSight collector")
    print("=" * 65)
    print("Run ID:", run_id)
    print("Indenter:", INDENTER_ID)
    print("Output:", save_root)
    print("Work frame:", WORK_FRAME)
    print("TCP:", TCP)
    print("Base points:", BASE_POINTS)
    print("Depths:", DEPTHS)
    print("Shear radius:", SHEAR_RADIUS)
    print("Directions:", ANGLE_N)
    print("Expected cycles:", expected_cycles)
    print("Expected trajectory images:", expected_trajectory)
    print("Expected total PNGs incl. reference:", expected_total)
    print()

    robot = None
    sensor = None
    metadata_handle = None
    sample_id = 0
    cycle = 0
    success = False

    try:
        sensor = RealSensor({"name": "gelsight", "source": CAMERA})
        preflight_camera(sensor)

        robot = SyncRobot(Controller["mg400"]())
        robot.coord_frame = WORK_FRAME
        robot.tcp = TCP

        initial_pose = np.asarray(robot.pose, dtype=float)
        if initial_pose.shape[0] < 6 or not np.all(np.isfinite(initial_pose[:6])):
            raise RuntimeError(f"Invalid initial robot pose: {initial_pose}")
        print("Robot connection OK. Initial pose:", initial_pose, flush=True)

        manifest["status"] = "collecting"
        atomic_write_json(manifest_file, manifest)

        metadata_handle = open(metadata_file, "w", newline="")
        writer = csv.writer(metadata_handle)
        writer.writerow(METADATA_FIELDS)
        metadata_handle.flush()

        safe = pose(0.0, 0.0, SAFE_Z)
        print("Moving to initial safe pose:", safe, flush=True)
        robot.move_linear(safe)
        time.sleep(SAFE_SETTLE_TIME)

        sample_id = capture(
            sensor=sensor, robot=robot,
            image_path=os.path.join(save_root, "reference.png"),
            writer=writer, metadata_handle=metadata_handle, run_id=run_id,
            sample_id=sample_id, cycle=0, base_idx=0, depth_idx=0,
            angle_idx=0, phase="reference", frame_idx=0, phase_progress=1.0,
            base_x=0.0, base_y=0.0, depth=0.0, angle_deg=0.0,
            command_pose=safe,
        )

        for base_idx, (base_x, base_y) in enumerate(BASE_POINTS):
            base_safe = pose(base_x, base_y, SAFE_Z)
            print(f"\nBASE {base_idx}: x={base_x:.3f}, y={base_y:.3f}", flush=True)
            robot.move_linear(base_safe)
            time.sleep(SAFE_SETTLE_TIME)

            for depth_idx, depth in enumerate(DEPTHS):
                center = pose(base_x, base_y, -depth)

                for angle_idx in range(ANGLE_N):
                    cycle += 1
                    angle_deg = 360.0 * angle_idx / ANGLE_N
                    theta = math.radians(angle_deg)
                    dx = SHEAR_RADIUS * math.cos(theta)
                    dy = SHEAR_RADIUS * math.sin(theta)
                    shear = pose(base_x + dx, base_y + dy, -depth)

                    print("\n" + "=" * 65)
                    print(
                        f"Cycle {cycle}/{expected_cycles}: "
                        f"base={base_idx}, depth_idx={depth_idx}, angle_idx={angle_idx}, "
                        f"depth={depth:.3f} mm, angle={angle_deg:.1f} deg"
                    )
                    print("=" * 65, flush=True)

                    sample_id = run_phase(
                        sensor, robot, writer, metadata_handle, save_root, run_id,
                        sample_id, cycle, base_idx, depth_idx, angle_idx,
                        "normal_inc", base_safe, center, NORMAL_SAMPLES,
                        base_x, base_y, depth, angle_deg,
                    )
                    sample_id = run_phase(
                        sensor, robot, writer, metadata_handle, save_root, run_id,
                        sample_id, cycle, base_idx, depth_idx, angle_idx,
                        "shear_inc", center, shear, SHEAR_SAMPLES,
                        base_x, base_y, depth, angle_deg,
                    )
                    sample_id = run_phase(
                        sensor, robot, writer, metadata_handle, save_root, run_id,
                        sample_id, cycle, base_idx, depth_idx, angle_idx,
                        "shear_dec", shear, center, SHEAR_SAMPLES,
                        base_x, base_y, depth, angle_deg,
                    )
                    sample_id = run_phase(
                        sensor, robot, writer, metadata_handle, save_root, run_id,
                        sample_id, cycle, base_idx, depth_idx, angle_idx,
                        "normal_dec", center, base_safe, NORMAL_SAMPLES,
                        base_x, base_y, depth, angle_deg,
                    )

                    robot.move_linear(base_safe)
                    time.sleep(SAFE_SETTLE_TIME)

                    manifest["completed_cycles"] = cycle
                    manifest["last_completed_cycle"] = cycle
                    manifest["metadata_rows"] = sample_id
                    manifest["png_files"] = count_pngs(save_root)
                    atomic_write_json(manifest_file, manifest)

        print("\nCollection trajectory completed. Returning to centre safe pose.", flush=True)
        robot.move_linear(pose(0.0, 0.0, SAFE_Z))
        time.sleep(SAFE_SETTLE_TIME)

        metadata_handle.flush()
        png_count = count_pngs(save_root)
        cycle_dir_count = count_cycle_dirs(save_root)

        if cycle != expected_cycles:
            raise RuntimeError(f"Cycle count mismatch: {cycle} != {expected_cycles}")
        if cycle_dir_count != expected_cycles:
            raise RuntimeError(
                f"Cycle-directory count mismatch: {cycle_dir_count} != {expected_cycles}"
            )
        if sample_id != expected_total:
            raise RuntimeError(f"Metadata row count mismatch: {sample_id} != {expected_total}")
        if png_count != expected_total:
            raise RuntimeError(f"PNG count mismatch: {png_count} != {expected_total}")

        manifest.update({
            "status": "complete",
            "completed_at": datetime.now().isoformat(),
            "completed_cycles": cycle,
            "last_completed_cycle": cycle,
            "metadata_rows": sample_id,
            "png_files": png_count,
            "cycle_directories": cycle_dir_count,
            "integrity_check": "passed",
        })
        atomic_write_json(manifest_file, manifest)

        with open(completed_flag, "w") as f:
            f.write(
                f"run_id={run_id}\n"
                f"completed_at={manifest['completed_at']}\n"
                f"cycles={cycle}\n"
                f"trajectory_samples={expected_trajectory}\n"
                f"total_samples={sample_id}\n"
                f"png_files={png_count}\n"
            )

        success = True
        print("\n" + "=" * 65)
        print("COLLECTION COMPLETED AND VERIFIED")
        print("=" * 65)
        print(f"Cycles:        {cycle}/{expected_cycles}")
        print(f"Metadata rows: {sample_id}/{expected_total}")
        print(f"PNG files:     {png_count}/{expected_total}")
        print(f"Output:        {save_root}")
        print("Integrity:     PASSED", flush=True)

    except KeyboardInterrupt:
        manifest.update({
            "status": "interrupted",
            "completed_at": datetime.now().isoformat(),
            "completed_cycles": max(0, cycle - 1),
            "last_completed_cycle": max(0, cycle - 1),
            "metadata_rows": sample_id,
            "png_files": count_pngs(save_root),
        })
        atomic_write_json(manifest_file, manifest)

        with open(failed_file, "w") as f:
            f.write("Collection interrupted by user.\n")
            f.write(f"run_id={run_id}\n")
            f.write(f"active_cycle={cycle}\n")
            f.write(f"samples_saved={sample_id}\n")

        print("\nCollection interrupted by user.", flush=True)
        print("No automatic robot recovery movement was issued.", flush=True)
        print(f"Partial data retained in: {save_root}", flush=True)

    except Exception as exc:
        manifest.update({
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "completed_cycles": max(0, cycle - 1),
            "last_completed_cycle": max(0, cycle - 1),
            "metadata_rows": sample_id,
            "png_files": count_pngs(save_root),
            "error": repr(exc),
        })
        atomic_write_json(manifest_file, manifest)

        with open(failed_file, "w") as f:
            f.write(f"run_id={run_id}\n")
            f.write(f"active_cycle={cycle}\n")
            f.write(f"samples_saved={sample_id}\n\n")
            traceback.print_exc(file=f)

        print("\nCOLLECTION FAILED:", repr(exc), flush=True)
        print("No automatic robot recovery movement was issued after the failure.", flush=True)
        print(f"Partial data retained in: {save_root}", flush=True)
        print(f"Failure details: {failed_file}", flush=True)
        raise

    finally:
        if metadata_handle is not None:
            try:
                metadata_handle.flush()
                metadata_handle.close()
            except Exception:
                pass

        if sensor is not None:
            try:
                sensor.cam.release()
            except Exception:
                pass

        if robot is not None:
            try:
                robot.close()
            except Exception:
                pass

        cv2.destroyAllWindows()

        if success:
            print("Closed camera and robot connection after successful run.", flush=True)
        else:
            print("Closed camera and robot connection; inspect robot state before recovery.", flush=True)


if __name__ == "__main__":
    main()
