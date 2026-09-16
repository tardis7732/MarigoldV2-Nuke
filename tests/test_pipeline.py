import json
import os
import socket
import struct
import subprocess
import sys
import threading
import time
from pathlib import Path

import numpy as np
import pytest
from fake_daemon import FixtureBackend
from image_ops import depth_planes, inference_size, normal_planes, prepare_rgb
from marigold_daemon import Engine, Server
from protocol import ProtocolError, pack_reply, read_request, request

ROOT = Path(__file__).resolve().parents[1]


def wait_ready(port, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return request({"cmd": "info"}, port=port, timeout=0.3)[0]
        except OSError:
            time.sleep(0.05)
    raise AssertionError("Test engine did not start")


@pytest.fixture
def server():
    engine = Engine(FixtureBackend())
    s = Server(engine, port=0, idle_timeout=15)
    t = threading.Thread(target=s.serve, daemon=True)
    t.start()
    deadline = time.monotonic() + 3
    while not s.port and time.monotonic() < deadline:
        time.sleep(0.01)
    wait_ready(s.port)
    yield s
    s.stop.set()
    t.join(timeout=3)
    assert not t.is_alive()


def test_image_math():
    assert inference_size(1920, 1080, 512) == (512, 288)
    assert inference_size(1080, 1920, 512) == (288, 512)
    assert inference_size(1919, 1081, 0) == (1920, 1088)
    with pytest.raises(ValueError):
        inference_size(1920, 1080, 8)
    values = np.array([0.0, 0.0031308, 0.18, 1.0], np.float32)
    np.testing.assert_allclose(
        prepare_rgb(values, "linear_srgb"), [0, 0.04044994, 0.4613561, 1], atol=1e-6
    )
    with pytest.raises(ValueError):
        prepare_rgb(values, "acescg")
    n = normal_planes(np.array([3, 4, 0], np.float32).reshape(3, 1, 1), (0, 1, 0))
    np.testing.assert_allclose(n[:, 0, 0], [0.6, -0.8, 0, 1])
    with pytest.raises(ValueError):
        normal_planes(np.zeros((3, 1, 1)))


@pytest.mark.parametrize(
    "header,length",
    [
        ({"cmd": "infer", "width": -1, "height": 10}, 0),
        ({"cmd": "infer", "width": 999999999, "height": 1}, 0),
        ({"cmd": "infer", "width": True, "height": 1}, 0),
        ({"cmd": "infer", "width": 1, "height": 1}, 11),
        ({"cmd": "info"}, 4),
        (["not an object"], 0),
        ({"cmd": "unknown"}, 0),
    ],
)
def test_reject_malformed_request(header, length):
    a, b = socket.socketpair()
    try:
        body = json.dumps(header).encode()
        a.sendall(b"MGV2" + struct.pack("<I", len(body)) + body + struct.pack("<I", length))
        b.settimeout(0.5)
        with pytest.raises(ProtocolError):
            read_request(b)
    finally:
        a.close()
        b.close()


def test_fragmented_packet():
    a, b = socket.socketpair()
    body = json.dumps({"cmd": "infer", "width": 1, "height": 1}).encode()
    packet = b"MGV2" + struct.pack("<I", len(body)) + body + struct.pack("<I", 12) + bytes(12)

    def send():
        for byte in packet:
            a.sendall(bytes([byte]))

    t = threading.Thread(target=send)
    t.start()
    try:
        header, data = read_request(b)
        assert header["width"] == 1 and len(data) == 12
    finally:
        t.join()
        a.close()
        b.close()


def test_round_trip_and_error_recovery(server):
    rgb = np.random.default_rng(4).random((9, 13, 3), dtype=np.float32)
    header = {"cmd": "infer", "width": 13, "height": 9, "flip_y": 1}
    metadata, data = request(header, rgb.astype("<f4").tobytes(), port=server.port)
    expected = normal_planes(FixtureBackend().predict(rgb, (16, 16), 2025), (0, 1, 0))
    np.testing.assert_array_equal(np.frombuffer(data, "<f4").reshape(4, 9, 13), expected)
    assert metadata["requests"] == 1
    with pytest.raises(RuntimeError, match="Seed"):
        request({**header, "seed": -1}, rgb.tobytes(), port=server.port)
    assert request({"cmd": "info"}, port=server.port)[0]["requests"] == 1


def test_depth_preserves_range_and_ignores_normal_axis_flips(server):
    rgb = np.random.default_rng(8).random((9, 13, 3), dtype=np.float32)
    header = {"cmd": "infer", "width": 13, "height": 9, "task": "depth",
              "flip_x": 1, "flip_y": 1, "flip_z": 1}
    meta, data = request(header, rgb.tobytes(), port=server.port)
    expected = depth_planes(FixtureBackend().predict(rgb, (16, 16), 2025, task="depth"))
    assert expected[0].min() < 0 and expected[0].max() > 1
    np.testing.assert_array_equal(np.frombuffer(data, "<f4").reshape(4, 9, 13), expected)
    assert meta["task"] == "depth"
    with pytest.raises(RuntimeError, match="Task"):
        request({**header, "task": "unknown"}, rgb.tobytes(), port=server.port)


def test_client_refuses_legacy_normals_as_depth():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        def send():
            with listener.accept()[0] as conn:
                read_request(conn)
                conn.sendall(pack_reply(0, {}, 1, 1, 4, bytes(16)))
        thread = threading.Thread(target=send)
        thread.start()
        try:
            with pytest.raises(ProtocolError):
                request({"cmd": "infer", "width": 1, "height": 1, "task": "depth"}, bytes(12), port=port)
        finally:
            thread.join(timeout=3)


@pytest.mark.parametrize(
    "bad_reply",
    [
        pack_reply(0, {}, 1, 1, 4, b"x"),
        struct.pack("<4siIIII", b"MGN2", 0, 1, 1, 4, 65537),
    ],
)
def test_client_rejects_bad_reply(bad_reply):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]

        def send():
            with listener.accept()[0] as conn:
                read_request(conn)
                conn.sendall(bad_reply)

        t = threading.Thread(target=send)
        t.start()
        with pytest.raises(ProtocolError):
            request({"cmd": "infer", "width": 1, "height": 1}, bytes(12), port=port)
        t.join()


def test_compiled_ofx_roundtrip_and_cache(server, tmp_path):
    build = Path(os.environ.get("MARIGOLD_OFX_BUILD_DIR", ROOT / "ofx/build"))
    host = build / "tests/mini_host.exe"
    plugin = build / "MarigoldV2Normals.ofx.bundle/Contents/Win64/MarigoldV2Normals.ofx"
    assert plugin.is_file() and host.is_file(), "Build the OFX before running integration tests"
    h, w = 19, 31
    rgb = np.random.default_rng(17).random((h, w, 3), dtype=np.float32)
    src, dst, dst2 = (tmp_path / name for name in ("src.rgb", "out.rgba", "out2.rgba"))
    rgb.astype("<f4").tofile(src)
    result = subprocess.run(
        [
            str(host),
            str(plugin),
            str(src),
            str(w),
            str(h),
            str(dst),
            "out2=" + str(dst2),
            f"port={server.port}",
            "autoStart=0",
            "inputColorspace=1",
            "flipY=1",
        ],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    expected = normal_planes(FixtureBackend().predict(rgb, (32, 16), 2025), (0, 1, 0)).transpose(
        1, 2, 0
    )
    np.testing.assert_array_equal(np.fromfile(dst, "<f4").reshape(h, w, 4), expected)
    assert dst.read_bytes() == dst2.read_bytes()
    assert server.engine.count == 1, "The identical second render should use the OFX cache"
    assert f"RoI for a 10x10 request -> source 0,0 {w},{h}".encode() in result.stdout


def test_launcher_parent_lifecycle(tmp_path):
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    profile = tmp_path / "launcher.json"
    profile.write_text(
        json.dumps({"command": [sys.executable, str(ROOT / "tests/fake_daemon.py")]})
    )
    parent = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    launcher = subprocess.Popen(
        [
            sys.executable,
            str(ROOT / "daemon/launcher.py"),
            "--config",
            str(profile),
            "--port",
            str(port),
            "--parent-pid",
            str(parent.pid),
        ]
    )
    try:
        wait_ready(port)
        parent.terminate()
        parent.wait(timeout=3)
        assert launcher.wait(timeout=10) == 0
        with pytest.raises(OSError):
            request({"cmd": "info"}, port=port, timeout=0.5)
    finally:
        for proc in (launcher, parent):
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=3)


def test_ofx_cancel_startup_wait_allows_retry(server, tmp_path, monkeypatch):
    build = Path(os.environ.get("MARIGOLD_OFX_BUILD_DIR", ROOT / "ofx/build"))
    host = build / "tests/mini_host.exe"
    plugin = build / "MarigoldV2Normals.ofx.bundle/Contents/Win64/MarigoldV2Normals.ofx"
    delayed = tmp_path / "delayed_start.py"
    delayed.write_text("import time; time.sleep(8)\n", encoding="utf-8")
    src, dst, retry = (tmp_path / n for n in ("src.rgb", "cancel.rgba", "retry.rgba"))
    rgb = np.full((16, 16, 3), 0.25, dtype="<f4")
    rgb.tofile(src)
    monkeypatch.setenv("MARIGOLD_TEST_ABORT_AT", "2")
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        unused_port = reserved.getsockname()[1]
        result = subprocess.run(
            [str(host), str(plugin), str(src), "16", "16", str(dst),
             f"port={unused_port}", "autoStart=1", "exitWithHost=0",
             f"pythonExe={sys.executable}", f"daemonScript={delayed}",
             f"out2={retry}", f"next.port={server.port}", "next.autoStart=0"],
            capture_output=True, timeout=20,
        )
    assert result.returncode == 0, result.stdout + result.stderr
    assert b"host cancelled daemon startup wait" in result.stderr
    assert b"plugin message" not in result.stderr
    assert server.engine.count == 1
    expected = normal_planes(FixtureBackend().predict(rgb, (16, 16), 2025), (0, 0, 0))
    np.testing.assert_array_equal(
        np.fromfile(retry, "<f4").reshape(16, 16, 4), expected.transpose(1, 2, 0)
    )


@pytest.mark.parametrize("knob,value", [("seed", 123), ("resolution", 768), ("cacheRevision", 1), ("outputMode", 1)])
def test_ofx_inference_knobs_invalidate_cache(server, tmp_path, knob, value):
    build = Path(os.environ.get("MARIGOLD_OFX_BUILD_DIR", ROOT / "ofx/build"))
    host = build / "tests/mini_host.exe"
    plugin = build / "MarigoldV2Normals.ofx.bundle/Contents/Win64/MarigoldV2Normals.ofx"
    src, dst, dst2 = (tmp_path / n for n in ("src.rgb", "a.rgba", "b.rgba"))
    np.full((16, 16, 3), 0.25, dtype="<f4").tofile(src)
    result = subprocess.run(
        [
            str(host),
            str(plugin),
            str(src),
            "16",
            "16",
            str(dst),
            "out2=" + str(dst2),
            f"port={server.port}",
            "autoStart=0",
            f"next.{knob}={value}",
        ],
        capture_output=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert server.engine.count == 2
