# The gate that audited its own metric

*How adopting a Rust contract system to protect a finished project ended up
dismantling its headline number — and what replaced it.*

Billy R. Davis Jr. — Hudson Forge Technologies LLC / IRMB

---

## Where this started: hf-critic was done

[hf-critic](https://github.com/billyrdavis1985-bot/hf-critic) trained two small
open-weight models into reasoning critics — models that judge the *process*
behind an answer rather than the answer itself, emitting a fixed contract of
VERDICT, STEP ANALYSIS, SEVERITY, and REVISED ANSWER.

Two bases, identical treatment: Qwen3-8B and Mistral-7B-Instruct-v0.3, both
4-bit QLoRA on the same corpus — 38 hand-written critique examples spanning all
twelve HF-IQR categories, upsampled, mixed with external instruction data. The
[HF-IQR benchmark](https://github.com/billyrdavis1985-bot/HF-IQR-V2-Hudson-Forge-Intelligence-and-Reasoning-Benchmark)
supplied a 40-question holdout reserved before training as a contamination
firewall. Both models shipped as GGUF through Ollama.

The 2×2 gave a clean story. Fine-tuning pulled both models toward the training
data's capability level from opposite directions — Qwen's trap detection down
from 0.975 to 0.900, Mistral's up from 0.800 to 0.850. Format compliance turned
out to be base-dependent: Mistral followed the output contract from the prompt
alone, Qwen needed the fine-tune to learn it.

That was written up and published. As far as I was concerned, the modelling work
was finished and the next question was operational: how do you keep a trained
critic from silently degrading?

## Studying aprender

[aprender](https://github.com/paiml/aprender) is Noah Gift's pure-Rust ML
framework. What drew me wasn't the training side — it was the contracts system:
YAML files that pin a metric baseline with falsification tests, wired so that
drift fails CI. That is a discipline I wanted, independent of language.

**Phase 1 was a wall.** `apr finetune` will not train on my hardware. The QLoRA
loop hangs at the transition into the training loop with the GPU at 0%
utilisation, reproducibly, on an RTX 5070 — compute capability 12.0, sm_120.
Existing upstream reports referenced sm_121, so my card widened the affected
range rather than duplicating a known case. I filed a reproduction on
[issue #563](https://github.com/paiml/aprender/issues/563) with the full
environment, the exact invocation, and what I had ruled out: the same dataset and
adapter config train to completion on the same card through an Unsloth pipeline,
so the stall is specific to the `apr` path rather than the hardware.

The conclusion was a boundary, not a rejection. Training stays on the working
Python pipeline. Adopt `apr` for the parts that work.

**Phase 2 was the contract.** I wrote a BeatBenchmark contract pinning
`trap_detection_rate` at the tuned-Qwen baseline of 0.900, with a threshold at
0.850, and confirmed `apr beat-run` emits WON on a passing value and REGRESSED
with a non-zero exit on a failing one.

Then I wired it to the real evaluation. A fail-closed shell script pulls the
measured rate out of the eval's summary artifact and hands it to the Rust
contract engine; a GitHub Action installs `apr` from crates.io and runs the gate
on every push. The architecture is deliberately split: **measurement stays in the
Python harness that produced every published number, enforcement is the Rust
contract engine, and a JSON summary file is the interface between them.** Nothing
about the trusted instrument had to change to gain an enforceable regression
gate.

The gate went green. A regressed critic could no longer merge.

## The question the gate forced

A gate makes you ask a question you can otherwise avoid: *what exactly is this
number, such that I'm willing to block a merge on it?*

I opened the scoring function and read it properly for the first time in months.

`trap_detection_rate` extracts words of five or more letters from the reference
solution and counts how many appear **as substrings** in the critique, passing
when hits reach `max(2, n_terms // 4)`.

That is lexical overlap, not reasoning assessment. Substring matching means a
critique arguing the *opposite* conclusion still scores — "entangled" matches
inside "not entangled". The floor of two dominates for short reference solutions:
one item's reference yielded three terms, so the single word "northwest" passed
by matching both "north" and "northwest".

A falsification test settled it. Of the ten holdout items the tuned critic
labelled **sound**, nine also scored as having **detected the flaw**. The metric
was largely independent of the critic's own judgement. Requiring the verdict not
to endorse the reasoning moved the rate from 0.900 to 0.675.

A second problem surfaced alongside it. The evaluation stores no candidate
answer, so the prompt asks the model to produce its own reasoning and then
critique that. Every published number described **self-assessment** — while the
entire deployment rationale was verifying *other* models' reasoning. Those are
different capabilities, and self-critique structurally cannot detect a critic
that simply agrees with the candidate, because agreeing with the candidate is
agreeing with itself.

There was also a reproducibility issue: the evaluation sampled at temperature 0.3
with no seed, so every published figure was a single stochastic draw. Adding a
deterministic decoding mode and verifying it bit-identical across two runs fixed
that going forward.

## Rebuilding the evaluation — and making the same mistake again

The replacement uses **controlled corruption**. Each question yields a correct
reasoning trace and a variant containing one deliberate, named error, so labels
are known by construction — no hand-labelling, and the label matches what the
critic actually claims to do. Questions came from the 160 non-holdout HF-IQR
questions, leaving the reserved holdout and its CI gate untouched.

Five batches, n=34. Every batch prediction was written into the experiment log
with a numeric falsification criterion **before** the batch ran.

Four hypotheses were recorded. All four failed.

- **Anchoring** — the weaker critic endorses whatever the candidate asserts.
  Falsified: it caught both a fabricated syllogistic mood and a false arithmetic
  verification, either of which a paraphrasing critic should have accepted.
- **Verification-checking** — it accepts verification steps that assert success
  but evaluates those that show work. Held 3/3 on early batches. A batch holding
  question and error fixed while varying only that step gave identical rates,
  with every matched pair agreeing. Question identity, not verification style,
  had been driving the verdicts.
- **Convergent failure** — both critics rejecting the same clean item indicated a
  shared blind spot. Reading the critiques showed opposite mechanisms; retracted.
- **Severity gating** — scoring on the SEVERITY field rather than the verdict
  token looked free on existing data (recall 12/12, specificity 13/14). The
  pre-registered out-of-sample criterion was recall ≥ 3/4 and specificity 4/4.
  It returned 3/4 and 3/4. A correct trace stripped of units scored SEVERITY 3;
  a candidate concluding that a true statement is false scored SEVERITY 1.

Then I read the critiques instead of the verdict field — and found the same class
of error in the new harness.

Scoring on the emitted `VERDICT:` token gave the stronger critic a recall of
16/16. Reading all sixteen against the injected error gave ten genuine diagnoses,
four spurious, two partial.

| model | verdict-string recall | diagnosis-verified | inflation |
|-------|----------------------|--------------------|-----------|
| tuned Qwen3-8B | 16/16 = 1.00 | 10/16 = 0.63 | 1.6× |
| tuned Mistral-7B | 8/16 = 0.50 | 2/16 = 0.13 | 3.8× |

A spurious catch emits a non-endorsing verdict while the analysis certifies the
flawed content. On one item a candidate asserted a fabricated syllogistic
classification and named it Datisi; **both** critics affirmed it as valid, then
emitted "flawed" over unrelated objections. On another, a candidate computed
4 mod 3 = 0 to disprove a true statement; the critic stated 4 ≡ 1 mod 3
correctly, then wrote that the candidate had computed it correctly and that the
disproof was sound — and rated it SEVERITY 1.

The inflation is larger for the weaker model. So verdict-string scoring does not
merely add noise: **it compresses the measured distance between a critic that
mostly works and one that mostly does not** — precisely the distinction a
deployment decision turns on.

## What changed in hf-critic

The repository looks different than it did before the gate went in.

- **Deterministic evaluation.** `EVAL_GREEDY=1` gives bit-identical runs,
  verified across two full passes. The published stochastic numbers are labelled
  as a single draw.
- **The contract says what it gates.** Its `notes:` block describes a regression
  canary that catches catastrophic degradation — explicitly *not* a
  reasoning-quality guarantee — with the lexical-overlap mechanism and the
  0.900 → 0.675 coherence-filtered figure stated in the file itself.
- **Claims partitioned.** The format findings hold: `verdict_rate` and
  `structure_rate` are direct string checks with large deltas, and the
  base-dependent compliance result stands. The convergence claim rests on
  two-to-three-question differences measured by a metric now known to be lexical
  overlap, and is downgraded to suggestive. The complementary-blind-spots claim
  came from self-critique; on external reasoning the weaker critic contributed no
  unique catches.
- **An audit trail anyone can check.** Per-item classifications for both critics,
  every candidate set, every run output, and the pre-registration log with its
  four falsified predictions are committed. Each classification is verifiable
  against the saved critique text.
- **Deployment posture changed.** Neither critic is currently a verification
  gate for downstream agent work. The stronger one is a plausible flag-raiser at
  0.63 verified recall; the weaker one is not usable in that role.

## What I'd take from this

**A metric you gate on is a claim you're making.** Wiring the number into CI is
what made me read the code that produces it. The audit was cheap; not having a
reason to do it was the expensive part.

**Test what your metric measures before you enforce it.** For the first failure:
can this metric pass a critique that reaches the wrong conclusion? For the
second: read the reasoning rather than the label. Neither check required new
data.

**Pre-registration is what makes negative results legible.** Without a criterion
written down beforehand, my first mechanism hypothesis would have been written up
after batch one and been wrong in public. Instead there are four falsifications
in the log, and the one scoring rule that looked free on existing data was caught
by fresh items rather than by a reviewer.

**The boundary between languages was the right call.** Rust enforces, Python
measures, JSON connects them. When the Blackwell hang closed off Rust training,
that split meant adopting the useful half cost nothing.

The open problem is the one this work names and does not solve: **what a valid
automatic measure of critique quality would look like.** Hand verification is
sound and does not scale. Matching a revised answer against a reference, or using
a second model as judge, each reintroduces a proxy whose validity would itself
need demonstrating — and the second forfeits the independence that made this
study interpretable. Until that has an answer, scaling the study just produces
more numbers of a kind I've already disowned.

---

## Links

- **hf-critic** — code, contracts, candidate sets, per-item audits:
  https://github.com/billyrdavis1985-bot/hf-critic
- **Experiment log** — pre-registrations, falsified predictions, revised results:
  https://github.com/billyrdavis1985-bot/hf-critic/blob/master/experiments.md
- **Diagnosis audits** —
  [Qwen](https://github.com/billyrdavis1985-bot/hf-critic/blob/master/eval/diagnosis_audit_qwen.md) ·
  [Mistral](https://github.com/billyrdavis1985-bot/hf-critic/blob/master/eval/diagnosis_audit_mistral.md)
- **aprender** (Noah Gift / Pragmatic AI Labs): https://github.com/paiml/aprender
  · fork: https://github.com/billyrdavis1985-bot/aprender
- **Blackwell reproduction, issue #563**:
  https://github.com/paiml/aprender/issues/563
- **HF-IQR benchmark** —
  [V1](https://github.com/billyrdavis1985-bot/-IRMB_HF-IQR_ReasoningBenchmark) ·
  [V2](https://github.com/billyrdavis1985-bot/HF-IQR-V2-Hudson-Forge-Intelligence-and-Reasoning-Benchmark) ·
  [V3](https://github.com/billyrdavis1985-bot/HF-IQR-V3)

*Developed as part of MLOps coursework with Alfredo Deza and Noah Gift.*
