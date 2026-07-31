#!/usr/bin/env python3
"""Other-critique pilot: feed EXTERNAL candidate reasoning to a critic and score
its verdict against labels known by construction.

Reuses eval_critic.run_model so loading/generation match the published runs;
only build_critique_prompt is replaced (real candidate instead of placeholder).
"""
import json, re, sys, argparse
from pathlib import Path
sys.path.insert(0, ".")
import eval_critic as e

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--tag", required=True)
ap.add_argument("--chat-template", default="qwen3")
ap.add_argument("--candidates", default="eval/candidates_pilot.jsonl")
ap.add_argument("--seq-len", type=int, default=2048)
ap.add_argument("--max-new", type=int, default=800)
a = ap.parse_args()

cands = [json.loads(l) for l in open(a.candidates) if l.strip()]

# real candidate reasoning in the slot the self-critique probe left as a placeholder
e.build_critique_prompt = lambda q: (
    f"QUESTION: {q['prompt']}\n\n"
    f"CANDIDATE RESPONSE:\n{q['candidate']}\n\n"
    f"Critique the candidate's reasoning using the required format."
)

qs = [dict(id=f"{c['id']}::{c['variant']}", category=c["id"], difficulty=0,
           ground_truth="", trap_type="", prompt=c["prompt"],
           candidate=c["candidate"]) for c in cands]

outs = e.run_model(a.model, qs, a.seq_len, a.max_new, a.chat_template)

def verdict(t):
    m = re.search(r"VERDICT:\s*([A-Za-z]+)", t)
    v = m.group(1).lower() if m else None
    return v if v in ("sound", "flawed", "unsound") else "(invalid)"

rows, tp = [], 0
for c, o in zip(cands, outs):
    v = verdict(o["critique"])
    said_sound = (v == "sound")
    correct = (said_sound and c["label"] == "sound") or \
              (v in ("flawed", "unsound") and c["label"] == "flawed")
    rows.append(dict(id=c["id"], variant=c["variant"], label=c["label"],
                     emitted=v, correct=correct,
                     error_type=c["error_type"], critique=o["critique"]))
    tp += correct

out = Path("eval") / f"othercrit_{a.tag}.json"
json.dump(rows, open(out, "w"), indent=2)

print(f"\n=== other-critique: {a.tag}  n={len(rows)} ===")
for r in rows:
    mark = "OK " if r["correct"] else "MISS"
    print(f"  {mark}  {r['id']:8s} {r['variant']:10s} label={r['label']:7s} emitted={r['emitted']}")
clean = [r for r in rows if r["label"] == "sound"]
corr  = [r for r in rows if r["label"] == "flawed"]
print(f"\naccuracy            : {tp}/{len(rows)}")
print(f"recall on corrupted : {sum(r['correct'] for r in corr)}/{len(corr)}  (flagged the injected error)")
print(f"specificity on clean: {sum(r['correct'] for r in clean)}/{len(clean)}  (did not false-alarm)")
print(f"invalid verdicts    : {sum(1 for r in rows if r['emitted']=='(invalid)')}")
print(f"\nfull outputs -> {out}")
