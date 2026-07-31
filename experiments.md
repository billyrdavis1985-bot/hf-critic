# Experiments — Hudson Forge Reasoning Critic

A running log of fine-tuning runs. One entry per run: setup, result, and the
lesson learned. Newest first.

---

## Addendum: base-Mistral baseline closes the 2x2 (2026-07-25)

Caught before publication: the comparison had no base-Mistral row — tuned-Mistral
had only ever been compared to tuned-Qwen. Ran the missing eval
(`--tag base-mistral --chat-template mistral`). Result:

| metric              | base-Mistral | tuned-Mistral | delta  |
|---------------------|--------------|---------------|--------|
| verdict_rate        | 1.000        | 1.000         | +0.000 |
| structure_rate      | 0.950        | 1.000         | +0.050 |
| trap_detection_rate | 0.800        | 0.850         | +0.050 |
| mean_score_3        | 2.750        | 2.850         | +0.100 |

Per-category deltas (tuning): frontier +0.67, temporal +0.50, ethical +0.33,
syllogism +0.25; spatial -0.50; rest unchanged.

**This revises the headline finding.** Base Mistral already followed the output
contract from the system prompt alone (verdict 1.000 untrained) — so "tuning
taught the contract on both" holds only for Qwen. And Mistral's trap detection
ROSE with tuning (0.800 -> 0.850) while Qwen's fell (0.975 -> 0.900): the two
converged from opposite directions toward the training data's implicit
capability level. Revised statement: *fine-tuning pulls a model toward its
data — down from above, up from below* — rather than "teaches format, not
capability."

Caveats: n=40, so 0.05 = two questions; convergence is consistent, not proven.
Lesson recorded: an incomplete comparison (missing baseline) nearly shipped a
cleaner, wronger conclusion. The 2x2 is the minimum honest design.

---

## Cross-model comparison — Qwen3-8B vs Mistral-7B (2026-07-25)

**Goal.** Hold everything constant except the base model, and measure how the
same critic fine-tune behaves on a different dense transformer. The question:
does fine-tuning help a weaker base *more* (moving reasoning) or just teach
format? Controlled variable = base model only.

**Setup (identical across both).**
- Same corpus (38 upsampled x20 + ~7,900 external, ~8% local share).
- Same LoRA config (rank 16), same 2 epochs, same seed, same 40-question
  stratified holdout.
- Bases: Qwen3-8B (Apache 2.0) and Mistral-7B-Instruct-v0.3 (Apache 2.0) —
  both dense, so architecture is held constant. Only Mistral is an older
  generation; note that as the one uncontrolled confound.
- Pipeline change: parameterized the chat template (\`--chat-template\`) in
  both train and eval scripts. Qwen uses \`<|im_start|>\` markers; Mistral uses
  \`[INST]\`/\`[/INST]\` and has NO system role (system prompt folds into the
  first user turn). Eval also needed an explicit EOS so Mistral generation
  terminates.

**Result (40Q holdout).**

| metric              | tuned-Qwen | tuned-Mistral | delta  |
|---------------------|------------|---------------|--------|
| verdict_rate        | 0.950      | 1.000         | +0.050 |
| structure_rate      | 0.950      | 1.000         | +0.050 |
| trap_detection_rate | 0.900      | 0.850         | -0.050 |
| mean_score_3        | 2.800      | 2.850         | +0.050 |

Per-category, tied at 3.0 everywhere EXCEPT where they diverge:
- Mistral wins: frontier_reasoning +0.67, meta_reasoning +0.34,
  quantum_reasoning +0.33.
- Qwen wins: counterfactual +0.50.

**Findings.**

1. **Format is learnable; raw capability is not manufactured.** Mistral (the
   weaker/older base) hit *perfect* format adherence — verdict and structure
   both 1.000 — but trailed on trap detection (0.850 vs 0.900). Fine-tuning
   taught the contract completely on both models, but couldn't give Mistral
   reasoning capability its base lacked. Clearest answer to the guiding
   question: fine-tuning teaches behavior/format, it does not close a
   base-capability gap.

2. **Complementary, uncorrelated blind spots.** Aggregate scores nearly tie,
   but that hides the real result: the two models fail in *different*
   categories. Mistral is strong exactly where Qwen was weakest
   (frontier_reasoning — Qwen's worst regression vs its own base). Qwen is
   strong where Mistral slips (counterfactual). Because the blind spots don't
   overlap, running BOTH as cross-checks covers more than either alone. This
   empirically supports a redundant, multi-critic design rather than picking a
   single "winner." (Ties to the HF-IQR finding on correlated blind spots in
   same-family judges — different bases give the decorrelation.)

3. **Qualitative caveat.** Format numbers are trustworthy, but the keyword
   scorer can't fully judge the reasoning *inside* the steps. Mistral's ADV-09
   produced perfect structure while its embedded arithmetic was shaky. So
   "perfect format" (1.000) is not "perfect reasoning" — a proper calibration
   measurement (when it says "sound," is it?) is the next instrument needed,
   and the HF-IQR line is built for exactly that.

**Operational note.** Mistral run was clean, ~4h, no crash (gradient clipping
from the v1 fix already baked in). Both models exported to GGUF Q4_K_M
(~4.1-4.7GB) and stored on the backup SSD alongside each other.

**Decision.** Proceed with BOTH as complementary specialists, not one. The
comparison's value was not "which is best" but "how do they differ" — and they
differ in a way (uncorrelated failure modes) that makes the pair more useful
than either single model.

---

## v1 — Qwen3-8B QLoRA reasoning critic (2026-07-24)

**Goal.** Fine-tune an open-source base model into a *reasoning-process
evaluator*: given a question + candidate response, judge the reasoning itself
(not just answer correctness) and emit a fixed contract — VERDICT
(sound/flawed/unsound), STEP ANALYSIS, SEVERITY (1-5), REVISED ANSWER.

**Setup.**
- Base model: Qwen3-8B (Apache 2.0), 4-bit QLoRA, LoRA rank 16.
- Corpus: 38 hand-written critique examples (all 12 HF-IQR V2 categories),
  upsampled 20x, mixed with ~7,900 external instruction/critique rows
  (Feedback-Collection, UltraFeedback, OpenThoughts3, Tulu-3). Local share ~8%.
- Hardware: single RTX 5070 (12GB, Blackwell) under WSL2. 2 epochs, ~8h wall.
- Eval: 40-question stratified holdout from HF-IQR V2, reserved BEFORE training
  as a contamination firewall. Same script scores base and tuned.

**Result (base -> tuned, 40Q holdout).**

| metric                | base  | tuned | delta  |
|-----------------------|-------|-------|--------|
| verdict_rate          | 0.525 | 0.950 | +0.425 |
| structure_rate        | 0.500 | 0.950 | +0.450 |
| trap_detection_rate   | 0.975 | 0.900 | -0.075 |
| mean_score_3          | 2.000 | 2.800 | +0.800 |

Biggest per-category gains where the base was weakest: logical_syllogism
(+1.75), quantum_reasoning (+1.67), probabilistic (+1.50), mathematical_proof
(+1.25). One category regressed: frontier_reasoning (-0.34).

**Interpretation.**
- The fine-tune's clear win is *format/contract adherence* — the base already
  detected traps well (0.975) but only emitted the required structure ~50% of
  the time; tuning pushed that to ~95%.
- Mild catastrophic forgetting: trap detection dipped 0.975 -> 0.900.
  Acceptable for a critic, but real — the price of hard format training.
- Frontier regression traced to *role drift*: on open-ended, knowledge-heavy
  prompts the base model's instinct to *explain the topic* overrode the critic
  contract. Under-covered question type, not a fine-tuning failure.
- Qualitative read (~10 outputs): reasoning genuinely sound, not
  fluent-but-empty. Verified generalization on two novel traps not in training
  (widget rate, compounded discount) — both critiqued correctly.

**Deployment.** Merged to 16-bit, exported to GGUF (Q4_K_M, 4.7GB), served via
Ollama with the system prompt baked into a Modelfile. Runs standalone.

**Lessons.**
- Python 3.14 breaks the ML stack (datasets/dill, torchvision ABI). Use 3.11.
- Long WSL2 GPU runs can throw transient \`cudaErrorUnknown\`. Gradient clipping
  + checkpoint-every-50-steps made it resumable; a crash cost only ~12 steps.
- 38 examples taught reasoning judgment but not a rigid contract — format still
  drifts on a few question types.

## Methods limitations (added after post-hoc audit)

**Decoding.** The published table was measured with `temperature=0.3,
do_sample=True` and no seed — a single stochastic draw. A re-run moved
structure_rate by one question and shifted 5 of 12 category means (sum of
absolute deltas 1.83) while aggregates stayed nearly flat: aggregate stability
masked item-level churn. `EVAL_GREEDY=1` adds deterministic decoding, verified
bit-identical across two runs. Greedy tuned-Qwen: verdict .925 / structure .900 /
trap .900 / mean 2.725.

**What trap_detection_rate measures.** It is a bag-of-words overlap check between
ground_truth and the critique, not a reasoning judgement — substring matching,
threshold `max(2, n_terms//4)`. For short reference solutions the floor of 2
dominates. 9 of 10 rows the critic called "sound" also scored trap_detected=True;
requiring a non-endorsing verdict gives 0.675 rather than 0.900.

**Self-critique, not other-critique.** The holdout stores no candidate response,
so the prompt asks the model to answer and then critique its own reasoning. All
results characterise self-assessment. Whether these critics evaluate *other*
models' reasoning as well is untested and is the next study.

**Annotated traps.** Only 4 of 40 rows carry a trap_type. On those 4 the tuned
critic flagged every one with a non-endorsing verdict. n=4.

## Pre-registered prediction: other-critique anchoring probe (batch 2)

Pilot (n=6, batch 1) gave tuned-Qwen 6/6 and tuned-Mistral 3/6. Reading the
Mistral critiques suggested a mechanism rather than a knowledge gap:
verification-by-paraphrase. On LSQ-01 it endorsed both a candidate claiming the
middle term was distributed and a candidate claiming it was undistributed. On
SRQ-01 it accepted a verification step that asserted a sum it never computed.

Prediction recorded before running batch 2:
1. tuned-Mistral's misses will concentrate on corrupted variants, not clean ones.
2. tuned-Qwen will not show the same concentration.
3. If tuned-Mistral catches TRQ-03-corrupted (a checkable arithmetic falsehood:
   hands coincide at 3:15, "verified" as 90 - 90 = 0), the anchoring hypothesis
   is weakened -- a paraphrasing critic should endorse it.
4. LSQ-03-corrupted asserts a fabricated mood ("Datisi") for a form it does not
   fit. Endorsement indicates deference to confident terminology.

Batch 2 candidates: TRQ-03, LSQ-03, TRQ-01 (paired clean/corrupted, n=6).
Labels known by construction. Decoding: EVAL_GREEDY=1, max_new 1200.
