"""Build an example with an immediate baked preview and a live inference branch."""

from pathlib import Path

from build_example_nuke import note, place

import nuke

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "examples/MarigoldV2_Normals_Ready.nk"


def preview(source, name, x, y):
    node = place(nuke.nodes.Expression(), name, x, y, "XYZ to display RGB")
    node.setInput(0, source)
    for channel, expression in enumerate(("r*0.5+0.5", "g*0.5+0.5", "b*0.5+0.5", "a")):
        node[f"expr{channel}"].setValue(expression)
    return node


def main():
    nuke.scriptClear()
    nuke.root()["name"].setValue(DEST.as_posix())
    nuke.root()["first_frame"].setValue(1)
    nuke.root()["last_frame"].setValue(1)
    nuke.root()["colorManagement"].setValue("Nuke")
    nuke.frame(1)
    note("Guide", -330, -260,
         "<b>MARIGOLD V2 / READY EXAMPLE</b>\n"
         "Viewer 1: saved normal preview (ready now)\n"
         "Viewer 2: source image | Viewer 3: live normal preview\n"
         "To compute your image: replace INPUT_IMAGE, then press 3 in Viewer.\n"
         "Use an sRGB JPG/PNG. Live resolution: 512.\n"
         "The saved result on the left stays fixed when the input changes.",
         1120, 220, 0x253548FF)
    note("SavedResult", -330, 0, "<b>SAVED RESULT / IMMEDIATE PREVIEW</b>\nActual Marigold inference / signed XYZ EXR", 480, 490, 0x354F61FF)
    baked = place(nuke.nodes.Read(), "SAVED_NORMALS", -160, 130, "Saved church normals / raw", 0x5799BDFF)
    baked["file"].setValue("[file dirname [value root.name]]/renders/normals.0001.exr")
    baked["raw"].setValue(True)
    saved_preview = preview(baked, "SAVED_PREVIEW", -160, 360)

    note("LiveInference", 200, 0, "<b>LIVE MODEL / NEW IMAGES</b>\nReplace the Read image, then view input 3.\nConvert ACEScg / linear EXR to sRGB upstream.", 590, 490, 0x36544BFF)
    source = place(nuke.nodes.Read(), "INPUT_IMAGE", 400, 130, "Replace with your sRGB JPG/PNG / raw", 0x5799BDFF)
    source["file"].setValue("[file dirname [value root.name]]/assets/church.jpg")
    source["raw"].setValue(True)
    for read in (baked, source):
        for knob in ("first", "last", "origfirst", "origlast"):
            read[knob].setValue(1)
    live = place(nuke.createNode("OFXorg.marigoldv2.normals_v1", inpanel=False), "MARIGOLD_NORMALS", 400, 260, "512 / seed 2025 / signed XYZ", 0x65AA8EFF)
    live.setInput(0, source)
    for knob, value in {"resolution": 512, "seed": 2025, "inputColorspace": 1, "port": 47822, "autoStart": True, "flipX": False, "flipY": False, "flipZ": False}.items():
        live[knob].setValue(value)
    live_preview = preview(live, "LIVE_PREVIEW", 310, 390)
    write = place(nuke.nodes.Write(), "WRITE_LIVE_NORMALS", 610, 390, "Render signed XYZ / raw float32 EXR")
    write.setInput(0, live)
    write["file"].setValue("[file dirname [value root.name]]/renders/live_normals.%04d.exr")
    write["file_type"].setValue("exr")
    write["channels"].setValue("rgba")
    write["datatype"].setValue("32 bit float")
    write["raw"].setValue(True)
    viewer = place(nuke.nodes.Viewer(), "VIEW_NORMALS", 70, 590, "1 saved / 2 source / 3 live")
    for index, node in enumerate((saved_preview, source, live_preview)):
        viewer.setInput(index, node)
    viewer["input_number"].setValue(0)
    viewer["viewerProcess"].setValue("None")
    for node in nuke.allNodes():
        node["selected"].setValue(False)
    nuke.scriptSave(DEST.as_posix())
    nuke.scriptClear()
    nuke.scriptOpen(DEST.as_posix())
    nuke.frame(1)
    for name in ("SAVED_NORMALS", "INPUT_IMAGE"):
        assert Path(nuke.filename(nuke.toNode(name))).is_file()
    baked = nuke.toNode("SAVED_NORMALS")
    assert (baked.width(), baked.height()) == (2048, 1360)
    xyz = [baked.sample(channel, 100, 100) for channel in ("red", "green", "blue")]
    assert abs(sum(value * value for value in xyz) - 1) < 0.001, xyz
    assert nuke.toNode("VIEW_NORMALS")["input_number"].value() == 0
    assert nuke.toNode("WRITE_LIVE_NORMALS").input(0) == nuke.toNode("MARIGOLD_NORMALS")
    assert nuke.toNode("MARIGOLD_NORMALS").input(0) == nuke.toNode("INPUT_IMAGE")
    print("READY_EXAMPLE_OK", DEST, "baked XYZ", xyz)


if __name__ == "__main__":
    main()
