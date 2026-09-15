"""Create and reopen the example graph with Nuke -i -t."""

from pathlib import Path

import nuke

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/MarigoldV2_Normals_Example.nk"


def place(node, name, x, y, label="", color=None):
    node.setName(name)
    node.setXYpos(x, y)
    node["label"].setValue(label)
    if color is not None:
        node["tile_color"].setValue(color)
    return node


def note(name, x, y, text, width, height, color):
    node = nuke.nodes.BackdropNode()
    place(node, name, x, y, text, color)
    node["bdwidth"].setValue(width)
    node["bdheight"].setValue(height)
    node["note_font_size"].setValue(20)
    node["z_order"].setValue(-1)
    return node


def main():
    nuke.scriptClear()
    nuke.root()["name"].setValue(str(EXAMPLE).replace("\\", "/"))
    nuke.frame(1)
    nuke.root()["first_frame"].setValue(1)
    nuke.root()["last_frame"].setValue(1)
    nuke.root()["colorManagement"].setValue("Nuke")

    note(
        "Guide",
        -380,
        -220,
        "<b>MARIGOLD V2 / NORMALS</b>\n"
        "1. Replace INPUT_IMAGE with your sRGB image.\n"
        "2. Configure the engine, then view input 2.\n"
        "3. Render WRITE_NORMALS_EXR for signed XYZ.\n"
        "Viewer: 1 = source / 2 = preview / 3 = signed XYZ\n"
        "Model setup is required; this file contains no generated normals.",
        1020,
        195,
        0x253548FF,
    )
    note(
        "InputArea",
        -180,
        0,
        "<b>01 / sRGB INPUT</b>\nRead is raw: preserves the JPEG's sRGB encoding.",
        610,
        210,
        0x354F61FF,
    )
    read = place(
        nuke.nodes.Read(),
        "INPUT_IMAGE",
        20,
        115,
        "Replace this image\nsRGB encoded / raw",
        0x5799BDFF,
    )
    read["file"].setValue("[file dirname [value root.name]]/assets/church.jpg")
    read["raw"].setValue(True)
    for name in ("first", "last", "origfirst", "origlast"):
        read[name].setValue(1)

    note(
        "InferenceArea",
        -180,
        240,
        "<b>02 / MARIGOLD V2 NORMALS</b>\n"
        "512 long edge / seed 2025\n"
        "Signed RGB = XYZ / alpha = 1\n"
        "For ACEScg or linear EXR, convert the input to sRGB first.",
        610,
        270,
        0x36544BFF,
    )
    normal = place(
        nuke.createNode("OFXorg.marigoldv2.normals_v1", inpanel=False),
        "MARIGOLD_NORMALS",
        20,
        405,
        "512 / seed 2025\nRGB = signed XYZ",
        0x65AA8EFF,
    )
    normal.setInput(0, read)
    normal["resolution"].setValue(512)
    normal["seed"].setValue(2025)
    normal["inputColorspace"].setValue(1)
    normal["port"].setValue(47822)
    normal["autoStart"].setValue(True)
    for name in ("flipX", "flipY", "flipZ"):
        normal[name].setValue(False)

    note(
        "PreviewArea",
        -380,
        555,
        "<b>03 / VIEW ONLY</b>\nMap XYZ -1..1 to RGB 0..1.\nThis branch is only for preview.",
        400,
        210,
        0x4D425CFF,
    )
    preview = place(
        nuke.nodes.Expression(), "NORMALS_PREVIEW", -240, 690, "XYZ * 0.5 + 0.5", 0x9E82BEFF
    )
    preview.setInput(0, normal)
    for name, expression in (
        ("expr0", "r*0.5+0.5"),
        ("expr1", "g*0.5+0.5"),
        ("expr2", "b*0.5+0.5"),
        ("expr3", "a"),
    ):
        preview[name].setValue(expression)

    note(
        "ExportArea",
        70,
        555,
        "<b>04 / NORMAL DATA</b>\nEXR / 32-bit float / raw\nSaves signed XYZ, without the preview remap.",
        550,
        210,
        0x5B4A35FF,
    )
    write = place(
        nuke.nodes.Write(),
        "WRITE_NORMALS_EXR",
        220,
        690,
        "Signed XYZ + alpha\nfloat32 / raw",
        0xB9945AFF,
    )
    write.setInput(0, normal)
    write["file"].setValue("[file dirname [value root.name]]/renders/normals.%04d.exr")
    write["file_type"].setValue("exr")
    write["channels"].setValue("rgba")
    write["datatype"].setValue("32 bit float")
    write["raw"].setValue(True)

    viewer = place(
        nuke.nodes.Viewer(),
        "VIEW_SOURCE_PREVIEW_NORMALS",
        -240,
        870,
        "1 source / 2 preview / 3 signed XYZ",
    )
    viewer.setInput(0, read)
    viewer.setInput(1, preview)
    viewer.setInput(2, normal)
    viewer["input_number"].setValue(0)
    viewer["viewerProcess"].setValue("None")
    for node in nuke.allNodes():
        node["selected"].setValue(False)
    nuke.scriptSave(str(EXAMPLE))

    # Reopen the actual deliverable: verify paths, graph connections and source pixels.
    nuke.scriptClear()
    nuke.scriptOpen(str(EXAMPLE))
    read = nuke.toNode("INPUT_IMAGE")
    normal = nuke.toNode("MARIGOLD_NORMALS")
    preview = nuke.toNode("NORMALS_PREVIEW")
    write = nuke.toNode("WRITE_NORMALS_EXR")
    viewer = nuke.toNode("VIEW_SOURCE_PREVIEW_NORMALS")
    assert Path(nuke.filename(read)).is_file(), nuke.filename(read)
    assert read.width() > 0 and read.height() > 0
    assert normal.input(0) == read
    assert preview.input(0) == normal and write.input(0) == normal
    assert int(viewer["input_number"].value()) == 0
    assert write["raw"].value() and int(normal["resolution"].value()) == 512
    assert nuke.filename(write).endswith("normals.%04d.exr"), nuke.filename(write)
    assert Path(nuke.filename(write)).parent.is_dir()
    print(
        "EXAMPLE_OK",
        str(EXAMPLE),
        "SOURCE",
        read.width(),
        read.height(),
        "PIXEL",
        read.sample("red", read.width() / 2, read.height() / 2),
    )


if __name__ == "__main__":
    main()
