# Methods note: auditing my own trap-detection metric

*Follow-up to the two-critic reasoning experiment.*

Since publishing that piece I audited the evaluation code behind its headline
number. Part of what I reported holds up. Part of it needs qualifying, and one
metric turned out not to measure what its name says. This note separates the
three, because a reader deciding whether to build on that work should know which
part is which.

## What stands

The format results are unaffected. `verdict_rate` and `structure_rate` are
direct string checks on the model's output — no proxy, no interpretation. The
deltas there are large: base Qwen3-8B emitted a parseable verdict on 52.5% of
holdout items and the required section structure on 50%, and the fine-tune took
both to 95%. Mistral-7B-Instruct-v0.3 scored 1.000 and 0.950 on the same two
metrics before any fine-tuning at all.

One caveat even here: `verdict_rate` checks only that the literal string
"verdict:" appears, not that the value is one of sound/flawed/unsound. One
holdout item parsed as "model". The metric is a proxy for contract compliance
too, just a much tighter one than the metric discussed below.

That contrast is the finding I'd still stand behind: **whether a fine-tune is
needed for format compliance depends on the base model, not on the task.** If
you are fine-tuning primarily to get structured output, test whether your base
already does it. Mine did, and I would not have known without running the 2x2.

## What needs qualifying

The convergence claim — that fine-tuning pulled both models toward the training
data's capability level, lowering Qwen's trap detection from .975 to .900 and
raising Mistral's from .800 to .850 — rests on differences of two and three
questions out of forty, measured by the metric discussed below. I now think that
claim is suggestive rather than established, and I would not build on it.

The "complementary blind spots" framing has a further problem. It came from
per-category means on an evaluation where each model critiques its own reasoning.
When I later tested both models on external reasoning, the weaker critic
contributed no unique catches that the stronger one missed. Whatever
complementarity showed up in the original numbers did not transfer.

## What was wrong

`trap_detection_rate` is not a measure of trap detection. Reading my own scoring
function: it extracts words of five or more letters from the reference solution
and checks how many appear as substrings in the critique, passing when hits reach
`max(2, n_terms // 4)`.

Three consequences follow. Substring matching means a critique arguing the
opposite conclusion still scores — "entangled" matches inside "not entangled".
The floor of two dominates for short references: one item's reference yielded
three terms, so the single word "northwest" passed by matching both "north" and
"northwest". And because the evaluation asks the model to answer the question and
then critique its own answer, shared vocabulary with the reference is close to
guaranteed.

The metric is largely independent of the critic's own judgement. Of ten items the
model labelled "sound", nine also scored as having detected the flaw. Requiring
the verdict not to endorse the reasoning moves the rate from .900 to .675.

I have not retracted the number, but I have documented what it measures, and the
CI contract that gates on it now describes itself as a regression canary rather
than a reasoning-quality guarantee.

## The same mistake, twice

I rebuilt the evaluation to avoid this. Candidates are now constructed rather
than generated: each question gets a correct reasoning trace and a variant
containing one deliberate, named error, so labels are known by construction. Five
batches, thirty-four items, every prediction pre-registered with a numeric
falsification criterion before the batch ran. Four hypotheses were recorded and
all four failed, including one of my own scoring rules that looked free on
existing data and did not survive fresh items.

Then I read the critiques instead of the verdict field, and found the same class
of error in the new harness. Scoring on the emitted verdict gave the stronger
critic a recall of 16/16. Reading all sixteen against the injected error gave
ten genuine diagnoses, four spurious, and two partial: 0.63.

A spurious case emits a non-endorsing verdict while its analysis certifies the
flawed content. On one item the candidate asserted a fabricated syllogistic
classification; the critic affirmed it as valid, then emitted "flawed" over an
unrelated objection. On another the candidate computed 4 mod 3 = 0 to disprove a
true statement; the critic stated 4 = 1 mod 3 correctly, then wrote that the
candidate had computed it correctly and that the disproof was sound.

Both metrics — lexical overlap and verdict-string matching — correlate with
capability on easy cases, which is exactly what makes them look valid. Both come
apart on the cases that matter.

## What I would tell someone building on this

Test what your metric measures before you gate on it. The check that found both
problems was cheap: for the first, ask whether the metric can pass a critique
that reaches the wrong conclusion. For the second, read the reasoning rather than
the label. Neither required new data.

Pre-registration is what made the failures visible. Without it I would have
written up my first mechanism hypothesis after batch one and been wrong in
public.

The code, per-item results, the pre-registration log with its falsified
predictions, and the full diagnosis audit are in the repository. Every
classification is checkable against the saved critique text.
