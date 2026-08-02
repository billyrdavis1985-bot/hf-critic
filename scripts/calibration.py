#!/usr/bin/env python3
"""SUPERSEDED. This computes precision-when-sound using the proxy
"trap_type non-empty => reasoning is flawed". That proxy is invalid:
only 4 of 40 holdout rows carry a trap_type, so the metric returns a
meaningless 1.000. Kept as part of the audit trail - see
experiments.md, "Methods limitations".
"""
"""Calibration diagnostic: does the critic's 'sound' verdict mean anything?
Derives expected verdict from trap_type (non-empty => reasoning is flawed)."""
import json, re, sys, collections
from pathlib import Path

tag = sys.argv[1] if len(sys.argv) > 1 else "tuned"
rows = json.load(open(Path("eval") / f"results_{tag}.json"))

def emitted(critique):
    m = re.search(r"VERDICT:\s*([A-Za-z]+)", critique)
    return m.group(1).lower() if m else "(unparsed)"

print(f"tag={tag}  n={len(rows)}")
print("\ntrap_type distribution:")
for k, v in collections.Counter(r.get("trap_type") or "(none)" for r in rows).most_common():
    print(f"  {v:3d}  {k}")

print("\nemitted verdict distribution:")
for k, v in collections.Counter(emitted(r["critique"]) for r in rows).most_common():
    print(f"  {v:3d}  {k}")

# confusion: emitted-sound vs has-trap
cells = collections.Counter()
for r in rows:
    said_sound = emitted(r["critique"]) == "sound"
    has_trap = bool(r.get("trap_type"))
    cells[(said_sound, has_trap)] += 1

tp = cells[(False, True)]   # said not-sound, trap present  -> correct catch
fp = cells[(False, False)]  # said not-sound, no trap       -> false alarm
fn = cells[(True, True)]    # said sound, trap present      -> MISS
tn = cells[(True, False)]   # said sound, no trap           -> correct pass

print("\nconfusion (rows = critic, cols = ground truth via trap_type):")
print(f"  said flawed/unsound + trap present : {tp}")
print(f"  said flawed/unsound + NO trap      : {fp}   <- false alarm")
print(f"  said sound + trap present          : {fn}   <- MISS")
print(f"  said sound + NO trap               : {tn}")

n_sound_said = tn + fn
if n_sound_said == 0:
    print("\nprecision_when_sound: UNDEFINED (critic never said sound)")
elif (tn + fp) == 0:
    print("\nprecision_when_sound: DEGENERATE — holdout has no trap-free questions,")
    print("  so every 'sound' verdict is wrong by construction. Needs sound controls.")
else:
    print(f"\nprecision_when_sound = {tn}/{n_sound_said} = {tn/n_sound_said:.3f}")
