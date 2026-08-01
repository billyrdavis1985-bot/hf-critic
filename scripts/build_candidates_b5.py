#!/usr/bin/env python3
"""Batch 5: out-of-sample test of the severity>=3 gating rule.
Fresh questions. 4 clean (one with a purely cosmetic defect) + 4 corrupted."""
import json
from pathlib import Path
C = []
def add(qid, variant, label, prompt, cand, err=None, note=None):
    C.append(dict(id=qid, variant=variant, label=label, error_type=err,
                  note=note, prompt=prompt, candidate=cand))

P7 = "Prove or disprove: If a\u00b2 is divisible by 3 then a is divisible by 3. State your proof method."
add("MPQ-07", "clean", "sound", P7, """Step 1: Method: proof by contrapositive. It suffices to show that if a is not divisible by 3, then a^2 is not divisible by 3.
Step 2: If 3 does not divide a, then a is congruent to 1 or 2 modulo 3. These are the only non-zero residues.
Step 3: If a = 1 mod 3, then a^2 = 1 mod 3.
Step 4: If a = 2 mod 3, then a^2 = 4 = 1 mod 3.
Step 5: In both cases a^2 = 1 mod 3, so a^2 is not divisible by 3. The contrapositive holds.
Conclusion: The statement is true, proved by contrapositive.""")
add("MPQ-07", "corrupted", "flawed", P7, """Step 1: Method: proof by contrapositive. Assume 3 does not divide a and examine a^2.
Step 2: If 3 does not divide a, then a is congruent to 1 or 2 modulo 3.
Step 3: If a = 1 mod 3, then a^2 = 1 mod 3, so a^2 is not divisible by 3.
Step 4: If a = 2 mod 3, then a^2 = 4 = 0 mod 3, so a^2 IS divisible by 3 while a is not.
Step 5: Step 4 is a counterexample to the claim.
Conclusion: The statement is false, disproved by the residue-2 case.""",
 err="arithmetic: 4 mod 3 is 1, not 0; yields a wrong conclusion (disproof of a true statement)")

P12 = "Evaluate: Some doctors are surgeons. Some surgeons are women. Therefore some doctors are women. Valid? If not explain why with a counter-example using sets described in words."
add("LSQ-12", "clean", "sound", P12, """Step 1: Both premises are particular affirmatives (I propositions). The middle term is "surgeons".
Step 2: In Premise 1 the middle term is the predicate of a particular affirmative, so it is undistributed. In Premise 2 it is the subject of a particular affirmative, so it is also undistributed.
Step 3: A valid syllogism requires the middle term to be distributed in at least one premise. It is distributed in neither, so this commits the fallacy of the undistributed middle.
Step 4: Counter-example: let every surgeon who is also a doctor be male, and let every female surgeon be someone who is not a doctor. Then some doctors are surgeons is true, some surgeons are women is true, and some doctors are women is false.
Step 5: The premises can be true with the conclusion false, so the conclusion does not follow.
Conclusion: Invalid, by undistributed middle.""")
add("LSQ-12", "corrupted", "flawed", P12, """Step 1: Premise 1 establishes an overlap between doctors and surgeons. Premise 2 establishes an overlap between surgeons and women.
Step 2: The middle term "surgeons" appears in both premises, which is what links them.
Step 3: Because both overlaps involve surgeons, the overlaps chain: passing through the shared middle term carries the doctor group into the women group.
Step 4: The conclusion therefore follows necessarily from the premises.
Step 5: Both premises are true as empirical statements, so the argument is also sound.
Conclusion: Valid and sound.""",
 err="chains two particular premises; two I premises never yield a valid syllogism (undistributed middle)")

P5 = "Train A leaves at 8:00AM at 60mph. Train B leaves at 9:30AM at 90mph. Distance 270 miles. When do they meet? How far from City A?"
add("TRQ-05", "clean-cosmetic", "sound", P5, """Step 1: A runs alone from 8:00 to 9:30, that is 1.5, so it covers 90.
Step 2: Gap left is 270 - 90 = 180.
Step 3: They approach at 60 + 90 = 150.
Step 4: 180 / 150 = 1.2
Step 5: 1.2 after 9:30 is 10:42. A has run 90 + 60(1.2) = 162 by then.
Conclusion: 10:42, 162 from A.""",
 note="COSMETIC ONLY: units omitted throughout, no AM/PM, bare decimals. Arithmetic and answer are correct. This is the item the severity>=3 rule must NOT flag.")
add("TRQ-05", "corrupted", "flawed", P5, """Step 1: Train A travels at 60 mph and Train B at 90 mph, so they close the gap at 60 + 90 = 150 mph.
Step 2: The distance between the cities is 270 miles.
Step 3: Time to close the gap is 270 / 150 = 1.8 hours, which is 1 hour 48 minutes.
Step 4: Measuring from Train B's departure at 9:30 AM, they meet at 11:18 AM.
Step 5: Train A has then been travelling 3.3 hours, covering 60 x 3.3 = 198 miles.
Conclusion: They meet at 11:18 AM, 198 miles from City A.""",
 err="ignores Train A's 90-mile head start; should use a 180-mile remaining gap")

PD = "Standard die with 1 on top and 2 facing you. Which numbers face right left away down?"
add("SRQ-05", "clean", "sound", PD, """Step 1: On a standard die, opposite faces sum to 7. The pairs are 1-6, 2-5 and 3-4.
Step 2: The top face is 1, so the bottom (down) face is 6.
Step 3: The front face is 2, so the back (away) face is 5.
Step 4: The remaining pair, 3 and 4, occupies the right and left faces.
Step 5: On a standard right-handed die with 1 up and 2 facing the viewer, 3 lies to the right and 4 to the left.
Conclusion: Right 3, left 4, away 5, down 6.""")
add("SRQ-05", "corrupted", "flawed", PD, """Step 1: On a standard die, opposite faces sum to 6. The pairs are 1-5, 2-4 and 3-6.
Step 2: The top face is 1, so the bottom face is 5.
Step 3: The front face is 2, so the back face is 4.
Step 4: That leaves 3 and 6 for the right and left faces, with 3 on the right.
Step 5: All six faces are now assigned without repetition.
Conclusion: Right 3, left 6, away 4, down 5.""",
 err="opposite faces sum to 7, not 6; every derived pairing is wrong")

out = Path("eval/candidates_b5.jsonl")
with open(out, "w") as f:
    for c in C:
        f.write(json.dumps(c) + "\n")
print(f"wrote {len(C)} candidates -> {out}")
for c in C:
    print(f"  {c['id']:8s} {c['variant']:15s} label={c['label']}")
