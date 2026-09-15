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


def selected_port():
    nodes = [n for n in nuke.selectedNodes() if n.Class() == CLASS]
    return int(nodes[0]["port"].value()) if nodes else _wire.PORT


def create():
    try:
        return nuke.createNode(CLASS)
    except Exception as exc:
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
    for node in nuke.selectedNodes():
        if node.Class() == CLASS:
            knob = node["cacheRevision"]
            knob.setValue(int(knob.value()) + 1)


def stop():
    try:
        _wire.request({"cmd": "shutdown"}, port=selected_port(), timeout=3)
        clear_cache()
    except Exception as exc:
        nuke.message("Could not stop engine:\n" + str(exc))
