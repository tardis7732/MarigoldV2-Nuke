"""Run the same MoGe-nuke sample through its model and the Marigold adapter.

Execute each model in its own process to release GPU memory between models.
The output is a qualitative comparison, not a ground-truth accuracy benchmark.
"""

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


def save_result(out, name, planes, metadata):
    import numpy as np
    import OpenEXR
    from PIL import Image

    planes = np.asarray(planes, dtype=np.float32)
    assert planes.ndim == 3 and planes.shape[0] == 4
    valid = planes[3] > 0.5
    assert np.isfinite(planes).all()
    lengths = np.linalg.norm(planes[:3], axis=0)
    metadata["max_unit_error_valid"] = float(np.abs(lengths[valid] - 1).max())
    metadata["valid_fraction"] = float(valid.mean())
    assert metadata["max_unit_error_valid"] < 0.001
    np.save(out / f"{name}.npy", planes)
    channels = {c: np.ascontiguousarray(planes[i]) for i, c in enumerate("RGBA")}
    with OpenEXR.File({}, channels) as file:
        file.write(str(out / f"{name}.exr"))
    rgb = np.rint(np.clip(planes[:3].transpose(1, 2, 0) * 0.5 + 0.5, 0, 1) * 255)
    rgb[~valid] = 0
    Image.fromarray(rgb.astype(np.uint8)).save(out / f"{name}.png")
    (out / f"{name}.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print("COMPARISON_RESULT_OK", name, json.dumps(metadata), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", choices=("moge", "marigold"), required=True)
    p.add_argument("--base", type=Path, required=True)
    args = p.parse_args()
    base = args.base.resolve()
    out = base / "results"
    out.mkdir(exist_ok=True)
    import numpy as np
    import torch
    from PIL import Image

    source = base / "moge-nuke/docs/sample.jpg"
    rgb = np.asarray(Image.open(source).convert("RGB"), dtype="<f4") / 255
    h, w = rgb.shape[:2]
    common = {
        "source": "MoGe-nuke/docs/sample.jpg",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_size": [w, h],
        "gpu": torch.cuda.get_device_name(),
        "torch": torch.__version__,
        "input_encoding": "srgb",
        "display": "RGB = XYZ * 0.5 + 0.5; no gamma; invalid pixels black",
        "ground_truth": False,
    }
    if args.model == "moge":
        module_path = base / "moge-nuke/daemon/moge_daemon.py"
        spec = importlib.util.spec_from_file_location("comparison_moge_daemon", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        engine = module.Engine("cuda")
        model_path = base / "assets/moge-3/model.safetensors"
        model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
        assert model_hash == "685c5bc2bc1acfac86b928255c2c5397a7de4824870ade392e2ba1f74c2ce52b"
        started = time.perf_counter()
        engine.ensure_model(str(model_path))
        torch.cuda.synchronize()
        load_seconds = time.perf_counter() - started
        header = {
            "width": w,
            "height": h,
            "refine_steps": 3,
            "resolution_level": 9,
            "num_tokens": 0,
            "fp16": 0,
            "input_colorspace": "srgb",
            "normal_space": "nuke",
            "apply_mask": 1,
        }
        times = []
        torch.cuda.reset_peak_memory_stats()
        for _ in range(2):
            torch.manual_seed(2025)
            started = time.perf_counter()
            metadata, payload = engine.infer(header, rgb.tobytes())
            torch.cuda.synchronize()
            times.append(time.perf_counter() - started)
        planes = np.frombuffer(payload, dtype="<f4").reshape(5, h, w)[:4]
        save_result(
            out,
            "moge3",
            planes,
            {
                **common,
                "settings": header,
                "model_sha256": model_hash,
                "load_seconds": load_seconds,
                "first_inference_seconds": times[0],
                "warm_inference_seconds": times[1],
                "inference_seconds_reported": metadata["elapsed"],
                "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                "axes": "MoGe-nuke normal_space=nuke: raw OpenCV XYZ * [1,-1,-1]",
            },
        )
    else:
        sys.path.insert(0, str(base / "adapter/daemon"))
        from backend import MarigoldBackend
        from image_ops import inference_size, normal_planes

        backend = MarigoldBackend(base / "marigold-v2", base / "assets")
        started = time.perf_counter()
        backend.load()
        torch.cuda.synchronize()
        load_seconds = time.perf_counter() - started
        for resolution, name in ((0, "marigold_native"),):
            size = inference_size(w, h, resolution)
            times = []
            torch.cuda.reset_peak_memory_stats()
            for _ in range(2):
                started = time.perf_counter()
                normal = backend.predict(rgb, size, 2025)
                torch.cuda.synchronize()
                times.append(time.perf_counter() - started)
            planes = normal_planes(normal, (0, 0, 0))
            save_result(
                out,
                name,
                planes,
                {
                    **common,
                    "settings": {
                        "resolution": resolution,
                        "inference_size": list(size),
                        "seed": 2025,
                        "quantization": "NF4",
                        "compute": "bf16",
                    },
                    "load_seconds": load_seconds,
                    "first_inference_seconds": times[0],
                    "warm_inference_seconds": times[1],
                    "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                    "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                    "axes": "Marigold V2 native / Hypersim camera normals; no axis flip",
                },
            )


if __name__ == "__main__":
    main()
