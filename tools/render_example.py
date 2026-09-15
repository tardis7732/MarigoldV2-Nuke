"""Render the actual example with the configured engine: Nuke -i -t this_file.py."""

from pathlib import Path

import nuke

ROOT = Path(__file__).resolve().parents[1]
nuke.scriptOpen(str(ROOT / "examples/MarigoldV2_Normals_Example.nk"))
nuke.frame(1)
node = nuke.toNode("MARIGOLD_NORMALS")
node["cacheRevision"].setValue(int(node["cacheRevision"].value()) + 1)
nuke.execute(nuke.toNode("WRITE_NORMALS_EXR"), 1, 1)
print("MARIGOLD_REAL_RENDER_OK", str(ROOT / "examples/renders/normals.0001.exr"))
