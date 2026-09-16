"""Compare raw depth on the same sample; display each model in log-depth space."""

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--model", choices=("moge", "marigold"), required=True)
    p.add_argument("--base", type=Path, required=True)
    args = p.parse_args()
    base = args.base.resolve()
    out = base / "depth-results"
    out.mkdir(exist_ok=True)
    import numpy as np
    import OpenEXR
    import torch
    from PIL import Image

    source = base / "moge-nuke/docs/sample.jpg"
    rgb = np.asarray(Image.open(source).convert("RGB"), dtype="<f4") / 255
    h, w = rgb.shape[:2]
    meta = {"source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "source_size": [w, h], "gpu": torch.cuda.get_device_name(),
            "torch": torch.__version__, "ground_truth": False, "seed": 2025}
    started = time.perf_counter()
    if args.model == "moge":
        spec = importlib.util.spec_from_file_location("moge", base / "moge-nuke/daemon/moge_daemon.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        engine = module.Engine("cuda")
        checkpoint = base / "assets/moge-3/model.safetensors"
        meta["model_sha256"] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
        engine.ensure_model(str(checkpoint))
        header = {"width": w, "height": h, "refine_steps": 3, "resolution_level": 9,
                  "num_tokens": 0, "fp16": 0, "input_colorspace": "srgb",
                  "normal_space": "nuke", "apply_mask": 1}
        def predict():
            torch.manual_seed(2025)
            _, payload = engine.infer(header, rgb.tobytes())
            planes = np.frombuffer(payload, dtype="<f4").reshape(5, h, w)
            return planes[4].copy(), planes[3] > 0.5
        meta["settings"] = header
        meta["representation"] = "MoGe metric depth estimate"
    else:
        sys.path.insert(0, str(base / "adapter/daemon"))
        from backend import MarigoldBackend
        from image_ops import inference_size
        engine = MarigoldBackend(base / "marigold-v2", base / "assets")
        engine.load("depth")
        size = inference_size(w, h, 0)
        def predict():
            return engine.predict(rgb, size, 2025, task="depth")[0], np.ones((h, w), dtype=bool)
        meta["settings"] = {"resolution": 0, "inference_size": list(size), "quantization": "NF4", "compute": "bf16"}
        meta["representation"] = "affine-invariant log-depth (Log-stage2); not metric"
    torch.cuda.synchronize()
    meta["load_seconds"] = time.perf_counter() - started
    torch.cuda.reset_peak_memory_stats()
    times = []
    for _ in range(2):
        started = time.perf_counter()
        depth, valid = predict()
        torch.cuda.synchronize()
        times.append(time.perf_counter() - started)
    assert np.isfinite(depth[valid]).all()
    meta.update(first_inference_seconds=times[0], warm_inference_seconds=times[1],
                peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                raw_range=[float(depth[valid].min()), float(depth[valid].max())],
                valid_fraction=float(valid.mean()))
    if args.model == "marigold":
        # Exercise both directions on the same GPU backbone, including prompt graph swaps.
        normals_a = engine.predict(rgb, size, 2025, task="normals")
        depth_b, _ = predict()
        normals_b = engine.predict(rgb, size, 2025, task="normals")
        meta["depth_roundtrip_max_abs"] = float(np.max(np.abs(depth - depth_b)))
        meta["normal_roundtrip_max_abs"] = float(np.max(np.abs(normals_a - normals_b)))
        assert np.allclose(depth, depth_b, atol=1e-5, rtol=0)
        assert np.allclose(normals_a, normals_b, atol=1e-5, rtol=0)
    channels = {c: np.ascontiguousarray(depth) for c in ("R", "G", "B", "depth.Z")}
    channels["A"] = valid.astype(np.float32)
    with OpenEXR.File({}, channels) as file:
        file.write(str(out / f"{args.model}_depth.exr"))
    np.save(out / f"{args.model}_depth.npy", depth)
    display = np.log(np.maximum(depth, 1e-8)) if args.model == "moge" else depth
    lo, hi = np.percentile(display[valid], [2, 98])
    preview = np.clip((display-lo) / (hi-lo), 0, 1)
    preview[~valid] = 0
    Image.fromarray(np.rint(preview*255).astype(np.uint8)).save(out / f"{args.model}_depth.png")
    meta["display"] = {"space": "log-depth", "percentiles": [2, 98],
                       "range": [float(lo), float(hi)], "far": "white",
                       "normalization": "independent per model; display only"}
    (out / f"{args.model}_depth.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print("DEPTH_COMPARISON_OK", args.model, json.dumps(meta), flush=True)


if __name__ == "__main__":
    main()
