#!/usr/bin/env python3
"""
eval_critic.py — before/after evaluation on the HF-IQR held-out set
===================================================================
Runs a model (base OR fine-tuned) as a reasoning critic on the 40 reserved
holdout questions, then scores each critique against the question's
ground_truth. Run it TWICE — once on the base model, once on the tuned model —
and compare. Same script, same prompts, same scoring: the delta is the result.

Scoring is rubric-based and deterministic where possible:
  - trap_detected: did the critique identify the known trap/error? (regex + key
    concept match against ground_truth)
  - has_verdict: did it emit a VERDICT line? (format adherence)
  - has_structure: STEP ANALYSIS + SEVERITY present? (format adherence)
These are proxies, not perfect graders, but they are consistent across both
runs, which is what makes the comparison fair. For a deeper score, pipe the
saved outputs through an LLM judge separately.

Usage (venv active, from ~/hf-critic):
    # baseline BEFORE training:
    python eval_critic.py --model unsloth/Qwen3-8B-unsloth-bnb-4bit --tag base
    # AFTER training:
    python eval_critic.py --model outputs/critic-qwen3-8b/final --tag tuned
    # then compare:
    python eval_critic.py --compare base tuned

Outputs:
    eval/results_<tag>.json     per-question critiques + scores
    eval/summary_<tag>.json     aggregate metrics
"""

import argparse
import os
import json
import re
from pathlib import Path

HOLDOUT_FILE = "eval_holdout.txt"
DATASET_FILE = "HF_IQR_Master_Dataset_v2.json"   # full V2, has prompt+ground_truth
EVAL_DIR = Path("eval")

SYSTEM = ("You are a reasoning process evaluator. Given a question and a "
          "candidate response, assess the quality of the reasoning process "
          "itself, not just answer correctness. Identify where reasoning holds, "
          "where it breaks down, and whether conclusions follow from stated "
          "premises. Output: VERDICT (sound / flawed / unsound), STEP ANALYSIS, "
          "SEVERITY (1-5), and a REVISED ANSWER if flawed.")


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def load_holdout_questions():
    with open(HOLDOUT_FILE, encoding="utf-8") as f:
        keep_ids = {line.strip() for line in f if line.strip()}

    with open(DATASET_FILE, encoding="utf-8") as f:
        data = json.load(f)

    questions = []
    for cat_items in data["dataset"].values():
        for q in cat_items:
            if q["id"] in keep_ids:
                questions.append(q)

    missing = keep_ids - {q["id"] for q in questions}
    if missing:
        print(f"WARNING: {len(missing)} holdout IDs not found: {sorted(missing)}")
    print(f"Loaded {len(questions)} holdout questions.")
    return questions


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def build_critique_prompt(q):
    """
    We ask the model to critique a candidate answer. Since the holdout has no
    stored candidate response, we ask the model to first reason then critique
    its OWN reasoning — a self-critique probe. This isolates the critic
    behavior the fine-tune targets.
    """
    return (f"QUESTION: {q['prompt']}\n\n"
            f"CANDIDATE RESPONSE: [Provide your own step-by-step answer to the "
            f"question, then critique that reasoning using the required format.]")


def run_model(model_path, questions, seq_len, max_new, chat_template="qwen3"):
    from unsloth import FastLanguageModel
    from unsloth.chat_templates import get_chat_template
    import torch

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=seq_len,
        load_in_4bit=True,
        dtype=None,
    )
    FastLanguageModel.for_inference(model)
    tokenizer = get_chat_template(tokenizer, chat_template=chat_template)

    outputs = []
    for i, q in enumerate(questions, 1):
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": build_critique_prompt(q)}]
        inputs = tokenizer.apply_chat_template(
            messages, tokenize=True, add_generation_prompt=True,
            return_tensors="pt").to("cuda")
        with torch.no_grad():
            gen = model.generate(input_ids=inputs, max_new_tokens=max_new,
                                 **({"do_sample": False} if os.environ.get("EVAL_GREEDY") else {"temperature": 0.3, "do_sample": True}),
                                 pad_token_id=tokenizer.eos_token_id)
        text = tokenizer.decode(gen[0][inputs.shape[1]:],
                                skip_special_tokens=True)
        outputs.append({"id": q["id"], "category": q["category"],
                        "difficulty": q["difficulty"],
                        "ground_truth": q["ground_truth"],
                        "trap_type": q.get("trap_type", ""),
                        "critique": text})
        print(f"  [{i}/{len(questions)}] {q['id']}")
    return outputs


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def score_one(o):
    crit = o["critique"].lower()
    gt = o["ground_truth"].lower()

    has_verdict = bool(re.search(r"verdict\s*:", crit))
    has_structure = ("step analysis" in crit or "step " in crit) and \
                    "severity" in crit

    # trap detection: extract salient content words from ground_truth and
    # check overlap. Crude but consistent across both runs.
    gt_terms = set(re.findall(r"[a-z]{5,}", gt)) - {
        "correct", "answer", "before", "solving", "should", "which", "state"}
    hits = sum(1 for t in gt_terms if t in crit)
    trap_detected = hits >= max(2, len(gt_terms) // 4)

    score = sum([has_verdict, has_structure, trap_detected])
    return {"has_verdict": has_verdict, "has_structure": has_structure,
            "trap_detected": trap_detected, "score_3": score,
            "gt_term_hits": hits, "gt_term_total": len(gt_terms)}


def evaluate(tag, model_path, seq_len, max_new, chat_template="qwen3"):
    EVAL_DIR.mkdir(exist_ok=True)
    questions = load_holdout_questions()
    outputs = run_model(model_path, questions, seq_len, max_new, chat_template)

    for o in outputs:
        o["scores"] = score_one(o)

    with open(EVAL_DIR / f"results_{tag}.json", "w", encoding="utf-8") as f:
        json.dump(outputs, f, indent=2, ensure_ascii=False)

    n = len(outputs)
    summary = {
        "tag": tag, "model": model_path, "n": n,
        "verdict_rate": sum(o["scores"]["has_verdict"] for o in outputs) / n,
        "structure_rate": sum(o["scores"]["has_structure"] for o in outputs) / n,
        "trap_detection_rate": sum(o["scores"]["trap_detected"] for o in outputs) / n,
        "mean_score_3": sum(o["scores"]["score_3"] for o in outputs) / n,
    }
    by_cat = {}
    for o in outputs:
        by_cat.setdefault(o["category"], []).append(o["scores"]["score_3"])
    summary["by_category_mean"] = {k: round(sum(v)/len(v), 2)
                                   for k, v in sorted(by_cat.items())}

    with open(EVAL_DIR / f"summary_{tag}.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n=== {tag} ===")
    for k in ("verdict_rate", "structure_rate", "trap_detection_rate", "mean_score_3"):
        print(f"  {k}: {summary[k]:.3f}")
    return summary


def compare(tag_a, tag_b):
    a = json.load(open(EVAL_DIR / f"summary_{tag_a}.json"))
    b = json.load(open(EVAL_DIR / f"summary_{tag_b}.json"))
    print(f"\n{'metric':<24}{tag_a:>10}{tag_b:>10}{'delta':>10}")
    print("-" * 54)
    for k in ("verdict_rate", "structure_rate", "trap_detection_rate", "mean_score_3"):
        d = b[k] - a[k]
        print(f"{k:<24}{a[k]:>10.3f}{b[k]:>10.3f}{d:>+10.3f}")
    print("\nper-category mean_score_3:")
    cats = sorted(set(a["by_category_mean"]) | set(b["by_category_mean"]))
    for c in cats:
        va = a["by_category_mean"].get(c, 0)
        vb = b["by_category_mean"].get(c, 0)
        print(f"  {c:<22}{va:>8.2f}{vb:>8.2f}{vb-va:>+8.2f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model")
    ap.add_argument("--tag")
    ap.add_argument("--seq-len", type=int, default=2048)
    ap.add_argument("--max-new", type=int, default=800)
    ap.add_argument("--chat-template", default="qwen3",
                    choices=["qwen3", "mistral"],
                    help="must match the model being evaluated")
    ap.add_argument("--compare", nargs=2, metavar=("TAG_A", "TAG_B"))
    args = ap.parse_args()

    if args.compare:
        compare(*args.compare)
    else:
        assert args.model and args.tag, "need --model and --tag (or --compare)"
        evaluate(args.tag, args.model, args.seq_len, args.max_new, args.chat_template)


if __name__ == "__main__":
    main()
