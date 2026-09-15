"""Open portable release examples and check paths, defaults and baked pixels."""

from pathlib import Path

import nuke

ROOT = Path(__file__).resolve().parents[1]

for relative, viewer_name, source_name, last in [
    ("examples/Normals_Still.nk", "VIEW_NORMALS", "INPUT_IMAGE", 1),
    ("examples/video_demo/Normals_Video.nk", "VIEW_VIDEO", "INPUT_VIDEO", 48),
]:
    path = ROOT / relative
    text = path.read_text(encoding="utf-8")
    assert "pythonExe " not in text and "daemonScript " not in text
    nuke.scriptClear()
    nuke.scriptOpen(path.as_posix())
    normal = nuke.toNode("MARIGOLD_NORMALS")
    assert normal.Class() == "OFXorg.marigoldv2.normals_v1"
    for knob in ("pythonExe", "daemonScript"):
        assert Path(normal[knob].value()).is_file()
    assert normal.input(0) == nuke.toNode(source_name)
    assert nuke.toNode(viewer_name).input(0).name() == "SAVED_PREVIEW"
    assert int(nuke.toNode(viewer_name)["input_number"].value()) == 0
    assert int(nuke.root()["last_frame"].value()) == last
    for frame in (1, last):
        nuke.frame(frame)
        saved = nuke.toNode("SAVED_NORMALS")
        xyz = [saved.sample(c, 100, 100) for c in ("red", "green", "blue")]
        assert abs(sum(value * value for value in xyz) - 1) < 0.001
        assert saved.sample("alpha", 100, 100) == 1
    print("PORTABLE_EXAMPLE_OK", relative, flush=True)
