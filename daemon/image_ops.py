"""Input encoding and output vector operations; no torch dependency."""

import numpy as np


def inference_size(width, height, resolution):
    if type(resolution) is not int or not 0 <= resolution <= 2048:
        raise ValueError("Resolution must be 0 (native) or 16..2048")
    if 0 < resolution < 16:
        raise ValueError("Resolution must be at least 16")
    scale = min(1.0, resolution / max(width, height)) if resolution else 1.0
    return tuple(max(16, int(round(edge * scale / 16)) * 16) for edge in (width, height))


def prepare_rgb(rgb, encoding):
    if encoding not in ("srgb", "linear_srgb"):
        raise ValueError("Input encoding must be srgb or linear_srgb")
    rgb = np.nan_to_num(rgb, nan=0.0, posinf=1.0, neginf=0.0)
    rgb = np.clip(rgb, 0, 1)
    if encoding == "linear_srgb":
        rgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)
    return np.ascontiguousarray(rgb, dtype=np.float32)


def normal_planes(normals, flips=(False, False, False)):
    normals = np.asarray(normals, dtype=np.float32)
    if normals.ndim != 3 or normals.shape[0] != 3 or not np.isfinite(normals).all():
        raise ValueError("Model must return finite normals with shape [3,H,W]")
    lengths = np.linalg.norm(normals, axis=0, keepdims=True)
    if np.any(lengths < 1e-6):
        raise ValueError("Model returned zero-length normals")
    normals = normals / lengths
    normals *= np.array([-1 if f else 1 for f in flips], dtype=np.float32)[:, None, None]
    return np.ascontiguousarray(
        np.concatenate([normals, np.ones((1, *normals.shape[1:]), dtype=np.float32)]), dtype="<f4"
    )


def depth_planes(depth):
    """Transport raw relative log-depth in RGB; alpha is validity, not depth."""
    depth = np.asarray(depth, dtype=np.float32)
    if depth.ndim != 3 or depth.shape[0] != 1 or not np.isfinite(depth).all():
        raise ValueError("Model must return finite depth with shape [1,H,W]")
    return np.ascontiguousarray(
        np.concatenate([np.repeat(depth, 3, axis=0), np.ones_like(depth)]), dtype="<f4"
    )
