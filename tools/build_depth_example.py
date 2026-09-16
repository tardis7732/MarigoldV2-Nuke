"""Build and verify a portable depth comparison in real Nuke."""

import json
import math
import re
import sys
from pathlib import Path

import nuke

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "nuke"))
import marigold_nuke  # noqa: E402

folder = ROOT / "examples/depth_comparison"
dest = folder / "Depth_Comparison.nk"
meta = json.loads((ROOT / "docs/depth-comparison.json").read_text())
nuke.scriptClear()
nuke.root()["name"].setValue(dest.as_posix())
nuke.addFormat("547 800 0 0 547 800 1 DepthComparison")
nuke.root()["format"].setValue("DepthComparison")
nuke.root()["last_frame"].setValue(1)
nuke.root()["colorManagement"].setValue("Nuke")
viewer = nuke.nodes.Viewer(name="VIEW_DEPTH", xpos=260, ypos=480)
viewer["viewerProcess"].setValue("None")
source = nuke.nodes.Read(name="SOURCE", xpos=-260, ypos=0, raw=True)
source["file"].setValue("[file dirname [value root.name]]/sample.jpg")
viewer.setInput(0, source)
for i, model in enumerate(("moge", "marigold")):
    read = nuke.nodes.Read(name=model.upper()+"_RAW", xpos=i*300, ypos=0, raw=True)
    read["file"].setValue("[file dirname [value root.name]]/"+model+"_depth.exr")
    read["label"].setValue("Metric depth estimate" if model == "moge" else "Relative log-depth / NOT metres")
    preview = nuke.nodes.Expression(name=model.upper()+"_PREVIEW", inputs=[read], xpos=i*300, ypos=180)
    lo, hi = meta[model]["display"]["range"]
    value = "log(max(r, 0.00000001))" if model == "moge" else "r"
    expression = f"a > 0.5 ? clamp(({value}-({lo}))/({hi-lo}),0,1) : 0"
    for k in range(3):
        preview["expr"+str(k)].setValue(expression)
    preview["expr3"].setValue("1")
    preview["label"].setValue("Display only / 2-98% log-depth / far=white")
    viewer.setInput(i+1, preview)
for node in nuke.allNodes():
    node.setSelected(False)
live = marigold_nuke.create()
live.setName("MARIGOLD_LIVE")
live.setInput(0, source)
live.setXYpos(650, 0)
live["outputMode"].setValue(1)
live["resolution"].setValue(0)
live["label"].setValue("Output: Normals / Depth\nLive model runs only when evaluated")
preview = nuke.nodes.Expression(name="LIVE_DEPTH_PREVIEW", inputs=[live], xpos=650, ypos=180)
lo, hi = meta["marigold"]["display"]["range"]
for k in range(3):
    preview["expr"+str(k)].setValue(f"clamp((r-({lo}))/({hi-lo}),0,1)")
preview["label"].setValue("Display only / this sample's fixed range")
viewer.setInput(3, preview)
write = nuke.nodes.Write(name="WRITE_RAW_DEPTH", inputs=[live], xpos=920, ypos=180)
write["file"].setValue("[file dirname [value root.name]]/live_depth.exr")
write["file_type"].setValue("exr")
write["channels"].setValue("all")
write["datatype"].setValue("32 bit float")
write["raw"].setValue(True)
note = nuke.nodes.StickyNote(name="DEPTH_GUIDE", xpos=-260, ypos=-260)
note["note_font_size"].setValue(20)
note["label"].setValue(
    "DEPTH / SAME IMAGE, TWO MODELS\n"
    "Viewer 1: source / 2: MoGe-3 / 3: Marigold / 4: LIVE (loads model)\n"
    "Saved results: no model needed. Use A/B Viewer inputs for wipe.\n"
    "Both previews use log-depth with independent 2-98% ranges; far=white.\n"
    "Raw EXRs include depth.Z. Marigold depth is relative, NOT metres.\n"
    "Write from the raw node; previews are for viewing only.\n"
    "If LIVE Output changes to Normals, use XYZ*0.5+0.5 for preview."
)
viewer["input_number"].setValue(2)
nuke.scriptSaveAs(dest.as_posix(), overwrite=1)
text = dest.read_text(encoding="utf-8")
text = "\n".join(line for line in text.splitlines()
                 if not line.startswith(("#!", "#write_info"))
                 and not re.match(r"^\s+(pythonExe|daemonScript|name [A-Za-z]:[/\\])", line))+"\n"
dest.write_text(text, encoding="utf-8")
nuke.scriptClear()
nuke.scriptOpen(dest.as_posix())
for model in ("MOGE", "MARIGOLD"):
    read = nuke.toNode(model+"_RAW")
    assert "depth.Z" in read.channels()
    assert read.width() == 547 and read.height() == 800
    for x,y in ((270,400), (200,620), (100,100)):
        z = read.sample("depth.Z", x,y)
        assert math.isfinite(z) and abs(z-read.sample("red",x,y)) < 1e-6
        assert 0 <= nuke.toNode(model+"_PREVIEW").sample("red",x,y) <= 1
assert nuke.toNode("MARIGOLD_LIVE").node("INFERENCE")["outputMode"].getValue() == 1
print("DEPTH_NUKE_EXAMPLE_OK", dest, flush=True)
