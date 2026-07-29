#!/usr/bin/env bash
# beat_gate.sh — read a summary_<tag>.json from eval_critic.py, gate via apr beat-run
# usage: ./scripts/beat_gate.sh <summary.json> [contract.yaml]
set -euo pipefail

SUMMARY="${1:?usage: beat_gate.sh <summary.json> [contract.yaml]}"
CONTRACT="${2:-contracts/beat-critic-trap-detection-v1.yaml}"

[[ -f "$SUMMARY" ]]  || { echo "GATE FAIL: summary not found: $SUMMARY" >&2; exit 2; }
[[ -f "$CONTRACT" ]] || { echo "GATE FAIL: contract not found: $CONTRACT" >&2; exit 2; }

VALUE=$(python3 - "$SUMMARY" << 'PY'
import json, sys
try:
    s = json.load(open(sys.argv[1]))
    v = s["trap_detection_rate"]
    assert isinstance(v, (int, float)) and 0.0 <= v <= 1.0, f"out of range: {v}"
    print(v)
except Exception as e:
    sys.exit(f"GATE FAIL: bad summary artifact: {e}")
PY
)

echo "gate: $SUMMARY -> trap_detection_rate = $VALUE"
exec apr beat-run "$CONTRACT" --measured "$VALUE"
