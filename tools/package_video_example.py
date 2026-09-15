"""Validate signed EXRs and make H.264 source/normal comparison videos."""

import json
import subprocess
from pathlib import Path

import imageio_ffmpeg
import numpy as np
import OpenEXR
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples/video_demo"
COUNT = 48


def main():
    previews = BASE / "preview"
    comparisons = BASE / "comparison"
    previews.mkdir(exist_ok=True)
    comparisons.mkdir(exist_ok=True)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 17)
    error = 0.0
    changes = []
    previous = None
    for frame in range(1, COUNT + 1):
        with OpenEXR.File(
            str(BASE / f"normals/normals.{frame:04d}.exr"), separate_channels=True
        ) as file:
            channels = file.channels()
            xyz = np.stack([channels[c].pixels for c in "RGB"], axis=-1)
            alpha = channels["A"].pixels
            assert xyz.shape == (768, 432, 3), xyz.shape
            assert np.isfinite(xyz).all()
            assert np.all(alpha == 1)
            unit_error = float(np.max(np.abs(np.linalg.norm(xyz, axis=-1) - 1)))
            assert unit_error < 0.001, unit_error
            error = max(error, unit_error)
        if previous is not None:
            changes.append(float(np.abs(xyz - previous).mean()))
        previous = xyz
        normal = Image.fromarray(np.rint(np.clip(xyz * 0.5 + 0.5, 0, 1) * 255).astype(np.uint8))
        normal.save(previews / f"preview.{frame:04d}.png")
        with Image.open(BASE / f"source/source.{frame:04d}.png") as source:
            pair = Image.new("RGB", (864, 808), (20, 25, 31))
            pair.paste(source, (0, 40))
            pair.paste(normal, (432, 40))
        draw = ImageDraw.Draw(pair)
        draw.text((12, 10), "SOURCE / Pexels - Airam Dato-on", font=font, fill="white")
        draw.text((444, 10), f"MARIGOLD NORMALS / {frame:02d} of 48", font=font, fill="white")
        pair.save(comparisons / f"comparison.{frame:04d}.png")
        if frame == 1:
            pair.save(BASE / "comparison_poster.png")

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    for folder, stem, dest in [
        ("source", "source", "source_clip"),
        ("preview", "preview", "normals_preview"),
        ("comparison", "comparison", "comparison"),
    ]:
        subprocess.run(
            [
                ffmpeg,
                "-v",
                "error",
                "-y",
                "-framerate",
                "12",
                "-start_number",
                "1",
                "-i",
                str(BASE / folder / (stem + ".%04d.png")),
                "-frames:v",
                str(COUNT),
                "-c:v",
                "libx264",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(BASE / (dest + ".mp4")),
            ],
            check=True,
        )
        reader = imageio_ffmpeg.read_frames(str(BASE / (dest + ".mp4")))
        meta = next(reader)
        decoded = sum(1 for _ in reader)
        assert decoded == COUNT, (dest, decoded)
        assert abs(meta["fps"] - 12) < 0.001

    progress = json.loads((BASE / "progress.json").read_text())
    report = {
        "frames": COUNT,
        "fps": 12,
        "duration_seconds": 4,
        "source_size": [432, 768],
        "inference_long_edge": 512,
        "seed": 2025,
        "max_normal_unit_error": error,
        "mean_absolute_normal_change_per_frame": changes,
        "render_seconds": sum(progress["frame_seconds"]),
        "temporal_processing": "Independent frames; no smoothing or interpolation",
        "source_url": "https://www.pexels.com/video/urban-street-life-with-people-walking-by-historic-building-35958383/",
    }
    (BASE / "validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    sheet = Image.new("RGB", (864, 808))
    for i, frame in enumerate((1, 12, 24, 48)):
        with Image.open(comparisons / f"comparison.{frame:04d}.png") as pair:
            sheet.paste(pair.resize((432, 404)), ((i % 2) * 432, (i // 2) * 404))
    sheet.save(BASE / "contact_sheet.jpg")
    print("VIDEO_PACKAGE_OK", COUNT, "frames; render seconds", report["render_seconds"])


if __name__ == "__main__":
    main()
