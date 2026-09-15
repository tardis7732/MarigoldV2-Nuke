"""Run a real normal prediction and record GPU memory without requiring Nuke."""

import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "daemon"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--image", required=True, help="sRGB PNG/JPEG image")
    parser.add_argument("--resolution", type=int, default=512)
    parser.add_argument("--output", default=str(ROOT / "output/gpu-smoke"))
    args = parser.parse_args()
    import cv2
    import numpy as np
    import torch
    from backend import MarigoldBackend
    from marigold_daemon import Engine

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable in this interpreter")
    bgr = cv2.imread(args.image, cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(args.image)
    rgb = np.ascontiguousarray(bgr[..., ::-1], dtype="<f4") / 255.0
    h, w = rgb.shape[:2]
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    engine = Engine(MarigoldBackend(args.repo, args.assets))
    torch.cuda.reset_peak_memory_stats()
    start = time.monotonic()
    report = {
        "gpu": torch.cuda.get_device_name(),
        "resolution": args.resolution,
        "total_vram_bytes": torch.cuda.get_device_properties(0).total_memory,
    }
    try:
        meta, payload = engine.infer(
            {"cmd": "infer", "width": w, "height": h, "resolution": args.resolution}, rgb.tobytes()
        )
        normal = np.frombuffer(payload, dtype="<f4").reshape(4, h, w)[:3]
        np.save(out / "normals.npy", normal)
        if not cv2.imwrite(str(out / "normals.exr"), normal.transpose(1, 2, 0)[..., ::-1]):
            raise RuntimeError("OpenEXR write failed")
        preview = ((normal.transpose(1, 2, 0) + 1) * 127.5).clip(0, 255).astype(np.uint8)
        cv2.imwrite(str(out / "preview.png"), preview[..., ::-1])
        report.update(meta)
        report["success"] = True
    except Exception as exc:
        report.update(success=False, error=str(exc))
        raise
    finally:
        report.update(
            elapsed_seconds=time.monotonic() - start,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        )
        (out / "memory.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
