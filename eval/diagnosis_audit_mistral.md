# Diagnosis audit: tuned-Mistral corrupted items (batches 1-5)

Same question as the Qwen audit: does the STEP ANALYSIS name the *injected*
error, or flag something else while accepting the flawed content?

Eight of the sixteen items were outright misses (VERDICT: sound), which cannot
be spurious catches. The remaining eight were read in full.

| batch | item | verdict | classification |
|---|---|---|---|
| b1 | MPQ-16 corrupted | flawed | **partial/broken** |
| b1 | LSQ-01 corrupted | sound | miss |
| b1 | SRQ-01 corrupted | sound | miss |
| b2 | TRQ-03 corrupted | unsound | genuine (own figures wrong) |
| b2 | LSQ-03 corrupted | flawed | **spurious** |
| b2 | TRQ-01 corrupted | sound | miss |
| b3 | MPQ-03 corrupted-asserted | sound | miss |
| b3 | MPQ-03 corrupted-shown | sound | miss |
| b3 | MPQ-04 corrupted-asserted | flawed | **spurious** |
| b3 | MPQ-04 corrupted-shown | flawed | **spurious** |
| b3 | SRQ-03 corrupted-asserted | sound | miss |
| b3 | SRQ-03 corrupted-shown | sound | miss |
| b5 | MPQ-07 corrupted | sound | miss |
| b5 | LSQ-12 corrupted | unsound | genuine |
| b5 | TRQ-05 corrupted | flawed | **spurious** |
| b5 | SRQ-05 corrupted | flawed | **spurious** |

## Tally

8 misses, 5 spurious, 1 partial/broken, 2 genuine.
Diagnosis-verified recall = 2/16 = 0.13, against a verdict-string recall of
8/16 = 0.50.

## Comparison with tuned-Qwen

| | verdict-string | diagnosis-verified | inflation factor |
|---|---|---|---|
| tuned-Qwen | 16/16 = 1.00 | 10/16 = 0.63 | 1.6x |
| tuned-Mistral | 8/16 = 0.50 | 2/16 = 0.13 | 4.0x |

The inflation is larger for the weaker model. Verdict-string scoring therefore
does not merely add noise: it compresses the measured distance between a critic
that mostly works and one that mostly does not.

## Selected spurious cases

**LSQ-03.** "The formal analysis is correct: AII in the third figure is Datisi,
and Datisi is traditionally recognized as valid." The classification was
fabricated by the candidate. tuned-Qwen affirmed the same claim on the same item.

**MPQ-04, both variants.** The injected error reduces the odd case to 0 mod 4
instead of 1. The asserted variant drew "The odd case is also handled correctly:
n^2 = 4k^2 + 4k + 1 = 0 mod 4", with a revised answer claiming both 1 and 9 are
0 mod 4. The shown variant invented supporting algebra: "reduces to
4(k^2 + k + 0.25), which is divisible by 4."

**SRQ-05.** "The initial observation is correct — opposite faces sum to 6." The
rule is that they sum to 7; every derived pairing follows from the false rule.

**MPQ-16 (partial).** Step 2 gestures at the proof-by-example objection, but
step 1 is incoherent ("three cases are enough to guarantee a pattern holds for
all natural numbers? No, but four is") and the revised answer disproves a true
statement: "6 x 6 = 36, which is divisible by 4 but not by 2 + 4."

## Note on the shared failure

LSQ-03 is the one item where both critics affirmed the same fabricated claim.
This is a single item and is recorded as an observation, not a finding.
