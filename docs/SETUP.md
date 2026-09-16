# Advanced setup

`tools/setup_windows.ps1` creates `.venv-engine`, installs Python 3.10 / PyTorch CUDA 12.8 and the pinned Marigold package, downloads normals and Depth assets and writes `config/launcher.json`.

## Existing native environment

```powershell
python tools/configure_engine.py --python C:/engine/.venv/Scripts/python.exe --repo C:/engine/marigold-v2 --assets C:/engine/assets
```

The launcher interpreter configured by `install.ps1 -Python C:/path/to/python.exe` uses only the standard library. It is separate from Nuke Python and the model environment.

## Linux / WSL2 helpers

The documented end-to-end runs used native Windows. Linux/WSL helpers were not validated end-to-end in that run. An existing working CUDA environment, Git and uv are required.

```bash
bash tools/setup_linux.sh "$HOME/marigold-engine"
```

From Windows, use Linux paths:

```powershell
python tools/configure_engine.py --wsl-distro Ubuntu --python /home/YOUR_USER/marigold-engine/.venv/bin/python --repo /home/YOUR_USER/marigold-engine/marigold-v2 --assets /home/YOUR_USER/marigold-engine/assets
```

WSL localhost forwarding must work. The server binds only to `127.0.0.1`. Windows host PIDs are monitored by the Windows launcher and never sent into Linux's PID namespace. WSL and Windows features are not installed automatically.

## Lifecycle

- Server listening precedes model loading; first inference loads weights.
- Default idle timeout is 300 seconds. Configure with `--idle-timeout 0` to keep it resident until shutdown/host exit.
- Engine → Start/Status/Stop manages the server. Startup/inference errors go to `output/daemon.log`.
- Clear node caches after restarting the server or changing weights.
- Cancelled startup waits leave the daemon running and do not cache an error. GPU inference itself still waits for a response or timeout.

The Qwen transformer/VAE plus Marigold normals and Depth Log-stage2 trainables/prompt embeddings are downloaded. `tools/download_normals.py --task normals` or `--task depth` restricts task downloads; the default is `all`. Revisions are pinned in `config/upstream.json` and `tools/download_normals.py`. CPU offload and automatic lower-resolution retries are not implemented.

The daemon keeps one quantized backbone on the GPU and caches each loaded task's trainables in system RAM. Switching Output replaces the complete task LoRA/decoder weights and prompt graph. This avoids two full GPU models, but switching takes extra time and only the last result per node is cached. Requests execute serially. Use the same port for nodes that should share the engine.

For development while an older binary is loaded in Nuke, build with `ofx/build.ps1 -BuildDirectory build-depth` and set `MARIGOLD_OFX_BUILD_DIR` to that absolute build directory for a **new** test process. Restart Nuke when installing a replacement binary.

`install.ps1 -SkipBuild -BuildDirectory build-depth` registers that build directory for subsequent Nuke sessions without replacing the DLL currently loaded by an open session. The installer stores this local path in ignored `config/frontend.json`.
