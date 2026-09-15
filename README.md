# Marigold V2 Normals for Nuke

Camera-space surface normals from images and image sequences, using [Marigold V2](https://github.com/huawei-bayerlab/marigold-v2) through a native OFX node.

Connect an image, view the normals, and write signed XYZ to EXR. The model runs in an external resident Python process on the GPU; Nuke communicates with it over localhost.

**Tested:** Windows x64 · Nuke 17.1v1 · RTX 5070 Ti 16GB · inference long edge 512.

[한국어 안내](docs/README.ko.md) · [Downloads](https://github.com/tardis7732/MarigoldV2-Nuke/releases/latest) · [Node reference](docs/NODES.md)

![Actual Nuke Viewer and node graph displaying Marigold normals](docs/media/nuke-normals.png)

*Actual Nuke capture. The Viewer displays a rendered EXR through `SAVED_PREVIEW`; the live OFX branch is on the right. Display RGB = XYZ × 0.5 + 0.5.*

<details>
<summary>Original image in the same Nuke graph</summary>

![Original image in Nuke](docs/media/nuke-source.png)

</details>

## Video example

![Original footage on the left and frame-by-frame Marigold normals on the right](docs/media/video-comparison.gif)

[Comparison MP4](docs/media/video-comparison.mp4) · [Validation data](docs/video-validation.json)

The first four seconds of [Airam Dato-on's Pexels clip](https://www.pexels.com/video/urban-street-life-with-people-walking-by-historic-building-35958383/) were sampled at 12 fps. All **48 frames** were rendered through the actual Nuke OFX. There is no temporal smoothing or frame interpolation. Each frame is estimated independently, so orientation and surface details can flicker.

## How it works

```text
Read / sRGB → MarigoldV2Normals ┬→ Expression (XYZ × 0.5 + 0.5) → Viewer
                              └→ Write EXR (raw, float32 signed XYZ)
                    │
             localhost:47822
                    │
         Python daemon / CUDA / Marigold V2
```

- Automatic daemon startup, resident model and per-node last-result cache.
- Inference resolution, seed, input encoding and per-axis sign controls.
- RGB = signed camera-space XYZ, alpha = 1. Results resize to input dimensions and are renormalized.
- GPU requests are serialized. The adapter preserves Marigold's axes; automatic Nuke relighting-axis conversion is not implemented.

This is an experimental community integration for whole-image normals. Plane fitting and temporal stabilization are not implemented.

## Requirements

- Windows x64 and licensed Nuke with third-party OFX support. **NukeX is not required** for the tested workflow.
- NVIDIA CUDA GPU. **512 long edge was tested on an RTX 5070 Ti 16GB**; memory headroom is small. Other GPU configurations have not been verified here.
- Driver compatible with the PyTorch CUDA 12.8 build, [Git](https://git-scm.com/), [uv](https://docs.astral.sh/uv/) and an external Python installation for the launcher.
- Approximately **43GB of checkpoint downloads**, plus Python packages and working space. Weights are downloaded separately from upstream.
- Visual Studio C++ Build Tools for a source build, or the prebuilt Windows plugin from Releases.

## Install on Windows

```powershell
git clone https://github.com/tardis7732/MarigoldV2-Nuke.git
cd MarigoldV2-Nuke

# Isolated Python 3.10 / CUDA environment and pinned model assets
powershell -ExecutionPolicy Bypass -File tools/setup_windows.ps1

# Build the OFX and register the Nuke menu
powershell -ExecutionPolicy Bypass -File install.ps1
```

**Prebuilt option:** extract `MarigoldV2-Nuke-Windows-x64.zip` from [Releases](https://github.com/tardis7732/MarigoldV2-Nuke/releases/latest) into the cloned project folder. Then replace the final command with:

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1 -SkipBuild
```

CUDA setup is still required for new inference. The installer writes machine-specific paths and adds the project to `.nuke/init.py`, backing up an existing file when it changes. Restart Nuke, then use **Nodes → ML → Marigold V2 → Normals**. Rerun the installer if you move the project. An external launcher interpreter can be selected with `install.ps1 -Python C:/path/to/python.exe`.

For an existing upstream checkout, use `tools/setup_windows.ps1 -Repository C:/path/to/marigold-v2`. `-SkipDownload` uses existing assets. See [advanced setup](docs/SETUP.md) for native/WSL configuration.

## Open the examples

Extract `MarigoldV2-Nuke-examples.zip` from [Releases](https://github.com/tardis7732/MarigoldV2-Nuke/releases/latest) into the project folder. It includes the inputs, rendered float EXRs and MP4s.

| Script | Contents |
|---|---|
| [examples/Normals_Still.nk](examples/Normals_Still.nk) | Church image, saved normals, live inference and EXR export |
| [examples/video_demo/Normals_Video.nk](examples/video_demo/Normals_Video.nk) | 48 input frames and rendered normals, 12 fps, live inference branch |

Install OFX first so Nuke recognizes the live node. **Saved results do not load the model.** Viewer inputs: **1 saved normals / 2 source / 3 live inference**. Replacing the input does not change the saved result branch.

Replace `INPUT_IMAGE` with your sRGB JPG/PNG and view input 3. For sequences, set the Read/project frame range and render `WRITE_LIVE_NORMALS`.

## Input and output

- Default input: **sRGB encoded**. Sample Reads use `raw` to preserve encoded values. Convert ACEScg or other spaces upstream and tone-map HDR as appropriate.
- `linear sRGB` applies only the sRGB transfer function to RGB with Rec.709 primaries; it is not a general OCIO transform. Input is clamped to 0…1.
- Display Expression: `r*0.5+0.5`, `g*0.5+0.5`, `b*0.5+0.5`, `a`. Example Viewer process: `None`.
- Data export: Write **directly from OFX**, EXR, RGBA, **32-bit float**, **raw**, preserving signed −1…+1 XYZ.
- Inference dimensions snap to multiples of 16. Output is resized bilinearly and renormalized; upscaling does not restore details absent from the inference resolution.

See [all nodes and controls](docs/NODES.md).

## Measured performance

RTX 5070 Ti 16GB, Nuke 17.1v1, Python 3.10.20, PyTorch 2.10.0+cu128. Sample measurements, not throughput guarantees.

| Test | Source/output | Internal inference | Time |
|---|---|---|---|
| Still, cold | 2048×1360 | 512×336 | ~58 seconds including loading |
| Still, warm | 2048×1360 | 512×336 | ~9–15 seconds |
| Video, 48 frames | 432×768 | 288×512 | **648.66 seconds total** |
| Video, warm | 432×768 | 288×512 | ~12–13 seconds/frame |

The first still test peaked at ~14.4 GiB PyTorch allocated and ~15.6 GiB reserved. These counters differ from total Windows dedicated/shared GPU usage. Native/1024 inference and concurrent GPU workloads have not been validated. CPU offload is not implemented.

## Troubleshooting

| Symptom | Action |
|---|---|
| Daemon exited during startup | Check `output/daemon.log`. Run engine setup; confirm `config/launcher.json` exists. |
| First frame appears stuck | Allow around a minute for model loading; inspect Engine → Status and the log. |
| Stale result | Select the OFX and use **Clear selected node cache**, or increment `cacheRevision`. |
| GPU out of memory | Restart the engine, close other GPU workloads and lower inference resolution. |
| Old cancellation popup | Install the current binary and fully restart Nuke. Cancelled startup waits no longer show an error popup. |
| `Nuke -t` cannot obtain a license | Local tests use `Nuke -i -t` with an interactive license. |

The daemon exits after five idle minutes by default. Engine → Start/Status/Stop is available. The initial `ready` status means the server is listening; weights load on first inference. GPU inference is synchronous and cannot be immediately interrupted. Transport is limited to 16 megapixels and 16384 pixels per edge. A shared daemon is tied to the Nuke session that started it.

## Development and verification

```powershell
uv venv --python 3.11 .venv-check
uv pip install --python .venv-check/Scripts/python.exe numpy==2.2.5 pytest ruff
powershell -ExecutionPolicy Bypass -File ofx/build.ps1
.venv-check/Scripts/python.exe -m pytest -q
.venv-check/Scripts/python.exe tests/run_nuke_smoke.py
```

18 tests cover protocol validation, normal normalization, pixel order, caching, launcher lifecycle and retry after a cancelled startup wait. Synthetic tests do not run the model. Real still/video renders were also completed in Nuke: all 48 video EXRs were finite with unit vectors (maximum length error ~1.8×10⁻⁷), and the MP4s decoded to 48 frames. [Validation data](docs/video-validation.json).

Linux/WSL helpers are provided; the documented end-to-end runs used native Windows. See [SETUP.md](docs/SETUP.md).

## Credits and licenses

- OFX frontend and mini host: adapted from [Sumit Chatterjee's MoGe-nuke](https://github.com/sumitchatterjee13/MoGe-nuke), MIT; original notices retained.
- Inference: [Huawei's Marigold V2](https://github.com/huawei-bayerlab/marigold-v2), Apache 2.0. Qwen/Marigold checkpoints are separate downloads under their respective licenses.
- OpenFX headers: BSD-3-Clause.
- Church sample: official Marigold assets. Video: [Airam Dato-on / Pexels](https://www.pexels.com/video/urban-street-life-with-people-walking-by-historic-building-35958383/), [Pexels License](https://www.pexels.com/license/).
- Screenshots show the actual Nuke example graph and output. Nuke is a Foundry product; this project is an independent integration.

See [LICENSE](LICENSE), [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and [licenses/](licenses/).
