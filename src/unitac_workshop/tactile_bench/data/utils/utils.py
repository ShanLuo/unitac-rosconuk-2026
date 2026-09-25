import os
import argparse
import shutil
import json
import numpy as np


def make_dir(dirs, check=True):
    dirs = [dirs] if isinstance(dirs, str) else dirs
    if check:
        check_dir(dirs)
    for dir in dirs:
        os.makedirs(dir, exist_ok=True)

def check_dir(dirs):
    if isinstance(dirs, str):
        dirs = [dirs]
    for dir in dirs:
        if os.path.isdir(dir):
            if not str2bool(input(f"\n{dir} exists. Continue (y/n)? ")):
                exit()
            empty_dir(dir)

def empty_dir(dirs):
    if isinstance(dirs, str):
        dirs = [dirs]
    for dir in dirs:
        shutil.rmtree(dir)
        os.makedirs(dir, exist_ok=True)

def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")

def save_json_obj(obj, name):
    with open(name if name.endswith('.json') else name + ".json", "w") as fp:
        json.dump(obj, fp)

def load_json_obj(name):
    with open(name if name.endswith('.json') else name + ".json", "r") as fp:
        return json.load(fp)

def update_json_obj(name, obj_update):
    obj = load_json_obj(name)
    obj.update(obj_update)
    save_json_obj(obj, name)

def convert_json(obj):
    """Convert obj to a version which can be serialized with JSON."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    if isinstance(obj, dict):
        return {convert_json(k): convert_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [convert_json(x) for x in obj]
    if hasattr(obj, "__dict__") and obj.__dict__:
        return convert_json(obj.__dict__)
    return str(obj)

def random_spherical(num_samples, phi_max):
    """Return uniform random sample over a spherical cap bounded by polar angle."""
    phi_max = np.radians(phi_max)
    theta = 2 * np.pi * np.random.rand(num_samples)
    phi = np.arccos(1 - np.random.rand(num_samples) * (1 - np.cos(phi_max)))
    Rx = -np.arcsin(np.sin(phi) * np.sin(theta))
    Ry = -np.arctan2(np.sin(phi) * np.cos(theta), np.cos(phi))
    return np.degrees(Rx), np.degrees(Ry)

def random_disk(num_samples, r_max):
    """Return uniform random sample over a 2D circular disk of radius r_max."""
    r = r_max * np.sqrt(np.random.rand(num_samples))
    theta = 2 * np.pi * np.random.rand(num_samples)
    return r * np.cos(theta), r * np.sin(theta)

def random_linear(num_samples, x_max):
    """Return uniform random sample over a 1D segment [-x_max, x_max]."""
    return -x_max + 2 * x_max * np.random.rand(num_samples)

def np_collate(batch):
    """Collate function for numpy arrays."""
    elem = batch[0]
    if isinstance(elem, np.ndarray):
        return np.stack(batch)
    if isinstance(elem, (tuple, list)):
        return [np_collate(samples) for samples in zip(*batch)]
    if isinstance(elem, dict):
        return {k: np_collate([d[k] for d in batch]) for k in elem}
    return np.array(batch)
