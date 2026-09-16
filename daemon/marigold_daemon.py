"""Loopback-only resident Marigold V2 normals and depth engine."""

import argparse
import logging
import os
import socket
import threading
import time

import numpy as np
from image_ops import depth_planes, inference_size, normal_planes, prepare_rgb
from protocol import PORT, ProtocolError, dimensions, pack_reply, read_request

LOG = logging.getLogger("marigold")


class Engine:
    def __init__(self, backend):
        self.backend = backend
        self.lock = threading.Lock()
        self.count = 0
        self.state = "ready; model loads on first inference"
        self.last_error = None

    def info(self):
        return {
            "engine": "Marigold V2 Normals + Depth",
            "protocol": 1,
            "tasks": ["normals", "depth"],
            "pid": os.getpid(),
            "state": self.state,
            "requests": self.count,
            "last_error": self.last_error,
            "gpu_metrics": getattr(self.backend, "metrics", {}),
        }

    def infer(self, header, data):
        w, h = dimensions(header)
        task = header.get("task", "normals")
        if task not in ("normals", "depth"):
            raise ProtocolError("Task must be normals or depth")
        seed = header.get("seed", 2025)
        if type(seed) is not int or not 0 <= seed <= 2147483647:
            raise ProtocolError("Seed must be an integer in [0,2147483647]")
        size = inference_size(w, h, header.get("resolution", 512))
        flips = [header.get("flip_" + axis, 0) for axis in "xyz"]
        if any(type(f) not in (int, bool) or f not in (0, 1) for f in flips):
            raise ProtocolError("Axis flips must be 0 or 1")
        if len(data) != w * h * 12:
            raise ProtocolError("RGB length mismatch")
        rgb = np.frombuffer(data, dtype="<f4").reshape(h, w, 3)
        rgb = prepare_rgb(rgb, header.get("input_colorspace", "srgb"))
        with self.lock:
            started = time.monotonic()
            self.state = "loading / inferring"
            try:
                prediction = self.backend.predict(rgb, size, seed, task=task)
                if prediction.shape != (3 if task == "normals" else 1, h, w):
                    raise ValueError("Backend output must match source dimensions")
                planes = normal_planes(prediction, flips) if task == "normals" else depth_planes(prediction)
                self.count += 1
                self.last_error = None
                self.state = "model resident"
                elapsed = time.monotonic() - started
                return {
                    "elapsed_seconds": elapsed,
                    "inference_size": size,
                    "source_size": [w, h],
                    "seed": seed,
                    "requests": self.count,
                    "task": task,
                    "representation": "camera_normals" if task == "normals" else "affine_invariant_log_depth",
                }, planes.tobytes()
            except Exception as exc:
                self.last_error = str(exc)
                self.state = "error; see last_error"
                raise


class Server:
    def __init__(self, engine, port=PORT, idle_timeout=300):
        self.engine = engine
        self.port = port
        self.idle_timeout = idle_timeout
        self.stop = threading.Event()
        self.slots = threading.BoundedSemaphore(8)
        self.last_activity = time.monotonic()
        self.active = 0
        self.state_lock = threading.Lock()

    def handle(self, conn):
        try:
            conn.settimeout(600)
            with conn:
                while not self.stop.is_set():
                    try:
                        header, data = read_request(conn)
                    except (ConnectionError, socket.timeout):
                        return
                    except ProtocolError as exc:
                        conn.sendall(pack_reply(2, {"error": str(exc)}))
                        return  # framing cannot be trusted after an invalid request
                    with self.state_lock:
                        self.active += 1
                    try:
                        cmd = header["cmd"]
                        if cmd == "infer":
                            meta, payload = self.engine.infer(header, data)
                            w, h = dimensions(header)
                            conn.sendall(pack_reply(0, meta, w, h, 4, payload))
                            LOG.info("Frame %dx%d: %.2fs", w, h, meta["elapsed_seconds"])
                        elif cmd == "info":
                            conn.sendall(pack_reply(0, self.engine.info()))
                        else:
                            conn.sendall(pack_reply(0, {"state": "stopping"}))
                            self.stop.set()
                            return
                    except Exception as exc:
                        LOG.exception("Request failed")
                        message = str(exc)[:10000]
                        if "out of memory" in message.lower():
                            message = (
                                "GPU memory exhausted. Reduce inference long edge, close other GPU workloads, "
                                "then restart the engine. Model loading also needs VRAM. " + message
                            )
                        conn.sendall(pack_reply(1, {"error": message}))
                    finally:
                        with self.state_lock:
                            self.active -= 1
                            self.last_activity = time.monotonic()
        except OSError:
            LOG.debug("Client disconnected", exc_info=True)
        finally:
            self.slots.release()

    def serve(self):
        with socket.socket() as listener:
            if os.name == "nt":
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            else:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            listener.bind(("127.0.0.1", self.port))
            self.port = listener.getsockname()[1]
            listener.listen(8)
            listener.settimeout(0.5)
            LOG.info("Listening on 127.0.0.1:%d", self.port)
            while not self.stop.is_set():
                try:
                    conn, _ = listener.accept()
                except socket.timeout:
                    with self.state_lock:
                        idle = (
                            not self.active
                            and time.monotonic() - self.last_activity > self.idle_timeout
                        )
                    if self.idle_timeout and idle:
                        return
                    continue
                if not self.slots.acquire(blocking=False):
                    conn.close()
                    continue
                threading.Thread(target=self.handle, args=(conn,), daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--assets", required=True)
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--idle-timeout", type=int, default=300)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535 or args.idle_timeout < 0:
        parser.error("Invalid port or idle timeout")
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from backend import MarigoldBackend

    Server(Engine(MarigoldBackend(args.repo, args.assets)), args.port, args.idle_timeout).serve()


if __name__ == "__main__":
    main()
