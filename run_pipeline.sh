#!/usr/bin/env bash
# Runs code/NN_*.py and code/NN_*.R in numeric order; stops at the first failure.
# The log records step, status and duration only, never script output, so it is safe to share.
set -uo pipefail
cd "$(dirname "$0")"

PY=.venv/bin/python
[ -x "$PY" ] || { echo "No .venv: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"; exit 1; }
[ -f config/config.json ] || { echo "config/config.json missing: copy config/config.example.json"; exit 1; }

LOG=output/final_no_phi/logs/run_pipeline.log
mkdir -p "$(dirname "$LOG")"
echo "run $(date '+%Y-%m-%dT%H:%M:%S') commit $(git rev-parse --short HEAD 2>/dev/null || echo none)" >> "$LOG"

shopt -s nullglob
for script in $(printf '%s\n' code/[0-9][0-9]_*.py code/[0-9][0-9]_*.R | sort); do
  step=$(basename "${script%.*}")
  start=$SECONDS
  echo "== $step"
  case "$script" in
    *.py) "$PY" "$script" ;;
    *.R)  Rscript "$script" ;;
  esac
  status=$?
  echo "$step exit=$status $((SECONDS - start))s" >> "$LOG"
  if [ "$status" -ne 0 ]; then
    echo "FAILED at $step (exit $status). Log: $LOG"
    exit "$status"
  fi
done
echo "Pipeline complete. Log: $LOG"
