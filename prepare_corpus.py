#!/usr/bin/env python3
"""
prepare_corpus.py — Hudson Forge fine-tuning corpus builder
============================================================
Normalizes external HF datasets + local Hudson Forge data into one
unified ChatML JSONL corpus, with deterministic subsampling, dedup,
train/val split, and a reproducibility manifest (pinned revisions).

Usage:
    pip install datasets huggingface_hub
    python prepare_corpus.py --out ./corpus --seed 42
    python prepare_corpus.py --out ./corpus --local my_data.jsonl

Output:
    corpus/train.jsonl      training split (unified schema)
    corpus/val.jsonl        held-out validation split
    corpus/manifest.json    pinned revisions, counts, config hash
"""

import argparse
import hashlib
import json
import random
from datetime import date
from pathlib import Path

from datasets import load_dataset
from huggingface_hub import dataset_info

# ---------------------------------------------------------------------------
# Mixture config — edit counts here, nowhere else.
# target_rows = rows AFTER filtering/dedup that we want from each source.
# ---------------------------------------------------------------------------
MIXTURE = {
    "prometheus-eval/Feedback-Collection": {"target_rows": 4000, "adapter": "feedback_collection"},
    "openbmb/UltraFeedback":               {"target_rows": 2000, "adapter": "ultrafeedback"},
    "open-thoughts/OpenThoughts3-1.2M":    {"target_rows": 3000, "adapter": "sharegpt"},
    "allenai/tulu-3-sft-mixture":          {"target_rows": 2000, "adapter": "chatml"},
}

VAL_FRACTION = 0.05
MAX_ASSISTANT_CHARS = 24_000   # drop pathological outliers (blows up seq len)
MIN_ASSISTANT_CHARS = 20       # drop empty / trivial responses


# ---------------------------------------------------------------------------
# Adapters — one per source format. Each yields unified records or None.
# Unified schema:
#   {"messages": [...ChatML...], "meta": {source, category, difficulty,
#                                          license, quality, created}}
# ---------------------------------------------------------------------------

def _record(messages, source, category=None, difficulty=None, quality=None):
    return {
        "messages": messages,
        "meta": {
            "source": source,
            "category": category,
            "difficulty": difficulty,
            "license": None,          # filled from manifest at write time
            "quality": quality,
            "created": date.today().isoformat(),
        },
    }


def adapt_feedback_collection(row, source):
    """instruction (task + rubric) -> output (structured feedback + score)."""
    instr, out = row.get("instruction"), row.get("output")
    if not instr or not out:
        return None
    return _record(
        [{"role": "user", "content": instr.strip()},
         {"role": "assistant", "content": out.strip()}],
        source, category="critique",
    )


def adapt_ultrafeedback(row, source):
    """Pick the highest-rated completion -> rejection-sampled SFT pair."""
    instr = row.get("instruction")
    completions = row.get("completions") or []
    if not instr or not completions:
        return None
    scored = [c for c in completions
              if isinstance(c.get("overall_score"), (int, float)) and c.get("response")]
    if not scored:
        return None
    best = max(scored, key=lambda c: c["overall_score"])
    if best["overall_score"] < 8.0:   # quality gate: keep only strong responses
        return None
    return _record(
        [{"role": "user", "content": instr.strip()},
         {"role": "assistant", "content": best["response"].strip()}],
        source, category="general", quality=best["overall_score"] / 10.0,
    )


def adapt_sharegpt(row, source):
    """OpenThoughts-style: conversations = [{from: human|gpt, value}]."""
    role_map = {"human": "user", "user": "user",
                "gpt": "assistant", "assistant": "assistant",
                "system": "system"}
    msgs = []
    for turn in row.get("conversations") or []:
        role = role_map.get(turn.get("from", "").lower())
        if role is None or not turn.get("value"):
            return None
        msgs.append({"role": role, "content": turn["value"].strip()})
    if not _valid_dialogue(msgs):
        return None
    return _record(msgs, source, category="reasoning",
                   difficulty=row.get("difficulty"))


def adapt_chatml(row, source):
    """Already in messages format (Tulu-3, and Hudson Forge originals)."""
    msgs = row.get("messages")
    if not _valid_dialogue(msgs):
        return None
    meta = row.get("meta") or {}
    return _record(msgs, meta.get("source", source),
                   category=meta.get("category", "general"),
                   difficulty=meta.get("difficulty"),
                   quality=meta.get("quality"))


ADAPTERS = {
    "feedback_collection": adapt_feedback_collection,
    "ultrafeedback": adapt_ultrafeedback,
    "sharegpt": adapt_sharegpt,
    "chatml": adapt_chatml,
}


def _valid_dialogue(msgs):
    if not msgs or not isinstance(msgs, list):
        return False
    roles = [m.get("role") for m in msgs]
    if "user" not in roles or roles[-1] != "assistant":
        return False
    return all(m.get("content") for m in msgs)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------

def passes_filters(rec):
    asst = "".join(m["content"] for m in rec["messages"] if m["role"] == "assistant")
    return MIN_ASSISTANT_CHARS <= len(asst) <= MAX_ASSISTANT_CHARS


def dedup_key(rec):
    """Dedupe on normalized user content across ALL sources."""
    user = " ".join(m["content"] for m in rec["messages"] if m["role"] == "user")
    return hashlib.sha256(" ".join(user.lower().split()).encode()).hexdigest()


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def collect_source(ds_id, cfg, seed, seen_hashes):
    """Stream a source via HF's auto-converted parquet branch, adapt, filter,
    reservoir-sample, dedupe.

    Design notes:
    - We stream from refs/convert/parquet because some datasets (e.g.
      Feedback-Collection) are stored as one monolithic JSON file, which the
      native streaming loader materializes in RAM.
    - Randomization is our own reservoir sampling: `datasets`' streaming
      shuffle buffers whole rows (OOM risk with long reasoning traces).
      The reservoir gives an unbiased sample of the *scanned prefix*; the
      scan cap bounds runtime on 1M+-row sets. Raise SCAN_MULTIPLIER for a
      more representative sample at the cost of wall-clock time.
    """
    SCAN_MULTIPLIER = 20
    adapter = ADAPTERS[cfg["adapter"]]
    target = cfg["target_rows"]
    info = dataset_info(ds_id)
    revision = info.sha                      # main-branch pin for the manifest
    license_ = (info.card_data.license if info.card_data else None)

    ds = load_dataset(
        "parquet",
        data_files=f"hf://datasets/{ds_id}@refs/convert/parquet/default/train/*.parquet",
        split="train", streaming=True,
    )

    rng = random.Random(seed ^ hash(ds_id) & 0xFFFFFFFF)
    reservoir_size = target * 2              # oversample; dedup shrinks it later
    reservoir, n_valid, scanned = [], 0, 0
    scan_cap = max(target * SCAN_MULTIPLIER, 10_000)

    for row in ds:
        scanned += 1
        if scanned > scan_cap:
            break
        rec = adapter(row, ds_id)
        if rec is None or not passes_filters(rec):
            continue
        n_valid += 1
        if len(reservoir) < reservoir_size:
            reservoir.append(rec)
        else:
            j = rng.randrange(n_valid)
            if j < reservoir_size:
                reservoir[j] = rec

    rng.shuffle(reservoir)
    kept = []
    for rec in reservoir:
        key = dedup_key(rec)
        if key in seen_hashes:
            continue
        seen_hashes.add(key)
        rec["meta"]["license"] = license_
        kept.append(rec)
        if len(kept) >= target:
            break

    return kept, {"revision": revision, "license": license_,
                  "kept": len(kept), "scanned": scanned, "valid": n_valid}


def collect_local(path, seen_hashes):
    kept = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = adapt_chatml(json.loads(line), f"local:{Path(path).name}")
            if rec is None or not passes_filters(rec):
                continue
            key = dedup_key(rec)
            if key in seen_hashes:
                continue
            seen_hashes.add(key)
            kept.append(rec)
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./corpus")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--local", nargs="*", default=[],
                    help="Local JSONL file(s) already in unified schema "
                         "(Hudson Forge originals). Loaded first, never subsampled.")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    seen, all_records, manifest_sources = set(), [], {}

    # Local (own) data first — it wins dedup collisions against external sets.
    for path in args.local:
        recs = collect_local(path, seen)
        all_records.extend(recs)
        manifest_sources[f"local:{path}"] = {"kept": len(recs)}
        print(f"[local] {path}: kept {len(recs)}")

    for ds_id, cfg in MIXTURE.items():
        recs, stats = collect_source(ds_id, cfg, args.seed, seen)
        all_records.extend(recs)
        manifest_sources[ds_id] = stats
        print(f"[hub]   {ds_id}: kept {stats['kept']} "
              f"(scanned {stats['scanned']}, rev {stats['revision'][:8]})")

    rng.shuffle(all_records)
    n_val = max(1, int(len(all_records) * VAL_FRACTION))
    val, train = all_records[:n_val], all_records[n_val:]

    for name, split in (("train.jsonl", train), ("val.jsonl", val)):
        with open(out / name, "w") as f:
            for rec in split:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    manifest = {
        "created": date.today().isoformat(),
        "seed": args.seed,
        "val_fraction": VAL_FRACTION,
        "totals": {"train": len(train), "val": len(val)},
        "sources": manifest_sources,
        "config_hash": hashlib.sha256(
            json.dumps(MIXTURE, sort_keys=True).encode()).hexdigest()[:16],
    }
    with open(out / "manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nDone: {len(train)} train / {len(val)} val -> {out}/")
    print("Manifest written with pinned revisions — commit it with the run.")


if __name__ == "__main__":
    main()
