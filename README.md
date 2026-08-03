# hf-critic — Hudson Forge Reasoning Critic

**Fine-tuning open-source LLMs into reasoning-process evaluators** — models that
judge the *quality of reasoning* behind an answer, not just whether the answer
is correct. Part of the IRMB research program at Hudson Forge Technologies LLC,
and developed as an MLOps coursework project.

---

## Overview

A reasoning critic takes a question and a candidate response and returns a fixed
assessment contract:

```
VERDICT: sound | flawed | unsound
STEP ANALYSIS: ...
SEVERITY: 1-5
REVISED ANSWER: ... (if flawed)
```

The project fine-tunes small, open-weight models into this role using a corpus
of hand-written critique examples mixed with external instruction data, then
evaluates them against a held-out benchmark reserved as a contamination
firewall. Two models were trained on identical data and compared head-to-head.

The intended use is as **lightweight, local, specialist verification
components** — a cheap always-on reasoning check, not a primary model.

## Results

| model            | verdict_rate | structure_rate | trap_detection | mean_score_3 |
|------------------|--------------|----------------|----------------|--------------|
| base Qwen3-8B    | 0.525        | 0.500          | 0.975          | 2.000        |
| tuned Qwen3-8B   | 0.950        | 0.950          | 0.900          | 2.800        |
| base Mistral-7B  | 1.000        | 0.950          | 0.800          | 2.750        |
| tuned Mistral-7B | 1.000        | 1.000          | 0.850          | 2.850        |

Evaluated on a 40-question stratified holdout. See
[`experiments.md`](experiments.md) for full run logs and per-category deltas.

> **Read the caveat before using these numbers.** A later audit of the scoring
> code found that `trap_detection` is a lexical-overlap heuristic, not a measure
> of reasoning: it counts substring matches between the reference solution and
> the critique. Nine of ten items the tuned critic labelled "sound" also scored
> as having detected the flaw. `verdict_rate` and `structure_rate` are direct
> string checks and are unaffected. See [Metric audit](#metric-audit).

**Headline finding.** Fine-tuning pulled both models toward the capability
level embedded in the training data — from opposite directions. Qwen's trap
detection came *down* (0.975 → 0.900, mild forgetting) while Mistral's came
*up* (0.800 → 0.850, a gain): they converged toward the corpus. Format proved
base-dependent: Mistral followed the output contract from the system prompt
alone (base verdict rate 1.000), while Qwen needed the fine-tune to learn it
(0.525 → 0.950). At n=40 a 0.05 delta is two questions, so the
convergence is consistent but not statistically proven — and because it rests
on the trap-detection metric, it is now best read as suggestive rather than
established. The **complementary blind spots** claim came from per-category
means on self-critique; when both models were later tested on *external*
reasoning, the weaker critic contributed no unique catches. The format result
(base-dependent contract compliance) depends on neither metric and stands.

## Metric audit

An audit of this repository's own evaluation code. Full detail in
[`experiments.md`](experiments.md) ("Methods limitations", "Revised results")
and [`eval/diagnosis_audit_qwen.md`](eval/diagnosis_audit_qwen.md) /
[`eval/diagnosis_audit_mistral.md`](eval/diagnosis_audit_mistral.md).

**Lexical overlap.** `trap_detection_rate` extracts words of five or more
letters from the reference solution and passes when enough appear as substrings
in the critique (`hits >= max(2, n_terms // 4)`). Substring matching means a
critique arguing the opposite conclusion still scores. Requiring the verdict not
to endorse the reasoning moves the rate from 0.900 to 0.675.

**Verdict-string scoring.** The other-critique harness scored critics on the
emitted `VERDICT:` token. Reading all 32 corrupted-item critiques by hand
against the injected error gives a different picture:

| model | verdict-string recall | diagnosis-verified | inflation |
|-------|----------------------|--------------------|-----------|
| tuned Qwen3-8B    | 16/16 = 1.00 | 10/16 = 0.63 | 1.6x |
| tuned Mistral-7B  | 8/16 = 0.50  | 2/16 = 0.13  | 3.8x |

A spurious catch emits a non-endorsing verdict while the analysis certifies the
flawed content. The inflation is larger for the weaker model, so verdict-string
scoring compresses the measured distance between a critic that mostly works and
one that mostly does not.

## Other-critique study

The evaluation above is a *self*-critique probe: the holdout stores no candidate
answer, so the model answers the question and then critiques its own reasoning.
The intended deployment is verifying *other* models' reasoning, which is a
different capability.

Five batches (n=34) test it directly, using candidates built by **controlled
corruption** — each question yields a correct trace and a variant containing one
deliberate, named error, so labels are known by construction. Questions come
from a 160-question pool disjoint from the reserved holdout.

Every batch prediction was pre-registered in `experiments.md` with a numeric
falsification criterion *before* the batch ran. Four hypotheses were recorded
and all four failed, including a severity-based scoring rule that looked free on
existing data and did not survive fresh items.

## CI regression gate

`contracts/beat-critic-trap-detection-v1.yaml` is a BeatBenchmark contract
enforced by GitHub Actions. A critic whose measured rate falls below the
threshold fails the build.

The gate is Rust: `apr` is the CLI of
[aprender](https://github.com/paiml/aprender), a pure-Rust ML framework whose
contract system pins a metric baseline and fails CI on regression. CI installs
it with `cargo install aprender --locked` and caches the binary. The split is
deliberate — measurement stays in the Python eval harness that produced every
published number, enforcement is the Rust contract engine, and
`eval/summary_<tag>.json` is the interface between them. Local Rust training is
not currently usable on this hardware (see aprender issues #559 and #563 for the
Blackwell / sm_120 finetune hang).

The contract's `notes:` block describes what it actually gates: a regression
canary that catches catastrophic degradation, not a reasoning-quality guarantee.
CI runners have no GPU, so the gate verifies the committed eval summary rather
than re-running the evaluation.

## Repository layout

```
hf-critic/
├── README.md              # this file
├── experiments.md         # detailed run logs, findings, next steps
├── prepare_corpus.py      # build unified ChatML corpus (own + external), pinned manifest
├── reserve_holdout.py     # reserve stratified eval set (contamination firewall)
├── train_critic.py        # QLoRA fine-tune; model-agnostic via --chat-template
├── eval_critic.py         # before/after + model-vs-model scoring on the holdout
├── export_gguf.py         # quantize merged model to GGUF for serving
├── Modelfile.qwen         # Ollama config — Qwen critic
├── Modelfile.mistral      # Ollama config — Mistral critic
├── seed_examples.jsonl    # 38 hand-written critique examples (12 categories)
├── eval_holdout.txt       # reserved HF-IQR question IDs — never trained on
├── .github/workflows/
│   └── beat-gate.yml      # CI: regression gate on every push
├── contracts/             # BeatBenchmark contract (apr beat-run)
├── corpus/
│   └── manifest.json      # pinned dataset revisions + run config
├── eval/                  # summaries, candidate sets, othercrit runs, diagnosis audits
├── figures/               # convergence and per-category plots
├── paper/                 # methods paper draft + article correction note
└── scripts/               # beat_gate.sh, candidate builders, othercrit harness, audit tools
```

Large artifacts (`outputs/`, `*.gguf`, generated corpus splits) are gitignored —
the code and manifests reproduce them.

## Pipeline

| stage | script | output |
|-------|--------|--------|
| build corpus | `prepare_corpus.py` | unified ChatML JSONL + pinned `manifest.json` |
| reserve eval set | `reserve_holdout.py` | `eval_holdout.txt` (stratified) |
| train | `train_critic.py` | QLoRA adapter + merged 16-bit model |
| evaluate | `eval_critic.py` | before/after scores, model-vs-model compare |
| deploy | `export_gguf.py` + `Modelfile.qwen` | GGUF served via Ollama |
| gate | `scripts/beat_gate.sh` + `apr beat-run` | WON/REGRESSED verdict, non-zero exit on regression |

## Quickstart

```bash
# 1. build the training corpus (own examples + external mix)
python prepare_corpus.py --out ./corpus --local seed_examples.jsonl

# 2. reserve the eval holdout — BEFORE training
python reserve_holdout.py

# 3. train (Qwen shown; swap --model + --chat-template for Mistral)
python train_critic.py --model unsloth/Qwen3-8B-unsloth-bnb-4bit \
  --chat-template qwen3 --out outputs/critic-qwen3-8b --upsample 20

# 4. evaluate base vs tuned, or model vs model
python eval_critic.py --model <path> --tag <name> --chat-template <tmpl>
python eval_critic.py --compare <tag_a> <tag_b>

# 5. export for serving
python export_gguf.py --model outputs/<run>/final --out outputs/<run>/gguf
ollama create critic -f Modelfile.qwen && ollama run critic
```

The train and eval scripts are model-agnostic via `--chat-template` (`qwen3`,
`mistral`); adding a base is a one-flag change plus a marker entry.

## Reproducibility

- **Pinned inputs.** `prepare_corpus.py` records exact dataset revisions in
  `corpus/manifest.json`; every corpus is rebuildable from it.
- **Contamination firewall.** The HF-IQR benchmark is reserved as the *eval
  instrument* (`eval_holdout.txt`) and never used as training data, so the
  before/after comparison is honest.
- **Seeded runs.** Training and holdout selection are seeded.
- **Controlled comparison.** The Qwen vs Mistral study holds corpus, config,
  epochs, seed, and holdout constant; the only variable is the base model.

## Methodology principles

- **Held-out evaluation** — the benchmark is never in the training set.
- **Honest deltas** — results reported base-vs-tuned and model-vs-model, with
  regressions and tradeoffs stated, not hidden (e.g. the format-vs-capability
  tradeoff, the frontier-reasoning role drift).
- **Qualitative verification** — outputs are read, not trusted on scorer numbers
alone. This principle is what surfaced both proxy failures above; where it was
applied loosely (scoring a verdict token instead of reading the analysis),
capability was overstated.
- **Pre-registration** — batch predictions are written down with numeric
falsification criteria before the batch runs. Four were recorded and all four
failed; the failures are kept in `experiments.md` rather than removed.
- **Local upsampling** — the small hand-written set is weighted (not merely
  concatenated) against the external data so it shapes behavior without being
  drowned out.

## Program lineage

- **HF-IQR (V1-V3)** established the multi-model council methodology for
  AI critique-behavior analysis and produced the reasoning benchmark reused here
  as a held-out eval instrument:
  [V1](https://github.com/billyrdavis1985-bot/-IRMB_HF-IQR_ReasoningBenchmark) ·
  [V2](https://github.com/billyrdavis1985-bot/HF-IQR-V2-Hudson-Forge-Intelligence-and-Reasoning-Benchmark) ·
  [V3](https://github.com/billyrdavis1985-bot/HF-IQR-V3).
- **hf-critic** turns that analysis line into a *component*: distilling
  critique behavior into small local models intended as specialist verification
  reflexes for downstream agent work (Forge Agent / AURION) and the Hudson
  Forge cluster.

## Related IRMB repositories



The reasoning benchmark used here as a held-out eval instrument:

- [HF-IQR V1](https://github.com/billyrdavis1985-bot/-IRMB_HF-IQR_ReasoningBenchmark)
- [HF-IQR V2](https://github.com/billyrdavis1985-bot/HF-IQR-V2-Hudson-Forge-Intelligence-and-Reasoning-Benchmark)
- [HF-IQR V3](https://github.com/billyrdavis1985-bot/HF-IQR-V3)

**[aprender](https://github.com/paiml/aprender)** (Noah Gift / Pragmatic AI Labs)
— the pure-Rust ML framework whose BeatBenchmark contract system enforces this
repository's CI gate. Fork:
[billyrdavis1985-bot/aprender](https://github.com/billyrdavis1985-bot/aprender).
A Blackwell (sm_120) reproduction of the QLoRA finetune hang was contributed
upstream on [issue #563](https://github.com/paiml/aprender/issues/563).

## Citation

```
Davis, B. (2026). hf-critic: Fine-tuned reasoning-process evaluators as
local verification specialists. Hudson Forge Technologies LLC.
https://github.com/billyrdavis1985-bot/hf-critic
```

## License

Apache 2.0. See [LICENSE](LICENSE).

---

*Experiment. Measure. Refine. Repeat. — Hudson Forge Technologies · IRMB Research Program*
