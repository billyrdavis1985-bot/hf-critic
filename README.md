# MTCA Research Program

**Mixed-Tier Corpus Analysis** — studies of how frontier AI systems reason about non-propositional, identity-regulating, therapeutically-framed content. Part of the IRMB research program at Hudson Forge Technologies LLC.

## Overview

The MTCA program studies a class of text — first-person affirmations, therapeutic intentions, spiritual assertions, behavioral commitments — that resists standard empirical evaluation yet increasingly appears as both training data and live input in AI systems. The program's instrument is a multi-model council: several frontier models, each in a fresh context, producing independent structured assessments that are then synthesized across responses.

Each study in the line is self-contained (its own artifacts, findings, and reproducibility anchors) while sharing the council methodology and infrastructure.

## Studies

| Study | Focus | Status |
|-------|-------|--------|
| MTCA-1 | Content-class analysis across 5 public-domain texts / 4 lineages | Complete; writeup in progress |
| MTCA-2 | Validated instrument applied to a contemporary consented specimen (Soul Sovereignty Principles™ v1) | **Data collection complete (571/571 calls); findings draft pending author framing review** |

**MTCA-2 headline result:** applying MTCA-1's instrument unchanged to a new specimen, the framework places in the **same frame-driven regime** as MTCA-1's texts — inter-model similarity 0.1717 vs MTCA-1's 0.172 (a near-exact replication), mean frame stability 0.2489 vs 0.2345. Three independent analysis layers (quantitative, council-qualitative, reflexive) triangulate on one account: framing produces real surface variation over a stable reasoning core, and the models recognize this when shown their own work. See [`mtca-2/README.md`](mtca-2/README.md) and [`mtca-2/writeup/findings.md`](mtca-2/writeup/findings.md).

## Repository layout

```text
mtca-research/
├── README.md                     # this file — program overview
├── LICENSE                       # Apache 2.0
├── .gitattributes                # forces binary handling for artifacts (hash stability)
├── .github/workflows/
│   └── verify-integrity.yml      # CI: verifies both study manifests + MTCA-2 sidecars on every push
│
├── mtca-1/
│   ├── README.md                 # MTCA-1 study specifics
│   ├── MANIFEST.sha256           # authoritative byte-level integrity anchors
│   ├── ARTIFACT_HASHES.json      # provenance-ID ↔ integrity-hash crosswalk
│   ├── notebooks/                # Stage 1–8 notebooks
│   ├── stage1/                   # foundational document (research question, nulls, ethics)
│   ├── corpus/                   # 5 source texts (raw) + frozen corpus v1.0/v1.1
│   ├── stage3_design/            # frame design + execution plan
│   ├── stage6_execution/         # full council dataset (2000 responses + index)
│   ├── stage7_synthesis/         # quantitative findings
│   ├── stage8_council/           # qualitative judge assessments
│   └── manifests/                # per-stage summary manifests
│
└── mtca-2/
    ├── README.md                 # MTCA-2 study specifics
    ├── MANIFEST.sha256           # 18 hash-anchored foundation artifacts (CI-verified)
    ├── consent/                  # consent record (author: Marina Tudor) + sidecar
    ├── prereg/
    │   ├── mtca2_prereg.md        # pre-registration (9 hypotheses, nulls, analysis plan)
    │   └── AMENDMENT_LOG.md        # amendment trail (2 amendments, hash-chained)
    ├── corpus/                   # SSP_v1 frozen corpus (13 principles) + extraction/verification
    ├── stage5_pilot/             # 40-call pilot (calibration validation; 40/40 clean)
    ├── stage6_execution/         # full council dataset (520 responses, 100% clean parse)
    ├── stage7_synthesis/         # quantitative frame-stability + MTCA-1 baseline comparison
    ├── stage8_council/           # council synthesis (36 judge assessments)
    ├── stage8_5_reflexive/       # Layer 3 reflexive (15 responses) + hash-locked prompt template
    └── writeup/                  # findings.md (three-layer synthesis, draft)
```

The two studies differ in how they treat the pilot: MTCA-1 excluded its Stage 5 pilot as superseded; MTCA-2 retains its pilot as a committed calibration artifact (it locked the token/decoding parameters used in the full run).

## Reproducibility

Both studies are frozen, hash-anchored, and continuously verified.

**Authoritative integrity** lives in each study's `MANIFEST.sha256`, verifiable on any platform:

```bash
cd mtca-1 && sha256sum -c MANIFEST.sha256
cd ../mtca-2 && sha256sum -c MANIFEST.sha256
```

**MTCA-1 — two-role hashing model.** Frozen-artifact *filenames* embed a **design-time provenance identifier** — a content hash computed during the freeze step that binds related artifacts into one version chain (e.g., Stage 3 design `6380e711…` links the design file, its execution plan, and every Stage 6 response generated under it). These filename identifiers are **not** byte-integrity checksums (corpus v1.0 is the lone self-verifying exception). The provenance-ID ↔ byte-hash mapping is recorded in `mtca-1/ARTIFACT_HASHES.json`. Corpus v1.1 canonical integrity hash: `e8e998c9099e0fa6dd0d3f98ae5ae49af3fc826c9a2c8c51a7eff19b4a439a53`.

**MTCA-2 — manifest + sidecars.** `mtca-2/MANIFEST.sha256` anchors the 18 foundation artifacts (corpus, pre-registration, consent, Layer 3 template, and their sidecars). The frozen corpus is `b917f798…`; the pre-registration (at Amendment 002) is `ad94f8d5…`. The 571 council responses (520 Stage 6 + 36 Stage 8 + 15 Stage 8.5) are committed in full. The Stage 7 synthesis is deterministic pure computation over the committed responses and reproduces its SHA on any machine; method fidelity to MTCA-1 (extraction, tokenization, Jaccard, null thresholds, frame prompts) was verified byte-equivalent before results were locked.

**Continuous verification.** `.github/workflows/verify-integrity.yml` runs `sha256sum -c` on **both** study manifests plus the four MTCA-2 sidecars (corpus, pre-registration, consent, Layer 3 template) on every push and pull request. A green check certifies that committed bytes match the manifests on a clean clone.

**Reproduction path:** load the frozen corpus and frame prompts → execute against the five council models using the archived design/pre-registration → verify response bytes against `MANIFEST.sha256`. Any divergence indicates either model drift (updated model versions or SDKs) or a reproduction error — both informative. MTCA-2's Amendment 002 documents the SDK-driven token/decoding calibrations required to reproduce MTCA-1's completion behavior on current model SDKs.

## Methodology principles

- **Frozen artifacts at every stage**, hash-anchored and archived.
- **Pre-registered nulls** — failure conditions defined before execution; null results are valid findings.
- **Language discipline** — all claims framed as model behavior under specified methodology, never as properties of the source texts.
- **Consent for non-public-domain specimens** — MTCA-2's specimen is used under an explicit consent agreement that binds the model-behavior language discipline and reserves author framing review before public release.
- **AI-augmented research disclosure** — where AI assists analysis, synthesis, or drafting, roles are documented and the researcher adjudicates.
- **Reflexivity tracking** — researcher decisions and corrections logged alongside artifacts (see MTCA-2's amendment log).

## Program lineage

- **HF-IQR (V1–V3)** established and refined the multi-model council methodology for AI critique-behavior analysis; V3 characterized position-defense and calibration patterns across five frontier models, including a ceiling-effect null on the primary endpoint. MTCA-2's reflexive layer (Stage 8.5) is a direct carryover of the HF-IQR V3 reflexive technique.
- **QPU Drift Collector** established the reproducibility conventions used across IRMB studies — frozen designs, SHA256 anchoring, open release under Apache 2.0.
- **MTCA-1** applied the council methodology to a new content class with a frame-sensitivity experimental design.
- **MTCA-2** validated that instrument by specimen-swap replication on a contemporary consented framework.

## Citation

Davis, B. (2026). *MTCA Research Program: Multi-model AI reasoning studies on non-propositional content classes.* Hudson Forge Technologies LLC. https://github.com/billyrdavis1985-bot/mtca-research

Individual studies carry their own citations in their directories.

## License

Apache 2.0. See `LICENSE`.

---

> *Experiment. Measure. Refine. Repeat.*
> — Hudson Forge Technologies · IRMB Research Program
