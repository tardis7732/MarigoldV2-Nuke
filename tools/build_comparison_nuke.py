"""Build and reopen the portable, baked one-image model comparison in Nuke."""

import math
import re
from pathlib import Path

import nuke

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "examples/model_comparison/Normals_Comparison.nk"

nuke.scriptClear()
nuke.root()["name"].setValue(DEST.as_posix())
nuke.addFormat("547 800 0 0 547 800 1 ModelComparison")
nuke.root()["format"].setValue("ModelComparison")
nuke.root()["first_frame"].setValue(1)
nuke.root()["last_frame"].setValue(1)
nuke.root()["colorManagement"].setValue("Nuke")
viewer = nuke.nodes.Viewer(name="VIEW_COMPARISON", xpos=500, ypos=300)
viewer["viewerProcess"].setValue("None")

for i, (name, filename, label) in enumerate(
    [
        ("SOURCE", "sample.jpg", "MoGe-nuke README sample / sRGB"),
        ("MOGE3", "moge3.exr", "MoGe-3 / level 9 / refine 3 / Nuke axes"),
        ("MARIGOLD_NATIVE", "marigold_native.exr", "Marigold V2 / 544 x 800 / seed 2025"),
    ]
):
    read = nuke.nodes.Read(name=name, xpos=i * 260, ypos=0)
    read["file"].setValue("[file dirname [value root.name]]/" + filename)
    read["raw"].setValue(True)
    read["label"].setValue(label)
    read["first"].setValue(1)
    read["last"].setValue(1)
    displayed = read
    if i:
        displayed = nuke.nodes.Expression(name=name + "_PREVIEW", xpos=i * 260, ypos=140)
        displayed.setInput(0, read)
        for k, channel in enumerate("rgb"):
            displayed["expr" + str(k)].setValue(f"a > 0.5 ? {channel}*0.5+0.5 : 0")
        displayed["expr3"].setValue("1")
        displayed["label"].setValue("Display XYZ * 0.5 + 0.5; mask invalid pixels")
    viewer.setInput(i, displayed)

note = nuke.nodes.StickyNote(name="COMPARISON_GUIDE", xpos=-200, ypos=-220)
note["label"].setValue(
    "BAKED CLOUD RESULTS / ONE IMAGE\n"
    "Viewer 1: source / 2: MoGe-3 / 3: Marigold V2 native\n"
    "Select A/B Viewer inputs to wipe. Viewer process: None.\n"
    "Read EXRs store signed XYZ; Expressions are display only.\n"
    "No live model loading. No ground-truth normals for this photograph."
)
note["note_font_size"].setValue(22)
viewer["input_number"].setValue(2)
nuke.frame(1)
nuke.scriptSaveAs(DEST.as_posix(), overwrite=1)
content = DEST.read_text(encoding="utf-8")
content = (
    "\n".join(
        line
        for line in content.splitlines()
        if not line.startswith(("#!", "#write_info"))
        and not re.match(r"^ name [A-Za-z]:[/\\]", line)
    )
    + "\n"
)
DEST.write_text(content, encoding="utf-8")
nuke.scriptClear()
nuke.scriptOpen(DEST.as_posix())
nuke.frame(1)
for name in ("MOGE3", "MARIGOLD_NATIVE"):
    read = nuke.toNode(name)
    assert read.width() == 547 and read.height() == 800
    for x, y in ((270, 400), (200, 620), (100, 100)):
        xyz = [read.sample(channel, x, y) for channel in ("red", "green", "blue")]
        assert all(math.isfinite(value) for value in xyz)
        if read.sample("alpha", x, y) > 0.5:
            assert abs(sum(value * value for value in xyz) - 1) < 0.001
print("NUKE_COMPARISON_OK", DEST.as_posix(), flush=True)
