#!/usr/bin/env python3
"""Batch 3: verification-checking probe.
Each question appears twice with the SAME injected error. The only difference is
the final step: 'asserted' claims success without showing work; 'shown' displays
a computation. Hypothesis: Mistral misses asserted, catches shown."""
import json
from pathlib import Path
C = []

# ---- MPQ-03: induction. Injected error: algebra slip in the inductive step.
_mpq3 = """Step 1: Base case n=1: the left side is 1, and n(n+1)/2 = 1(2)/2 = 1. The base case holds.
Step 2: Inductive hypothesis: assume 1+2+...+k = k(k+1)/2 for some positive integer k.
Step 3: For n = k+1 the left side is k(k+1)/2 + (k+1).
Step 4: Factoring out (k+1) gives (k+1)(k+3)/2, which is the formula with n = k+1.
"""
C.append(dict(id="MPQ-03", variant="corrupted-asserted", label="flawed",
  error_type="inductive step algebra: (k+1)(k+3)/2 should be (k+1)(k+2)/2",
  verification_style="asserted",
  prompt="Prove by mathematical induction: For all positive integers n, 1+2+3+...+n = n(n+1)/2. Show the base case and inductive step explicitly.",
  candidate=_mpq3 + """Step 5: Verification: the algebra has been checked and the inductive step is confirmed correct.
Conclusion: The formula holds for all positive integers n."""))

C.append(dict(id="MPQ-03", variant="corrupted-shown", label="flawed",
  error_type="inductive step algebra: (k+1)(k+3)/2 should be (k+1)(k+2)/2",
  verification_style="shown",
  prompt="Prove by mathematical induction: For all positive integers n, 1+2+3+...+n = n(n+1)/2. Show the base case and inductive step explicitly.",
  candidate=_mpq3 + """Step 5: Verification at k=2: the left side is 1+2+3 = 6, and the derived formula gives (3)(5)/2 = 7.5. These agree, confirming the inductive step.
Conclusion: The formula holds for all positive integers n."""))

# ---- MPQ-04: mod 4 cases. Injected error: odd case reduced to 0 instead of 1.
_mpq4 = """Step 1: Every integer is either even or odd, so these two cases are exhaustive.
Step 2: Even case: n = 2k, so n^2 = 4k^2, which is 0 mod 4.
Step 3: Odd case: n = 2k+1, so n^2 = 4k^2 + 4k + 1. The first two terms are multiples of 4, so n^2 is 0 mod 4.
"""
C.append(dict(id="MPQ-04", variant="corrupted-asserted", label="flawed",
  error_type="odd case: 4k^2+4k+1 is 1 mod 4, not 0; also contradicts the stated claim",
  verification_style="asserted",
  prompt="Prove or disprove: For any integer n, n² ≡ 0 or 1 (mod 4). Use case analysis. Cover all possible cases explicitly.",
  candidate=_mpq4 + """Step 4: Verification: both cases have been checked and both reduce to 0 mod 4.
Conclusion: For any integer n, n^2 is 0 mod 4."""))

C.append(dict(id="MPQ-04", variant="corrupted-shown", label="flawed",
  error_type="odd case: 4k^2+4k+1 is 1 mod 4, not 0; also contradicts the stated claim",
  verification_style="shown",
  prompt="Prove or disprove: For any integer n, n² ≡ 0 or 1 (mod 4). Use case analysis. Cover all possible cases explicitly.",
  candidate=_mpq4 + """Step 4: Verification with n=3: 3^2 = 9, and 9 mod 4 = 0. This matches the odd case result.
Conclusion: For any integer n, n^2 is 0 mod 4."""))

# ---- SRQ-03: spider and fly. Injected error: ignores the 3m dimension entirely.
_srq3 = """Step 1: The room is 12 x 8 x 3 metres, with the spider at a bottom-left floor corner and the fly at the top-right ceiling corner.
Step 2: Unfolding the floor and the far wall into a single plane, the horizontal separation is 12 and the other leg is 8.
Step 3: The shortest surface path is therefore the straight line across that unfolding: sqrt(12^2 + 8^2).
"""
C.append(dict(id="SRQ-03", variant="corrupted-asserted", label="flawed",
  error_type="unfolding omits the 3m ceiling height; correct answer is sqrt(12^2+19^2)~22.47",
  verification_style="asserted",
  prompt="Spider at bottom-left floor corner. Fly at top-right ceiling corner. Room 12x8x3m. Shortest path along surfaces only?",
  candidate=_srq3 + """Step 4: Verification: the unfolding has been checked and this is the minimal surface path.
Conclusion: approximately 14.42 metres."""))

C.append(dict(id="SRQ-03", variant="corrupted-shown", label="flawed",
  error_type="unfolding omits the 3m ceiling height; correct answer is sqrt(12^2+19^2)~22.47",
  verification_style="shown",
  prompt="Spider at bottom-left floor corner. Fly at top-right ceiling corner. Room 12x8x3m. Shortest path along surfaces only?",
  candidate=_srq3 + """Step 4: Verification: 12^2 + 8^2 = 144 + 64 = 208, and sqrt(208) is approximately 14.42. This is shorter than any alternative route, confirming minimality.
Conclusion: approximately 14.42 metres."""))

out = Path("eval/candidates_b3.jsonl")
with open(out, "w") as f:
    for c in C:
        f.write(json.dumps(c) + "\n")
print(f"wrote {len(C)} candidates -> {out}")
for c in C:
    print(f"  {c['id']:8s} {c['verification_style']:9s} label={c['label']}")
