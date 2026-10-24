#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
printf '%s\n' 'RiskGraph paired demo: http://127.0.0.1:8765/demo' 'Saved evidence only. No model API calls.'
exec ./scripts/start-local.sh
