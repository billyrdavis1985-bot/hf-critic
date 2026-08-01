# Verdict-string scoring can inflate measured critic capability: a controlled-corruption case study

*Draft. Billy R. Davis Jr., Hudson Forge Technologies / IRMB.*

## Abstract

Reasoning critics are evaluated by proxy. This paper reports two independent
cases where a proxy metric correlated with critic capability without measuring
it, and in both cases overstated it substantially. The first was a lexical
overlap score used as a trap-detection rate. The second appeared in a harness
built specifically to avoid that failure: scoring a critic on the verdict token
it emits rather than on whether its analysis identifies the injected error.
Hand verification of all 16 corrupted items put diagnosis-verified recall at
0.63 against a verdict-string recall of 1.00. The magnitude is specific to these
models and these constructed errors; the demonstration that the two scorings can
diverge this far is the transferable result.

## 1. Two proxy failures

A critic model judges the reasoning behind an answer and emits a structured
verdict. Measuring whether it does this well is harder than measuring whether an
answer is correct, and the usual response is a proxy.

**Proxy one: lexical overlap.** The original evaluation scored trap detection by
extracting content words from a reference solution and checking how many appear
in the critique, passing at `hits >= max(2, n_terms // 4)`. Matching was on
substrings, so a critique reaching the opposite conclusion still scored. The
floor of two dominated for short reference solutions: for one item the reference
yielded three terms, and the single word "northwest" satisfied the threshold by
matching both "north" and "northwest".

The metric was largely independent of the critic's own judgement. Of ten items
the critic labelled "sound", nine also scored as having detected the flaw.
Requiring the verdict not to endorse the reasoning moved the rate from 0.900 to
0.675.

**Proxy two: the verdict token.** The replacement harness scored a critic by
parsing `VERDICT:` and comparing it to a known label. This looked sound, since
labels were known by construction. It was not: a critic can emit a
non-endorsing verdict while its analysis certifies the flawed content. Section 5
quantifies how often that happened.

## 2. Setting

Two critics, both QLoRA fine-tunes on the same corpus: Qwen3-8B and
Mistral-7B-Instruct-v0.3. Both emit a fixed contract of VERDICT
(sound/flawed/unsound), STEP ANALYSIS, SEVERITY 1-5, and REVISED ANSWER.

The original evaluation had a further validity problem worth stating, because it
motivated everything below. Its holdout stores no candidate answer, so the
prompt asks the model to produce its own reasoning and then critique that. Every
published number therefore describes self-assessment, while the intended
deployment is verifying other models' reasoning. Self-critique cannot detect a
critic that simply agrees with the candidate, because agreeing with the
candidate is agreeing with itself.

## 3. Method: controlled corruption

Candidates are constructed, not generated and then labelled. Each question
yields a clean trace whose correct verdict is "sound", and a variant containing
one deliberate, named error whose correct verdict is "flawed". Labels are known
by construction.

The alternative -- generating candidates from a model and labelling them on
final-answer correctness -- repeats the proxy mistake, because a trace can reach
the correct answer through invalid reasoning. Several items here were built
specifically to exercise that case.

Questions were drawn from a 160-question pool disjoint from the reserved
evaluation holdout. Three contamination checks were run: the corpus preparation
script does not open the question dataset, no hand-written training example
references a question by identifier, and an 8-word text-overlap scan against
those examples excluded one further question. These do not rule out paraphrased
overlap, and the roughly 7,900 externally sourced training rows were not
inspected for shared provenance.

Five batches, n=34: 16 corrupted, 18 clean. All runs used greedy decoding,
verified bit-identical across repeated runs before the study began.

## 4. Pre-registration

Each batch's prediction was written to the experiment log with an explicit
numeric falsification criterion before the batch ran. Four hypotheses were
recorded and all four failed.

1. **Anchoring.** The weaker critic endorses whatever the candidate asserts.
   Falsified: it caught both a fabricated syllogistic mood and a false
   arithmetic verification, either of which a paraphrasing critic should have
   accepted.
2. **Verification-checking.** It accepts verification steps that assert success
   but evaluates those that show work. This held 3/3 on earlier batches. A batch
   holding question and error fixed while varying only that final step gave
   identical rates (1/3 vs 1/3), with every matched pair agreeing. Question
   identity, not verification style, drove the verdicts.
3. **Convergent failure.** Both critics rejecting the same clean item indicated
   a shared blind spot. Reading the critiques showed opposite mechanisms; the
   claim was retracted.
4. **Severity gating.** Flagging on SEVERITY >= 3 rather than the verdict token
   looked free on saved outputs (recall 12/12, specificity 13/14). The
   out-of-sample criterion was recall >= 3/4 and specificity 4/4; the result was
   3/4 and 3/4. A correct trace stripped of units scored SEVERITY 3, while a
   candidate concluding that a true statement is false scored SEVERITY 1.
   Cumulatively the two scorings are indistinguishable at 31/34, trading one
   false alarm for one miss.

No fifth hypothesis is offered from the same evidence. Distinguishing mechanisms
would require a design testing several pre-specified candidates simultaneously.

## 5. The diagnosis audit

Verdict-string scoring gave the stronger critic a corrupted-item recall of
16/16. Each item was then read against its injected error and classified as
genuine, spurious, or partial.

All 16 were read: 10 genuine, 4 spurious, 2 partial or broken.
Diagnosis-verified recall is 10/16 = 0.63.

Three of the four spurious cases share a shape: the critic affirms a false
general rule stated by the candidate, then checks the candidate's arithmetic
against that rule rather than checking the rule. This is an observation from the
audit rather than a tested hypothesis, and it is offered as a direction, not a
finding.

**A fabricated classification, affirmed.** A candidate labelled a syllogism as
mood AII in the third figure, naming it Datisi, and concluded validity. The
critic affirmed this: "AII in the third figure is Datisi, which is indeed listed
in the traditional valid moods. Valid." The middle term is the predicate of the
first premise and the subject of the second, which is the first figure; the mood
is IAI-1, invalid. The critic missed the injected error entirely and emitted
"flawed" over an unrelated objection to the soundness wording.

**An arithmetic error, endorsed.** A candidate computed 4 mod 3 = 0 and
concluded that a true statement is false. The critic stated 4 = 1 mod 3
correctly, then wrote that the candidate had computed this correctly, then that
"the statement is false, and the disproof is correct". It rated the item
SEVERITY 1 and emitted "unsound".

**A substituted objection.** A candidate ignored a 90-mile head start. The
critic called four of five steps correct, described the erroneous outputs as
"accurately derived" and "the right distance", and raised an unrelated objection
about which distance a figure referred to.

One further observation: an identical injected error presented in two variants
received contradictory diagnoses from the same model. One variant identified the
omitted surface correctly; the other claimed a shorter path existed and produced
fabricated distances.

The weaker critic was not audited and its figures carry the same inflation. Its
verdict-string numbers were recall 8/16 and specificity 11/18.

## 6. Discussion

The two proxy failures share a structure. Both metrics move with critic
capability across easy cases, which is what makes them look valid. Both come
apart on the cases that matter: a critique that mentions the right vocabulary
while reaching the wrong conclusion, or emits the right token while endorsing
the wrong content.

This has a practical consequence for deployment. A verification gate that scores
its critic on the verdict field will count agreement-with-the-error as a
successful catch. No downstream pipeline outcomes were measured here, so the
argument is about detectability rather than net harm: a spurious catch produces
an approval carrying the authority of a check that did not occur, and it will
not appear in the gate's own metrics.

The open problem is what to score instead. Hand verification is valid and does
not scale. Automatic alternatives -- matching the revised answer against a
reference, or using a second model as judge -- each reintroduce a proxy whose
validity would itself need demonstrating, and the second forfeits the
independence that made this study interpretable. This work does not solve it,
and further scaling is blocked until it is solved.

## 7. Limitations

n=34, with hand-constructed errors that are plausibly easier to detect than
errors models make naturally, making these figures an upper bound. Candidate
traces were drafted with LLM assistance and verified by the author; one label
was wrong and is disclosed in the experiment log, which bounds the confidence
the remaining labels deserve. That error was identified by a critic's own
critique. Questions appear in multiple items, so items are not independent. One
model pair, one corpus, one fine-tuning recipe. The mechanism of critic failure
remains unknown.

The weaker critic's unsuitability as a verification gate rests on the aggregate
rather than any single batch: recall was 5/12 across four batches and 3/4 on the
fifth.

## 8. Availability

Candidate sets, harness, per-item results, the diagnosis audit, and the
pre-registration log with its falsified predictions are in the project
repository. Every classification in Section 5 is checkable against the saved
critique text.
