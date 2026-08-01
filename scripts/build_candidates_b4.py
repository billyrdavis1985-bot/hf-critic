#!/usr/bin/env python3
"""Batch 4: false-alarm probe. ALL candidates are correct (label=sound).
Each question appears in two styles to isolate presentation effects."""
import json
from pathlib import Path
C = []
def add(qid, style, prompt, cand):
    C.append(dict(id=qid, variant=f"clean-{style}", label="sound",
                  error_type=None, style=style, prompt=prompt, candidate=cand))

P3 = "Prove by mathematical induction: For all positive integers n, 1+2+3+...+n = n(n+1)/2. Show the base case and inductive step explicitly."
add("MPQ-03", "standard", P3, """Step 1: Base case n=1. The left side is 1. The formula gives 1(1+1)/2 = 1. They agree, so the base case holds.
Step 2: Inductive hypothesis. Assume 1+2+...+k = k(k+1)/2 for some positive integer k.
Step 3: Consider n = k+1. The left side is (1+2+...+k) + (k+1), which by the hypothesis equals k(k+1)/2 + (k+1).
Step 4: Factor out (k+1): (k+1)(k/2 + 1) = (k+1)(k+2)/2.
Step 5: This is exactly the formula with n replaced by k+1, so the inductive step holds.
Conclusion: By induction the formula holds for all positive integers n.""")
add("MPQ-03", "terse", P3, """Step 1: n=1: 1 = 1(2)/2. Base holds.
Step 2: Assume 1+...+k = k(k+1)/2.
Step 3: k(k+1)/2 + (k+1) = (k+1)(k+2)/2, the formula at k+1.
Conclusion: Holds for all n by induction.""")

P4 = "Prove or disprove: For any integer n, n\u00b2 \u2261 0 or 1 (mod 4). Use case analysis. Cover all possible cases explicitly."
add("MPQ-04", "standard", P4, """Step 1: Every integer is even or odd, and these cases are exhaustive.
Step 2: Even case. Write n = 2k. Then n^2 = 4k^2, so n^2 is congruent to 0 mod 4.
Step 3: Odd case. Write n = 2k+1. Then n^2 = 4k^2 + 4k + 1 = 4(k^2 + k) + 1, so n^2 is congruent to 1 mod 4.
Step 4: The two cases cover all integers and yield only 0 and 1.
Conclusion: For any integer n, n^2 is congruent to 0 or 1 mod 4. The statement is true.""")
add("MPQ-04", "informal", P4, """Step 1: Split into evens and odds, which is everything.
Step 2: An even number squared is (2k)(2k) = 4k squared, so dividing by 4 leaves nothing over.
Step 3: An odd one squared is (2k+1)(2k+1) = 4k squared + 4k + 1. The first two chunks are multiples of 4, so dividing by 4 leaves 1 over.
Step 4: Nothing else to check.
Conclusion: You always get remainder 0 or remainder 1. True.""")

P6 = "Prove that for any integer n, n\u00b3-n is always divisible by 6. You may use factoring or case analysis."
add("MPQ-06", "factoring", P6, """Step 1: Factor: n^3 - n = n(n^2 - 1) = n(n-1)(n+1) = (n-1)n(n+1).
Step 2: This is a product of three consecutive integers.
Step 3: Among any three consecutive integers at least one is even, so the product is divisible by 2.
Step 4: Among any three consecutive integers exactly one is divisible by 3, so the product is divisible by 3.
Step 5: Since 2 and 3 are coprime, a number divisible by both is divisible by 6.
Conclusion: n^3 - n is divisible by 6 for every integer n.""")
add("MPQ-06", "exhaustive-residues", P6, """Step 1: The value of n^3 - n modulo 6 depends only on n modulo 6, so it suffices to check the six residues.
Step 2: n=0: 0 - 0 = 0. n=1: 1 - 1 = 0. n=2: 8 - 2 = 6.
Step 3: n=3: 27 - 3 = 24. n=4: 64 - 4 = 60. n=5: 125 - 5 = 120.
Step 4: Every one of 0, 0, 6, 24, 60, 120 is a multiple of 6.
Step 5: Since the residues are exhaustive, the property holds for all integers.
Conclusion: n^3 - n is divisible by 6 for every integer n.""")

P2 = "No fish are mammals.\nAll whales are mammals.\nConclusion: Therefore no whales are fish.\nIs this argument valid? Is it sound?\nIdentify the logical form."
add("LSQ-02", "standard", P2, """Step 1: Let S = whales, M = mammals, P = fish. Premise 1 is No P are M. Premise 2 is All S are M. The conclusion is No S are P.
Step 2: E propositions convert simply, so Premise 1 is equivalent to No M are P.
Step 3: The argument is then No M are P, All S are M, therefore No S are P. That is EAE in the first figure, traditionally Celarent.
Step 4: Celarent is a valid form, so the conclusion follows necessarily.
Step 5: Both premises are true, and a valid argument with true premises is sound.
Conclusion: Valid (Celarent) and sound.""")
add("LSQ-02", "verbose", P2, """Step 1: Before naming the form, note what each premise asserts. "No fish are mammals" denies any overlap between the class of fish and the class of mammals. "All whales are mammals" places the whole class of whales inside the class of mammals.
Step 2: If whales lie entirely within mammals, and mammals share no member with fish, then no whale can be a fish. The conclusion follows from the class relations alone, independently of biology.
Step 3: Formally, with S = whales, M = mammals, P = fish: Premise 1 is No P are M, which by simple conversion of E propositions is No M are P. Premise 2 is All S are M. The conclusion is No S are P.
Step 4: That pattern is EAE in the first figure, known as Celarent, one of the traditionally valid moods. The middle term M is distributed in the first premise, satisfying the distribution requirement.
Step 5: Validity concerns form only. Soundness additionally requires true premises, and both premises are true, so the argument is sound as well.
Conclusion: The argument is valid, its form is Celarent, and it is sound.""")

out = Path("eval/candidates_b4.jsonl")
with open(out, "w") as f:
    for c in C:
        f.write(json.dumps(c) + "\n")
print(f"wrote {len(C)} candidates -> {out}")
for c in C:
    print(f"  {c['id']:8s} {c['style']:20s} label={c['label']}")
