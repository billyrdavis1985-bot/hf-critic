# Experiments — Hudson Forge Reasoning Critic

A running log of fine-tuning runs. One entry per run: setup, result, and the
lesson learned. Newest first.

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
  (Feedback-Collection, UltraFeedback, OpenThoughts3, Tulu-3). Local share
  ~8%.
- Hardware: single RTX 5070 (12GB, Blackwell) under WSL2. 2 epochs, ~15h wall.
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
- The fine-tune's clear win is *format/contract adherence* — the base model
  already detected traps well (0.975) but only emitted the required structure
  ~50% of the time; tuning pushed that to ~95%.
- Mild catastrophic forgetting: trap detection dipped 0.975 -> 0.900. Acceptable
  for a critic (still strong), but real — the price of hard format training.
- Frontier regression traced to *role drift*: on open-ended,
  knowledge-heavy prompts the base model's instinct to *explain the topic*
  overrode the critic contract (one holdout answer re-explained the simulation
  argument instead of critiquing a candidate). Under-covered question type, not
  a fine-tuning failure.
- Qualitative read (spot-checked ~10 outputs): reasoning is genuinely sound,
  not fluent-but-empty. Verified generalization on two novel traps not in
  training (widget rate, compounded discount) — both critiqued correctly with
  calibrated severity.

**Deployment.** Merged to 16-bit, exported to GGUF (Q4_K_M, 4.7GB), served via
Ollama with the system prompt baked into a Modelfile. Runs standalone on the
5070.

**Lessons for next time.**
- Python 3.14 breaks the ML stack (datasets/dill pickle error, torchvision ABI
  mismatch). Use Python 3.11.
- Long WSL2 GPU runs can throw transient `cudaErrorUnknown`. Gradient clipping
  (`max_grad_norm=1.0`) + checkpoint-every-50-steps made the run resumable; a
  mid-run crash cost only ~12 steps.
- 38 examples taught reasoning judgment but not a rigid contract — format still
  drifts on a few question types.

**v2 candidates (evidence-based).**
1. Grow seed set to 100-150, targeting the drift categories (open-ended
   frontier/meta) with candidate-response-to-critique examples that keep the
   model in critic role.
2. Try `--upsample 10` to recover the lost trap detection; measure the tradeoff.
3. Run the *same corpus + eval* on Gemma and Nemotron bases — cross-model delta
   comparison (one-flag change in the pipeline).
