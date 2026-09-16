"""Run with Nuke -t while the explicit synthetic test server is listening."""

import math
import os
import sys
from pathlib import Path

import nuke

root = Path(__file__).resolve().parents[1]
port = int(os.environ["MARIGOLD_TEST_PORT"])
out = root / "output/nuke-smoke"
out.mkdir(parents=True, exist_ok=True)
nuke.scriptClear()
nuke.addFormat("64 48 0 0 64 48 1 smoke")
nuke.root()["format"].setValue("smoke")
nuke.frame(1)
source = nuke.nodes.Constant()
source["color"].setValue([0.2, 0.4, 0.8, 1])
node = nuke.createNode("OFXorg.marigoldv2.normals_v1", inpanel=False)
node.setInput(0, source)
node["autoStart"].setValue(False)
node["port"].setValue(port)
node["inputColorspace"].setValue(1)
write = nuke.nodes.Write(
    inputs=[node], file=str(out / "synthetic.exr").replace("\\", "/"), file_type="exr"
)
write["channels"].setValue("rgba")
write["datatype"].setValue("32 bit float")
write["raw"].setValue(True)
nuke.execute(write, 1, 1)
readback = nuke.nodes.Read(file=str(out / "synthetic.exr").replace("\\", "/"), raw=True)
length = math.sqrt(0.6**2 + 0.2**2 + 0.65**2)
expected = [-0.6 / length, -0.2 / length, 0.65 / length, 1.0]
for x, y in [(0.5, 0.5), (32.5, 24.5), (63.5, 47.5)]:
    for channel, value in zip(("red", "green", "blue", "alpha"), expected):
        actual = readback.sample(channel, x, y)
        assert math.isclose(actual, value, abs_tol=1e-5), (channel, actual, value)
print("MARIGOLD_PIXELS_OK", "NukeX:", nuke.env.get("nukex", "unknown"))

sys.path.insert(0, str(root / "nuke"))
import marigold_nuke  # noqa: E402

group = marigold_nuke.create()
assert group is not None
group.setInput(0, source)
engine = group.node("INFERENCE")
engine["autoStart"].setValue(False)
engine["port"].setValue(port)
engine["inputColorspace"].setValue(1)
group["outputMode"].setValue(1)
assert engine["outputMode"].getValue() == 1
for red, expected_depth in ((0.2, -1.2), (0.9, 1.6)):
    source["color"].setValue([red, 0.4, 0.8, 1])
    engine["flipX"].setValue(True)
    engine["flipY"].setValue(True)
    engine["flipZ"].setValue(True)
    write.setInput(0, group)
    path = str(out / f"depth-{red}.exr").replace("\\", "/")
    write["file"].setValue(path)
    write["channels"].setValue("all")
    nuke.execute(write, 1, 1)
    result = nuke.nodes.Read(file=path, raw=True)
    assert "depth.Z" in result.channels(), result.channels()
    for channel in ("red", "green", "blue", "depth.Z"):
        assert math.isclose(result.sample(channel, 32.5, 24.5), expected_depth, abs_tol=1e-5)
group["outputMode"].setValue(0)
assert math.isclose(sum(group.sample(c, 32.5, 24.5)**2 for c in ("red", "green", "blue")), 1, abs_tol=1e-5)
nuke.scriptSave(str(out / "unified.nk"))
nuke.scriptClear()
nuke.scriptOpen(str(out / "unified.nk"))
restored = nuke.toNode("MarigoldV2")
restored["outputMode"].setValue(1)
assert math.isclose(restored.sample("depth.Z", 32.5, 24.5), 1.6, abs_tol=1e-5)
print("MARIGOLD_DEPTH_CHANNEL_AND_REOPEN_OK")
print("MARIGOLD_NUKE_SMOKE_OK", restored.Class(), sorted(restored.knobs()))
nuke.scriptSave(str(out / "synthetic.nk"))
