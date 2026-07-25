# hf-critic — Hudson Forge Reasoning Critic

Fine-tuning open-source LLMs into **reasoning-process evaluators**: given a
question and a candidate answer, the model judges the *reasoning itself* — not
just whether the answer is right — and returns a fixed contract:

```
VERDICT: sound | flawed | unsound
STEP ANALYSIS: ...
SEVERITY: 1-5
REVISED ANSWER: ... (if flawed)
```

Two critics were trained on the same corpus and compared head-to-head. See
[`experiments.md`](experiments.md) for the full write-up.

## Result

| metric              | tuned-Qwen3-8B | tuned-Mistral-7B |
|---------------------|----------------|------------------|
| verdict_rate        | 0.950          | 1.000            |
| structure_rate      | 0.950          | 1.000            |
| trap_detection_rate | 0.900          | 0.850            |
| mean_score_3        | 2.800          | 2.850            |

**Finding.** Fine-tuning teaches the output contract completely on both bases,
but cannot manufacture reasoning capability the base model lacks (weaker Mistral
maxed format, trailed on trap detection). The two models have **complementary,
uncorrelated blind spots** — Mistral is strong where Qwen is weakest
(frontier/meta/quantum reasoning), Qwen is strong where Mistral slips
(counterfactual) — which argues for running both as cross-checks rather than
picking one.

## Pipeline

| stage | script | output |
|-------|--------|--------|
| build corpus | `prepare_corpus.py` | unified ChatML JSONL + pinned `manifest.json` |
| reserve eval set | `reserve_holdout.py` | `eval_holdout.txt` (stratified, contamination firewall) |
| train | `train_critic.py` | QLoRA adapter + merged model |
| evaluate | `eval_critic.py` | before/after scores, model-vs-model compare |
| deploy | `export_gguf.py` + `Modelfile` | GGUF for Ollama |

The training and eval scripts are model-agnostic via `--chat-template`
(supports `qwen3` and `mistral`); adding a base is a one-flag change plus a
marker entry.

## Quickstart

```bash
# 1. build the training corpus (own examples + external mix)
python prepare_corpus.py --out ./corpus --local seed_examples.jsonl

# 2. reserve the eval holdout (do this BEFORE training)
python reserve_holdout.py

# 3. train (Qwen shown; swap --model + --chat-template for Mistral)
python train_critic.py --model unsloth/Qwen3-8B-unsloth-bnb-4bit \
  --chat-template qwen3 --out outputs/critic-qwen3-8b --upsample 20

# 4. evaluate base vs tuned, or model vs model
python eval_critic.py --model <path> --tag <name> --chat-template <tmpl>
python eval_critic.py --compare <tag_a> <tag_b>

# 5. export for serving
python export_gguf.py --model outputs/<run>/final --out outputs/<run>/gguf
ollama create critic -f Modelfile && ollama run critic
```

## Design notes

- **Contamination firewall.** The HF-IQR benchmark is held out as the *eval
  instrument*, never used as training data, so the before/after comparison is
  honest.
- **Local upsampling.** The hand-written critique examples are ~0.5% of the
  corpus raw; they're repeated (`--upsample`) so they carry real weight against
  the external instruction data without discarding it.
- **Reproducibility.** Every corpus build pins dataset revisions in
  `manifest.json`; runs are seeded.

## Environment

Trained locally on a single RTX 5070 (12GB, Blackwell) under WSL2. Requires
Python 3.11 (3.14 breaks `datasets`/`dill`), torch 2.11 + cu128, and Unsloth.
Large artifacts (`outputs/`, `*.gguf`) are gitignored — the code and manifests
reproduce them.

## Status

Two critics trained, evaluated, deployed (GGUF/Ollama), and archived. Intended
as lightweight, local, specialist verification components. See `experiments.md`
for detailed run logs and evidence-based next steps.
