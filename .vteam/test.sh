#!/usr/bin/env bash
# the project test entrypoint the generic gate profile runs (gate.py "test" step)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
npm test
