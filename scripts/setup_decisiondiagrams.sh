#!/bin/bash
# Build and smoke-test the repository-owned adapters against upstream.
set -euo pipefail
benchmark_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v dotnet >/dev/null || { echo "Install the .NET 6 SDK first." >&2; exit 1; }
exec python3 "$benchmark_root/scripts/run_nqueens_benchmarks.py" \
    --targets DD-BDD DD-CBDD --sizes 8 "$@"
