"""Build identical display mappings and matching detail crops for a model comparison."""

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--results", type=Path, required=True)
    args = p.parse_args()
    root = args.results
    font_path = "C:/Windows/Fonts/arial.ttf"
    title = ImageFont.truetype(font_path, 25)
    body = ImageFont.truetype(font_path, 18)
    images = [
        Image.open(root / name).convert("RGB")
        for name in ("sample.jpg", "moge3.png", "marigold_native.png")
    ]
    w, h = images[0].size
    assert all(im.size == (w, h) for im in images)
    labels = [
        "INPUT / MoGe-nuke sample",
        "MoGe-3 / level 9, refine 3",
        "Marigold V2 / native",
    ]
    notes = [
        f"Same {w} x {h} source",
        "Nuke axes / default float32",
        "544 x 800 inference / seed 2025",
    ]
    for indexes, filename in [
        ((0, 1, 2), "comparison.png"),
    ]:
        sheet = Image.new("RGB", (w * len(indexes), h + 120), (20, 24, 31))
        draw = ImageDraw.Draw(sheet)
        for column, index in enumerate(indexes):
            x = column * w
            draw.text((x + 14, 12), labels[index], font=title, fill="white")
            draw.text((x + 14, 47), notes[index], font=body, fill=(184, 196, 208))
            sheet.paste(images[index], (x, 80))
        draw.text(
            (14, h + 91),
            "Same display: XYZ * 0.5 + 0.5 | Qualitative comparison; no ground-truth normals",
            font=body,
            fill="white",
        )
        sheet.save(root / filename)
    crops = ["Figures", "Icing / surface details", "Rose petals"]
    boxes = [(150, 65, 370, 265), (140, 265, 380, 455), (0, 610, 200, 795)]
    tile_w, tile_h = 500, 460
    detail = Image.new("RGB", (tile_w * 3, 65 + tile_h * 3), (20, 24, 31))
    draw = ImageDraw.Draw(detail)
    for col, label in enumerate(labels[:3]):
        draw.text((col * tile_w + 14, 18), label, font=title, fill="white")
    for row, (caption, box) in enumerate(zip(crops, boxes)):
        for col, image in enumerate(images[:3]):
            crop = image.crop(box)
            crop = crop.resize((crop.width * 2, crop.height * 2), Image.Resampling.NEAREST)
            x, y = col * tile_w + 14, 65 + row * tile_h
            draw.text((x, y), caption + " / 2x pixels", font=body, fill="white")
            detail.paste(crop, (x, y + 34))
    detail.save(root / "details.png")
    print("COMPARISON_SHEETS_OK", root)


if __name__ == "__main__":
    main()
