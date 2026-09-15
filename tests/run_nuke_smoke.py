"""Exercise the real Nuke host using a synthetic server and an interactive license."""

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--nuke", default="C:/Program Files/Nuke17.1v1/Nuke17.1.exe")
    args = parser.parse_args()
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    server = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "tests/fake_daemon.py"),
            "--port",
            str(port),
            "--idle-timeout",
            "120",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    env = dict(os.environ)
    env["MARIGOLD_TEST_PORT"] = str(port)
    logpath = ROOT / "output/nuke-smoke-interactive.log"
    logpath.parent.mkdir(exist_ok=True)
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.3):
                    break
            except OSError:
                if time.monotonic() >= deadline or server.poll() is not None:
                    raise RuntimeError("Synthetic test server failed to start")
                time.sleep(0.05)
        with logpath.open("w", encoding="utf-8") as log:
            result = subprocess.run(
                [args.nuke, "-i", "-t", str(ROOT / "tests/nuke_smoke.py")],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=90,
            )
        print("NUKE_EXIT", result.returncode)
        text = logpath.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            if any(
                token in line
                for token in (
                    "Error",
                    "Traceback",
                    "MARIGOLD",
                    "Marigold",
                    'File "',
                    "Unrecognized",
                )
            ):
                print(line)
        if result.returncode != 0 or "MARIGOLD_NUKE_SMOKE_OK" not in text:
            raise SystemExit(1)
    finally:
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    main()
