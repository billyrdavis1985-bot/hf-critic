# Diagnosis audit: tuned-Qwen corrupted items (batches 1-5)

Question for each item: does the STEP ANALYSIS name the *injected* error, or
does it flag something else while accepting the flawed conclusion?

Verdict-word recall was 16/16. Hand verification gives a different picture.

| batch | item | verdict | sev | classification |
|---|---|---|---|---|
| b1 | MPQ-16 corrupted | unsound | 4 | genuine |
| b1 | LSQ-01 corrupted | flawed | 3 | genuine (incomplete refutation) |
| b1 | SRQ-01 corrupted | flawed | 3 | genuine (revised answer: "3 edges per axis x 4 axes") |
| b2 | TRQ-03 corrupted | unsound | 4 | genuine |
| b2 | LSQ-03 corrupted | flawed | 3 | **spurious** |
| b2 | TRQ-01 corrupted | flawed | 3 | **partial** |
| b3 | MPQ-03 corrupted-asserted | flawed | 4 | not fully read (screen only) |
| b3 | MPQ-03 corrupted-shown | flawed | 3 | not fully read (screen only) |
| b3 | MPQ-04 corrupted-asserted | flawed | 3 | not fully read (screen only) |
| b3 | MPQ-04 corrupted-shown | flawed | 3 | genuine (muddled sub-point on the n=3 test) |
| b3 | SRQ-03 corrupted-asserted | flawed | 3 | **broken** (directionally wrong) |
| b3 | SRQ-03 corrupted-shown | flawed | 3 | genuine diagnosis, broken revision |
| b5 | MPQ-07 corrupted | unsound | 1 | **spurious** |
| b5 | LSQ-12 corrupted | unsound | 5 | not fully read (screen only) |
| b5 | TRQ-05 corrupted | flawed | 3 | **spurious** |
| b5 | SRQ-05 corrupted | flawed | 3 | not fully read (screen only) |

## Tally

Of the 11 items read in full: 6 genuine, 3 spurious, 2 partial/broken.
Diagnosis-verified recall = 6/11 = 0.55. Treating the 5 screen-only items as
genuine gives a best case of 11/16 = 0.69.

Verdict-word recall (16/16 = 1.00) overstates capability by 30-45 points.

## The three spurious cases

**b2 LSQ-03.** The candidate asserted a fabricated form classification: mood AII
in the third figure, named Datisi. tuned-Qwen affirmed it -- "AII in the third
figure is Datisi, which is indeed listed in the traditional valid moods. Valid"
-- and concluded the argument form is valid. But the middle term here is the
predicate of premise 1 and the subject of premise 2, which is the first figure,
not the third; the mood is IAI-1, which is invalid. The injected error was
missed entirely. The critic flagged only the soundness wording, and emitted
VERDICT: flawed on that basis.

**b5 MPQ-07.** The candidate computed 4 mod 3 = 0 and concluded a true statement
is false. tuned-Qwen stated 4 = 1 mod 3 correctly, then wrote "the candidate
correctly computed this", then "The statement is false, and the disproof is
correct". It endorsed the false conclusion, rated the item SEVERITY 1, and
emitted VERDICT: unsound.

**b5 TRQ-05.** The candidate ignored Train A's 90-mile head start. tuned-Qwen
called steps 1, 3, 4 and 5 correct, described 1.8 hours as "accurately derived"
and 198 miles as "the right distance" -- both outputs of the injected error --
and raised an unrelated objection about which distance "270 miles" refers to.

## Same error, contradictory diagnoses

SRQ-03 appears twice with an identical injected error (the unfolding omits the
3m ceiling; the candidate's 14.42m is an underestimate of the true 22.47m).

- corrupted-shown: correct direction -- "the spider-to-fly path crosses floor to
  wall to ceiling, not floor to wall only" -- but the revised arithmetic wanders
  through 17, 25 and 16.28 without reaching 22.47.
- corrupted-asserted: wrong direction -- claims a *shorter* path exists at 15m
  and 12.69m, both fabricated.

## Methodological consequence

Verdict-string scoring is not a valid measure of critic capability. A critic can
emit a non-endorsing verdict while its analysis certifies the flawed content,
and any harness reading the verdict field counts that as a detection.

This is the same failure mode as trap_detection_rate's lexical overlap: a proxy
that correlates with the target property without measuring it. It appeared here
in a harness built specifically to avoid that class of mistake.

tuned-Mistral's numbers were not audited and carry the same inflation.
