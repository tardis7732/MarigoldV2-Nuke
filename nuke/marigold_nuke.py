"""Nuke menu helpers. Uses only the standard library and Nuke."""

import importlib.util
import json
import os
import subprocess
from pathlib import Path

import nuke

ROOT = Path(__file__).resolve().parents[1]
CLASS = "OFXorg.marigoldv2.normals_v1"
_spec = importlib.util.spec_from_file_location("marigold_wire", ROOT / "daemon/protocol.py")
_wire = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_wire)


def _engine(node):
    if node.Class() == CLASS:
        return node
    if node.Class() == "Group" and node.knob("marigoldAdapter"):
        return node.node("INFERENCE")
    return None


def selected_port():
    nodes = [engine for n in nuke.selectedNodes() if (engine := _engine(n)) is not None]
    return int(nodes[0]["port"].value()) if nodes else _wire.PORT


def create():
    """One user node, one selected task. Native OFX handles inference/cache.

    The serializable Nuke wrapper adds depth.Z; OFX itself transports RGBA.
    Old standalone OFX nodes continue to work and default to normals.
    """
    try:
        upstream = nuke.selectedNode() if nuke.selectedNodes() else None
        group = nuke.nodes.Group(name="MarigoldV2")
        group.addKnob(nuke.Tab_Knob("marigold", "Marigold V2"))
        marker = nuke.Boolean_Knob("marigoldAdapter", "")
        marker.setVisible(False)
        group.addKnob(marker)
        group.begin()
        try:
            source = nuke.nodes.Input(name="Source")
            engine = nuke.createNode(CLASS, inpanel=False)
            engine.setName("INFERENCE")
            engine.setInput(0, source)
            depth = nuke.nodes.Copy(name="DEPTH_CHANNEL", inputs=[engine, engine])
            depth["from0"].setValue("rgba.red")
            depth["to0"].setValue("depth.Z")
            depth["disable"].setExpression("parent.INFERENCE.outputMode != 1")
            nuke.nodes.Output(inputs=[depth])
        finally:
            group.end()
        for name, label in (
            ("outputMode", "output"), ("resolution", "processing resolution"),
            ("seed", "seed"), ("inputColorspace", "input colorspace"),
            ("flipX", "flip normal X"), ("flipY", "flip normal Y"),
            ("flipZ", "flip normal Z"), ("cacheRevision", "cache revision"),
        ):
            knob = nuke.Link_Knob(name, label)
            knob.makeLink("INFERENCE", name)
            group.addKnob(knob)
        group.addKnob(nuke.Text_Knob("outputHelp", "",
            "Normals: signed XYZ in RGB.\n"
            "Depth: raw relative log-depth in RGB and depth.Z.\n"
            "Depth increases with distance; it is not measured in metres.\n"
            "Only the selected task is evaluated. Axis flips affect normals only."))
        group.addKnob(nuke.Tab_Knob("setup", "Setup"))
        for name in ("pythonExe", "daemonScript", "port", "autoStart", "exitWithHost"):
            knob = nuke.Link_Knob(name, engine[name].label())
            knob.makeLink("INFERENCE", name)
            group.addKnob(knob)
        if upstream is not None:
            group.setInput(0, upstream)
        if nuke.GUI:
            group.showControlPanel()
        return group
    except Exception as exc:
        if not nuke.GUI:
            raise
        nuke.message(
            "Marigold V2 OFX is not loaded. Run install.ps1 and restart Nuke.\n" + str(exc)
        )


def status():
    try:
        meta, _ = _wire.request({"cmd": "info"}, port=selected_port(), timeout=3)
        nuke.message(json.dumps(meta, indent=2, ensure_ascii=False))
    except Exception as exc:
        nuke.message("Engine is not available:\n" + str(exc))


def start():
    settings = json.loads((ROOT / "config/frontend.json").read_text(encoding="utf-8-sig"))
    env = dict(os.environ)
    for key in ("PYTHONHOME", "PYTHONPATH", "PYTHONEXECUTABLE", "PYTHONSTARTUP"):
        env.pop(key, None)
    subprocess.Popen(
        [
            settings["python"],
            str(ROOT / "daemon/launcher.py"),
            "--port",
            str(selected_port()),
            "--parent-pid",
            str(os.getpid()),
        ],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    print("[Marigold V2] Starting engine; check Engine/Status and output/daemon.log")


def clear_cache():
    for selected in nuke.selectedNodes():
        node = _engine(selected)
        if node is not None:
            knob = node["cacheRevision"]
            knob.setValue(int(knob.value()) + 1)


def stop():
    try:
        _wire.request({"cmd": "shutdown"}, port=selected_port(), timeout=3)
        clear_cache()
    except Exception as exc:
        nuke.message("Could not stop engine:\n" + str(exc))
