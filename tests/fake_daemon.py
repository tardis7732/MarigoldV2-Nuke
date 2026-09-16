"""Synthetic test fixture. Never selected by the production launcher."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "daemon"))
from marigold_daemon import Engine, Server


class FixtureBackend:
    def predict(self, rgb, size, seed, task="normals"):
        if task == "depth":
            # Negative and >1 values ensure depth is not clipped, normalized, or flipped.
            return rgb[:, :, 0][None].copy() * 4 - 2
        # Vary all axes across the image to expose channel swaps and row reversal.
        out = rgb.transpose(2, 0, 1).copy() * 2 - 1
        out[2] = out[2] * 0.25 + 0.5
        return out


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--idle-timeout", type=int, default=15)
    args = p.parse_args()
    Server(Engine(FixtureBackend()), args.port, args.idle_timeout).serve()
