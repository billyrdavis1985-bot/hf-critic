#!/usr/bin/env python3
"""Audit tool: tests whether trap_detected rewards critiques that reach
the wrong conclusion. Produced the finding that 9 of 10 rows labelled
"sound" also scored trap_detected=True. See experiments.md.
"""
"""Does trap_detected reward critiques that reach the WRONG conclusion?
A row where the critic says VERDICT: sound while trap_detected=True is
self-contradictory: it endorsed the reasoning yet 'detected the flaw'."""
import json, re, sys
sys.path.insert(0, ".")
from eval_critic import score_one

tag = sys.argv[1] if len(sys.argv) > 1 else "tuned-greedy"
rows = json.load(open(f"eval/results_{tag}.json"))

def verdict(c):
    m = re.search(r"VERDICT:\s*([A-Za-z]+)", c)
    return m.group(1).lower() if m else "(unparsed)"

contra, margins = [], []
for r in rows:
    s = score_one(r)
    v = verdict(r["critique"])
    thr = max(2, s["gt_term_total"] // 4)
    margins.append((s["gt_term_hits"], thr, s["trap_detected"]))
    if s["trap_detected"] and v == "sound":
        contra.append((r["id"], r["category"], s["gt_term_hits"],
                       s["gt_term_total"], thr))

print(f"tag={tag}  n={len(rows)}\n")
print(f"CONTRADICTIONS (said sound AND trap_detected=True): {len(contra)}")
for cid, cat, h, tot, thr in contra:
    print(f"  {cid:8s} [{cat}]  hits={h}/{tot}  threshold={thr}")

passed = [m for m in margins if m[2]]
tight = [m for m in passed if m[0] <= m[1] + 1]
print(f"\nrows passing trap_detected: {len(passed)}/{len(rows)}")
print(f"  of those, within 1 hit of the threshold: {len(tight)}")
print(f"  median hits/threshold ratio: "
      f"{sorted(h/max(t,1) for h,t,_ in passed)[len(passed)//2]:.2f}")
