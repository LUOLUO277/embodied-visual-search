#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="${VENV_PATH:-$HOME/projects/embodied-visual-search/.venv}"

cd "$ROOT_DIR"
source "$VENV_PATH/bin/activate"

export AI2THOR_PLATFORM="${AI2THOR_PLATFORM:-Linux64}"
export AI2THOR_X_DISPLAY="${AI2THOR_X_DISPLAY:-:0}"
export AI2THOR_FORCE_GLCORE="${AI2THOR_FORCE_GLCORE:-1}"
export DISPLAY="${DISPLAY:-:0}"
export GALLIUM_DRIVER="${GALLIUM_DRIVER:-d3d12}"
export MESA_D3D12_DEFAULT_ADAPTER_NAME="${MESA_D3D12_DEFAULT_ADAPTER_NAME:-NVIDIA}"

python backend/launch_backend.py
