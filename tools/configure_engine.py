"""Write the launch command for an installed native or WSL CUDA environment."""

import argparse
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--python", required=True, help="Absolute inference Python path (Linux path for WSL)"
    )
    p.add_argument("--repo", required=True, help="Absolute installed Marigold V2 repository path")
    p.add_argument("--assets", required=True, help="Absolute model assets path")
    p.add_argument("--wsl-distro", help="Use this WSL distribution instead of native Python")
    p.add_argument("--idle-timeout", type=int, default=300)
    args = p.parse_args()
    daemon = str(ROOT / "daemon/marigold_daemon.py")
    prefix = []
    if args.wsl_distro:
        prefix = ["wsl.exe", "--distribution", args.wsl_distro, "--exec"]
        daemon = subprocess.check_output(prefix + ["wslpath", "-a", daemon], text=True).strip()
    command = prefix + [
        args.python,
        daemon,
        "--repo",
        args.repo,
        "--assets",
        args.assets,
        "--idle-timeout",
        str(args.idle_timeout),
    ]
    (ROOT / "config/launcher.json").write_text(
        json.dumps({"command": command}, indent=2) + "\n", encoding="utf-8"
    )
    print("Saved config/launcher.json. Use the Nuke menu Engine > Start.")


if __name__ == "__main__":
    main()
