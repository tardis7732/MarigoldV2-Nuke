"""Lay out measured depth outputs without modifying the underlying predictions."""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
results = ROOT / "examples/depth_comparison"
media = ROOT / "docs/media"
font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 25)
small = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 18)
images = [Image.open(results / f).convert("RGB") for f in
          ("sample.jpg", "moge_depth.png", "marigold_depth.png")]
labels = ["INPUT / same cake image", "MoGe-3 / log(depth)", "Marigold V2 / Log-stage2"]
sheet = Image.new("RGB", (1641, 925), (20, 24, 31))
draw = ImageDraw.Draw(sheet)
for i, (im, label) in enumerate(zip(images, labels)):
    draw.text((i*547+14, 16), label, font=font, fill="white")
    draw.text((i*547+14, 50), ["547 x 800 source", "Level 9 / refine 3 / FP32",
              "544 x 800 inference / NF4 BF16"][i], font=small, fill="#bac6d4")
    sheet.paste(im, (i*547, 85))
draw.text((14, 895), "Far = white | Each model: log-depth, 2-98% display range | No ground truth", font=small, fill="white")
sheet.save(media / "depth-comparison.png")
detail = Image.new("RGB", (1500, 1010), (20, 24, 31))
draw = ImageDraw.Draw(detail)
for i, label in enumerate(labels):
    draw.text((i*500+14, 16), label, font=font, fill="white")
for row, (label, box) in enumerate((
    ("Figures / cake edge", (135, 70, 375, 280)),
    ("Icing / strawberries", (135, 275, 375, 485)),
)):
    for col, im in enumerate(images):
        y = 65+row*465
        draw.text((col*500+10, y), label+" / 2x pixels", font=small, fill="white")
        detail.paste(im.crop(box).resize((480, 420), Image.Resampling.NEAREST), (col*500+10, y+30))
detail.save(media / "depth-comparison-details.png")
metadata = {model: json.loads((results / f"{model}_depth.json").read_text())
            for model in ("moge", "marigold")}
(ROOT / "docs/depth-comparison.json").write_text(json.dumps(metadata, indent=2)+"\n")
print("DEPTH_SHEETS_OK")
