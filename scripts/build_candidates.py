#!/usr/bin/env python3
"""Smoke-test candidate set for the other-critique pilot.
Paired variants: same question, clean vs corrupted. Labels known by construction."""
import json
from pathlib import Path

C = []

C.append(dict(id="MPQ-16", variant="clean", label="sound", error_type=None,
  prompt="Prove or disprove: The product of any two even integers is always divisible by 4. Show your proof in numbered steps.",
  candidate="""Step 1: Let m and n be any two even integers.
Step 2: By definition of even, m = 2a and n = 2b for some integers a and b.
Step 3: Their product is mn = (2a)(2b) = 4ab.
Step 4: Since a and b are integers, ab is an integer.
Step 5: Therefore mn = 4 times an integer, which is divisible by 4.
Conclusion: The statement is true, by direct proof."""))

C.append(dict(id="MPQ-16", variant="corrupted", label="flawed",
  error_type="right answer via wrong route (proof by example, misuse of induction)",
  prompt="Prove or disprove: The product of any two even integers is always divisible by 4. Show your proof in numbered steps.",
  candidate="""Step 1: Test some cases: 2 x 2 = 4, which is divisible by 4.
Step 2: Test more: 2 x 4 = 8, divisible by 4. And 4 x 6 = 24, divisible by 4.
Step 3: All three cases hold, so by induction the pattern continues for every pair of even integers.
Step 4: No counterexample appeared in testing.
Conclusion: The statement is true."""))

C.append(dict(id="LSQ-01", variant="clean", label="sound", error_type=None,
  prompt="All squares are rectangles.\nAll rectangles have four sides.\nConclusion: Therefore all squares have four sides.\nIs this argument valid? Is it sound?\nWhat is the logical form and does the conclusion\nfollow necessarily from the premises?",
  candidate="""Step 1: Premise 1 has the form: All S are M (all squares are rectangles).
Step 2: Premise 2 has the form: All M are P (all rectangles have four sides).
Step 3: The conclusion is: All S are P. This is Barbara, AAA-1.
Step 4: The middle term M is distributed as the subject of Premise 2, satisfying the distribution requirement, so the form is valid.
Step 5: Both premises are true in standard Euclidean geometry.
Step 6: A valid argument with true premises is sound.
Conclusion: The argument is valid and sound."""))

C.append(dict(id="LSQ-01", variant="corrupted", label="flawed",
  error_type="misapplied distribution rule -> false invalidity claim (wrong conclusion)",
  prompt="All squares are rectangles.\nAll rectangles have four sides.\nConclusion: Therefore all squares have four sides.\nIs this argument valid? Is it sound?\nWhat is the logical form and does the conclusion\nfollow necessarily from the premises?",
  candidate="""Step 1: The middle term is "rectangles".
Step 2: In Premise 1, "rectangles" is the predicate of a universal affirmative, so it is undistributed.
Step 3: A valid syllogism requires the middle term to be distributed, and here it is not.
Step 4: This is the fallacy of the undistributed middle.
Step 5: Since the argument is invalid, it cannot be sound.
Conclusion: The argument is invalid and therefore unsound."""))

C.append(dict(id="SRQ-01", variant="clean", label="sound", error_type=None,
  prompt="A 3x3x3 cube is painted and cut into 27 pieces. How many have 3 painted faces? 2 faces? 1 face? 0 faces? Verify sum to 27.",
  candidate="""Step 1: Corner cubies have 3 painted faces. A cube has 8 corners, so 8 cubies.
Step 2: Edge cubies (non-corner) have 2 painted faces. Each of the 12 edges holds 3 - 2 = 1 non-corner cubie, so 12 cubies.
Step 3: Face-centre cubies have 1 painted face. Each of the 6 faces has exactly 1 centre, so 6 cubies.
Step 4: The single cubie at the centre of the solid touches no surface, so 1 cubie with 0 painted faces.
Step 5: Verify: 8 + 12 + 6 + 1 = 27, matching the total.
Conclusion: 8 with 3 faces, 12 with 2, 6 with 1, 1 with 0."""))

C.append(dict(id="SRQ-01", variant="corrupted", label="flawed",
  error_type="miscounted edges + false verification (asserted sum never checked)",
  prompt="A 3x3x3 cube is painted and cut into 27 pieces. How many have 3 painted faces? 2 faces? 1 face? 0 faces? Verify sum to 27.",
  candidate="""Step 1: Corner cubies have 3 painted faces: 8 corners, so 8 cubies.
Step 2: Edge cubies have 2 painted faces. A cube has 8 edges, so 8 cubies.
Step 3: Face-centre cubies have 1 painted face: 6 faces, so 6 cubies.
Step 4: The interior cubie has 0 painted faces: 1 cubie.
Step 5: Verify: the four counts sum to 27 as required.
Conclusion: 8 with 3 faces, 8 with 2, 6 with 1, 1 with 0."""))

out = Path("eval/candidates_pilot.jsonl")
out.parent.mkdir(exist_ok=True)
with open(out, "w") as f:
    for c in C:
        f.write(json.dumps(c) + "\n")
print(f"wrote {len(C)} candidates -> {out}")
for c in C:
    print(f"  {c['id']:8s} {c['variant']:10s} label={c['label']:8s} {c['error_type'] or ''}")
