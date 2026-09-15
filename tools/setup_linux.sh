#!/usr/bin/env bash
# Run inside Linux/WSL after Python 3.10, uv, git and the NVIDIA driver are available.
# bash tools/setup_linux.sh /absolute/path/to/engine
set -euo pipefail
engine_root="${1:?Provide an absolute engine directory}"
case "$engine_root" in /*) ;; *) echo 'Use an absolute path' >&2; exit 2;; esac
project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$engine_root"
if [ ! -d "$engine_root/marigold-v2" ]; then
  git clone https://github.com/huawei-bayerlab/marigold-v2.git "$engine_root/marigold-v2"
  git -C "$engine_root/marigold-v2" checkout 18466672fb8661152434a0efe1184939164cda19
fi
actual_revision="$(git -C "$engine_root/marigold-v2" rev-parse HEAD)"
if [ "$actual_revision" != 18466672fb8661152434a0efe1184939164cda19 ]; then
  echo 'Existing repository revision differs from the tested adapter pin; use a new engine directory.' >&2
  exit 2
fi
uv venv --python 3.10 "$engine_root/.venv"
uv pip install --python "$engine_root/.venv/bin/python" torch==2.10.0 torchvision==0.25.0 --index-url https://download.pytorch.org/whl/cu128
uv pip install --python "$engine_root/.venv/bin/python" -e "$engine_root/marigold-v2"
uv pip check --python "$engine_root/.venv/bin/python"
"$engine_root/.venv/bin/python" "$project_root/tools/download_normals.py" --assets "$engine_root/assets"
printf 'Engine ready at %s. Configure its paths from the Windows project.\n' "$engine_root"
