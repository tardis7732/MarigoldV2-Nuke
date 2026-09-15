"""Nuke -i -t: render a 48-frame video through the actual OFX model."""

import json
import time
from pathlib import Path

from build_example_nuke import note, place
from build_ready_example import preview

import nuke

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "examples/video_demo"
DEST = BASE / "MarigoldV2_Video_Example.nk"
COUNT = 48


def read_sequence(name, file, x, y):
    node = place(nuke.nodes.Read(), name, x, y)
    node["file"].setValue("[file dirname [value root.name]]/" + file)
    node["raw"].setValue(True)
    for knob in ("first", "origfirst"):
        node[knob].setValue(1)
    for knob in ("last", "origlast"):
        node[knob].setValue(COUNT)
    return node


def main():
    (BASE / "normals").mkdir(exist_ok=True)
    nuke.scriptClear()
    nuke.root()["name"].setValue(DEST.as_posix())
    nuke.root()["first_frame"].setValue(1)
    nuke.root()["last_frame"].setValue(COUNT)
    nuke.root()["fps"].setValue(12)
    nuke.root()["colorManagement"].setValue("Nuke")
    nuke.addFormat("432 768 0 0 432 768 1 MarigoldVideo")
    nuke.root()["format"].setValue("MarigoldVideo")
    nuke.frame(1)
    note(
        "Guide",
        -340,
        -230,
        "<b>MARIGOLD V2 / VIDEO EXAMPLE</b>\n"
        "4 seconds / 12 fps / frames 1-48 / inference long edge 512\n"
        "Viewer 1 = rendered normals / 2 = source / 3 = live inference\n"
        "Frame-independent model; temporal flicker may occur.\n"
        "Source: Airam Dato-on / Pexels 35958383 (see README.md)",
        1060,
        200,
        0x253548FF,
    )
    source = read_sequence("INPUT_VIDEO", "source/source.%04d.png", 300, 80)
    normal = place(
        nuke.createNode("OFXorg.marigoldv2.normals_v1", inpanel=False),
        "MARIGOLD_NORMALS",
        300,
        220,
        "512 / seed 2025 / signed XYZ",
        0x65AA8EFF,
    )
    normal.setInput(0, source)
    for key, value in {
        "resolution": 512,
        "seed": 2025,
        "inputColorspace": 1,
        "autoStart": True,
        "port": 47822,
        "flipX": False,
        "flipY": False,
        "flipZ": False,
    }.items():
        normal[key].setValue(value)
    live = preview(normal, "LIVE_PREVIEW", 230, 360)
    write = place(nuke.nodes.Write(), "WRITE_LIVE_NORMALS", 510, 360)
    write.setInput(0, normal)
    write["file"].setValue("[file dirname [value root.name]]/normals/normals.%04d.exr")
    write["file_type"].setValue("exr")
    write["channels"].setValue("rgba")
    write["datatype"].setValue("32 bit float")
    write["raw"].setValue(True)
    nuke.scriptSave(DEST.as_posix())
    timings = []
    for frame in range(1, COUNT + 1):
        nuke.frame(frame)
        started = time.monotonic()
        nuke.execute(write, frame, frame)
        timings.append(time.monotonic() - started)
        (BASE / "progress.json").write_text(
            json.dumps({"complete": frame, "total": COUNT, "frame_seconds": timings}, indent=2),
            encoding="utf-8",
        )
        print(f"VIDEO_FRAME_OK {frame}/{COUNT} {timings[-1]:.2f}s", flush=True)
    saved = read_sequence("SAVED_NORMALS", "normals/normals.%04d.exr", -150, 80)
    saved_preview = preview(saved, "SAVED_PREVIEW", -150, 360)
    viewer = place(nuke.nodes.Viewer(), "VIEW_VIDEO", 30, 540, "1 saved / 2 source / 3 live")
    for index, node in enumerate((saved_preview, source, live)):
        viewer.setInput(index, node)
    viewer["input_number"].setValue(0)
    viewer["viewerProcess"].setValue("None")
    nuke.frame(1)
    for node in nuke.allNodes():
        node["selected"].setValue(False)
    nuke.scriptSave(DEST.as_posix())
    nuke.scriptClear()
    nuke.scriptOpen(DEST.as_posix())
    assert nuke.root()["last_frame"].value() == COUNT
    assert nuke.toNode("VIEW_VIDEO").input(0).name() == "SAVED_PREVIEW"
    for frame in (1, COUNT):
        nuke.frame(frame)
        assert nuke.toNode("SAVED_NORMALS").width() == 432
        assert abs(nuke.toNode("SAVED_NORMALS").sample("alpha", 200, 300) - 1) < 1e-6
    print("MARIGOLD_VIDEO_RENDER_OK", sum(timings), flush=True)


if __name__ == "__main__":
    main()
