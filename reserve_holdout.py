#!/usr/bin/env python3
"""
reserve_holdout.py — reserve an HF-IQR V2 eval holdout (contamination firewall)
==============================================================================
Downloads the HF-IQR V2 master dataset, draws a STRATIFIED sample of question
IDs (proportional across all 12 categories), and writes them to a text file.

These IDs must never appear in training data. Commit the output to Git so the
boundary is auditable and reproducible.

Usage:
    python reserve_holdout.py                 # 40 IDs, seed 42
    python reserve_holdout.py --n 60 --seed 7
"""

import argparse
import json
import random
from collections import Counter, defaultdict

from huggingface_hub import hf_hub_download

DATASET = "Billyrdavis1985/hudson-forge-iqr-v2"
FILENAME = "master_dataset.jsonl"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=40, help="holdout size")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="eval_holdout.txt")
    args = ap.parse_args()

    path = hf_hub_download(DATASET, FILENAME, repo_type="dataset")
    with open(path, encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]

    # Group by category so every reasoning type is represented in the holdout.
    # An unstratified sample can miss whole categories, which would leave blind
    # spots in the before/after comparison.
    by_cat = defaultdict(list)
    for r in rows:
        by_cat[r["category"]].append(r)

    rng = random.Random(args.seed)
    selected = []
    total = len(rows)

    for cat, items in sorted(by_cat.items()):
        # Proportional allocation, minimum 1 per category.
        k = max(1, round(args.n * len(items) / total))
        k = min(k, len(items))
        selected.extend(rng.sample(items, k))

    # Trim/pad to exactly n after rounding drift.
    rng.shuffle(selected)
    if len(selected) > args.n:
        selected = selected[: args.n]
    elif len(selected) < args.n:
        pool = [r for r in rows if r not in selected]
        selected.extend(rng.sample(pool, args.n - len(selected)))

    ids = sorted(r["id"] for r in selected)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(ids) + "\n")

    print(f"Reserved {len(ids)} IDs -> {args.out}  (seed={args.seed})")
    print("Category spread:", dict(sorted(
        Counter(r["category"] for r in selected).items())))
    print("Difficulty spread:", dict(sorted(
        Counter(r["difficulty"] for r in selected).items())))
    print("\nThese IDs are now EVAL-ONLY. Never train on them.")


if __name__ == "__main__":
    main()
