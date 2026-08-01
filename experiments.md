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

## Pre-registered prediction: verification-checking probe (batch 3)

Batch 2 falsified the broad anchoring hypothesis -- tuned-Mistral caught both a
fabricated syllogism mood ("Datisi") and a false arithmetic verification
(90 - 90 = 0). A narrower pattern survived. Across batches 1-2, all three
candidate verification steps behaved the same way:

  SRQ-01 "the counts sum to 27 as required"    (no work shown) -> Mistral accepted
  TRQ-01 "all four constraints are satisfied"  (no work shown) -> Mistral accepted
  TRQ-03 "90 - 90 = 0, confirming alignment"   (work shown)    -> Mistral caught

Refined hypothesis: tuned-Mistral does not re-execute verification claims that
merely assert success, but does evaluate verification steps that display a
computation. tuned-Qwen re-executes in all three cases.

Batch 3 holds question and injected error fixed and varies only the final step
(asserted vs shown): MPQ-03, MPQ-04, SRQ-03, n=6, all corrupted.

Prediction recorded before running:
1. tuned-Mistral catches >= 2 of 3 "shown" variants and <= 1 of 3 "asserted".
2. tuned-Qwen shows no gap between the two styles.
3. If Mistral catches asserted and shown at similar rates, the refined
   hypothesis is falsified too and the batch 1-2 pattern was coincidence.

Known confound: the "shown" variants contain more text, so any detection
difference could reflect content volume rather than verification-checking.

## Pre-registered prediction: false-alarm probe (batch 4)

Batch 3 falsified the refined hypothesis: tuned-Mistral's asserted/shown rates
were identical (1/3 vs 1/3) and every pair agreed, so question identity drove
the verdicts and the batch 1-2 pattern was confounded. Mechanism is unknown and
no third hypothesis is offered from the same evidence.

Cumulative n=18: tuned-Qwen 17/18 (corrupted recall 12/12, clean 5/6);
tuned-Mistral 9/18 (corrupted recall 5/12 = 0.42, clean 4/6).

Qwen is at ceiling on corrupted detection, so the informative quantity is now
the FALSE ALARM rate on correct reasoning -- operationally decisive, since a
gate that rejects valid work gets disabled. Batch 4 is all-clean (n=8), four
questions in two styles each, to test whether presentation drives rejection.

Prediction recorded before running:
1. tuned-Qwen false-alarms on at least one terse or informal variant, and its
   false alarms concentrate in those styles rather than standard/verbose.
2. Any variant rejected on notation or presentation while the critique concedes
   the answer is correct counts as a calibration failure, as on TRQ-03-clean.
3. If both models accept all 8, false alarms are rarer than TRQ-03 suggested and
   the AURION gate risk is lower than feared.

## Study: other-critique on external reasoning (batches 1-4, n=26)

> SUPERSEDED. The severity-gating conclusion below was falsified out-of-sample in
> batch 5, and the recall figures are verdict-string counts that a later diagnosis
> audit showed to be inflated. See "Revised results" at the end of this file.

### Motivation

The published evaluation is a self-critique probe: the holdout stores no
candidate answer, so the model produces its own reasoning and then critiques it.
The deployment story is different -- the critics are meant to verify *other*
models' reasoning. This study tests that directly.

### Design

Candidates are built by controlled corruption rather than generated and then
labelled. Each question yields a clean trace (correct verdict: sound) and a
variant with one deliberate, named error (correct verdict: flawed). Labels are
known by construction, so no hand-labelling is required and the label aligns
with the critic's stated task -- unlike labelling on final-answer correctness,
which a trace can satisfy through invalid reasoning.

Questions were drawn from the 160 non-holdout HF-IQR V2 questions, so the
reserved 40-question holdout and its CI gate stay untouched. Firewall checks:
prepare_corpus.py never reads the master dataset; seed_examples.jsonl contains
no question IDs; an 8-word text-overlap scan against the 38 seeds flagged one
question (MPQ-02), which was excluded.

Harness: scripts/run_other_critique.py reuses eval_critic.run_model and replaces
only build_critique_prompt, so model loading and decoding match the published
runs. All runs use EVAL_GREEDY=1 (deterministic) and max_new 1200.

### Results (verdict-word scoring)

n=26: 12 corrupted, 14 clean.

  tuned-Qwen     24/26   corrupted recall 12/12   clean specificity 12/14
  tuned-Mistral  14/26   corrupted recall  5/12   clean specificity  9/14

tuned-Mistral falls well below the 0.6 recall threshold pre-registered as the
condition for serving as a verification gate. That conclusion held across all
four batches.

### Two falsified hypotheses

Both were pre-registered with explicit falsification criteria, and both failed.

1. *Anchoring / verification-by-paraphrase*: tuned-Mistral endorses whatever the
   candidate asserts. Batch 2 refuted it -- Mistral caught a fabricated
   syllogism mood ("Datisi") and a false arithmetic verification (90 - 90 = 0),
   both of which a paraphrasing critic should have endorsed.

2. *Verification-checking*: Mistral accepts verification steps that assert
   success but evaluates those that show work. Batch 3 held question and error
   fixed and varied only that final step. Every asserted/shown pair agreed
   (1/3 vs 1/3), so question identity drove the verdicts and the earlier pattern
   was confounded. No third hypothesis is offered from the same evidence.

### What the critique text shows

Verdict-level scoring conceals a qualitative difference. On the two clean items
tuned-Qwen flagged, it identified real defects. On the clean items tuned-Mistral
flagged, it fabricated them: it claimed an algebraic identity holds "only when k
is even" (it holds for all k), asserted that even and odd are residue classes
modulo 4, and supplied a counter-model (humans/mammals/fish) that in fact
satisfies the argument it was meant to refute. Mistral confabulates in both
directions -- inventing technical content to endorse flawed reasoning and to
reject valid reasoning.

### Label correction (disclosed)

MPQ-03-terse was authored as a correct trace but never applies the inductive
hypothesis: it states the algebraic identity k(k+1)/2 + (k+1) = (k+1)(k+2)/2,
which is unconditionally true, without establishing that the left side is the
sum to k+1. It therefore does not exhibit the structure S(k) => S(k+1). The
label was wrong; the item belongs with the corrupted set.

This correction was made after seeing results, prompted by tuned-Qwen's
critique. Both scorings are reported. The criterion -- whether the trace applies
the inductive hypothesis -- is checkable independently of which model raised it.

### Severity gating (the deployment finding)

Re-scoring saved outputs on the SEVERITY field instead of the verdict word:

  threshold >= 3   Qwen recall 12/12, specificity 13/14
                   Mistral recall  4/12, specificity  9/14
  threshold >= 4   Qwen recall  3/12, specificity 14/14
                   Mistral recall  2/12, specificity 13/14

At >= 3 tuned-Qwen loses one false alarm at no cost to recall. The recovered
item is TRQ-03-clean, which it had marked flawed at SEVERITY 2 while writing
that the answer was correct. At >= 4 recall collapses: Qwen reserves 4+ for
severe defects and rates most genuine errors 3.

Conclusion: tuned-Qwen's SEVERITY field is better calibrated than its VERDICT
word. It separates cosmetic from substantive defects but maps both to "flawed".
Recommended deployment: read SEVERITY, threshold at 3, ignore the verdict
string. With MPQ-03 relabelled this gives 13/13 recall and 13/13 specificity.

Thresholding does not rescue tuned-Mistral at any value, because its severity
ratings decorate fabricated findings.

### Limitations

- n=26, and the errors are hand-constructed. Deliberately injected flaws may be
  easier to detect than errors models make naturally, so these figures are
  plausibly an upper bound.
- The candidate traces were drafted by an LLM (Claude) and verified by the
  author against the reference solutions. One label was wrong (see above), which
  bounds how much confidence the remaining labels deserve.
- Four questions contribute two items each, so items are not independent.
- Mechanism is unknown. Two hypotheses were falsified; separating candidates
  would require a design testing several pre-specified alternatives at once.
- Severity gating was found post hoc on saved outputs. It should be
  pre-registered and tested on a fresh batch before being relied on.

## Pre-registered prediction: severity gating, out-of-sample (batch 5)

Severity gating was found post hoc by re-scoring saved outputs from batches 1-4.
Batch 5 tests it on fresh questions never shown to either critic: MPQ-07,
LSQ-12, TRQ-05, SRQ-05 (MPQ-11 excluded as a duplicate of MPQ-06; SRQ-04 and
TRQ-04 excluded as underspecified). n=8: four clean, four corrupted.

Rule under test: flag a candidate when SEVERITY >= 3, ignoring the VERDICT word.

Confirmation criterion, recorded before running: the rule confirms if tuned-Qwen
achieves recall >= 3/4 AND specificity 4/4. Anything less and the post-hoc
finding did not generalise.

Key item: TRQ-05-clean-cosmetic is arithmetically correct and reaches the right
answer (10:42, 162 miles) but omits units, AM/PM markers and labels throughout.
It is the case the rule exists to handle. If tuned-Qwen rates it SEVERITY >= 3,
the rule breaks regardless of the other seven.

Secondary: tuned-Mistral is predicted to remain below 0.6 recall at any
threshold, consistent with batches 1-4.

## Revised results: batches 1-5 (n=34) and the diagnosis audit

This section supersedes the batch 1-4 study above on two points: severity gating
and the recall figures.

### Severity gating failed out-of-sample

The rule (flag when SEVERITY >= 3, ignore the VERDICT word) was found post hoc
on batches 1-4, where it looked free: recall 12/12, specificity 13/14. Batch 5
pre-registered the criterion recall >= 3/4 AND specificity 4/4. Result: 3/4 and
3/4. Two items show why.

- TRQ-05-clean-cosmetic, arithmetically correct but stripped of units and AM/PM
  markers, scored SEVERITY 3. It is the exact case the rule existed to pass.
- MPQ-07-corrupted, where the candidate concludes a true statement is false off
  a 4 mod 3 = 0 error, scored SEVERITY 1.

Severity is miscalibrated in both directions. Cumulatively, verdict-word scoring
gives 31/34 and severity>=3 gives 31/34: the rule trades one false alarm for one
miss. The post-hoc finding did not generalise.

### Verdict-string recall overstates capability by 30-45 points

All 16 tuned-Qwen corrupted items were audited by hand against the injected
error (eval/diagnosis_audit_qwen.md). Of the 11 read in full: 6 genuine
diagnoses, 3 spurious, 2 partial or broken. Diagnosis-verified recall is
6/11 = 0.55; treating the 5 screen-only items as genuine gives a best case of
11/16 = 0.69. Verdict-word recall was 16/16.

A spurious case emits a non-endorsing verdict while the analysis certifies the
flawed content. On LSQ-03 the critic affirmed a fabricated mood classification
("AII in the third figure is Datisi ... Valid") and declared the argument form
valid -- the middle term is predicate of premise 1 and subject of premise 2,
making it first figure, mood IAI-1, invalid. It emitted VERDICT: flawed on an
unrelated objection to the soundness wording.

SRQ-03 appears twice with an identical injected error and received contradictory
diagnoses: the "shown" variant identified the omitted ceiling correctly, the
"asserted" variant claimed a shorter path exists and produced fabricated
distances. Same model, same flaw, opposite readings.

tuned-Mistral was not audited and carries the same inflation.

### What this means

Verdict-string scoring is a proxy metric: it correlates with critic capability
without measuring it. This is the same failure as trap_detection_rate's lexical
overlap, arriving independently in a harness built to avoid that class of
mistake. Any future scoring of these critics should verify the diagnosis, not
the verdict field -- which currently means hand verification, since no automatic
proxy for "named the injected error" has been validated.

### Standing on the model comparison

tuned-Mistral remains unsuitable as a verification gate, but that rests on the
aggregate rather than any single batch: 5/12 recall across batches 1-4, then 3/4
on batch 5. It also confabulates in both directions, inventing technical content
both to endorse flawed reasoning and to reject valid reasoning.

tuned-Qwen is stronger but not gate-ready on this evidence. Its diagnosis-
verified recall is 0.55-0.69, it has a confirmed false alarm with a fabricated
justification (TRQ-05-clean), and it produced contradictory diagnoses of the
same injected error.

### Limitations

n=34, errors hand-constructed, candidate traces authored by an LLM and verified
by the author with one label error found and disclosed (MPQ-03-terse). Questions
appear in multiple items, so items are not independent. One model pair. Mechanism
of failure unknown: two pre-registered hypotheses were falsified and no third is
offered from the same evidence.
