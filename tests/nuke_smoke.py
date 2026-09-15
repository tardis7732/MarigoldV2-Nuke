"""Run with Nuke -t while the explicit synthetic test server is listening."""

import math
import os
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
print("MARIGOLD_NUKE_SMOKE_OK", node.Class(), sorted(node.knobs()))
nuke.scriptSave(str(out / "synthetic.nk"))
