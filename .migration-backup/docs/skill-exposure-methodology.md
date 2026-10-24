# Skill Automation-Exposure Methodology

**Document**: `docs/skill-exposure-methodology.md`  
**Feature**: F2 AI-trend signal layer (M1)  
**Referenced from**: `src/api/app/contracts/trends.py` → `SkillVelocity.automation_exposure`  
**Last updated**: 2026-10-20

---

## What `automation_exposure` represents

`automation_exposure` is an editorial coefficient in the range `[0, 1]` that
represents how susceptible a skill's associated tasks are to full automation by
currently available or near-term AI/ML systems. It is **not** a probability; it
is a relative ordinal score collapsed to a unit interval for use in the
velocity-scenario transform (see `src/pipelines/trends/score.py`).

A value of `1.0` would mean the skill's tasks are entirely substitutable by
automation today; `0.0` means the tasks are entirely non-automatable (requiring
human judgment, embodied action, or social context that no current system can
replicate). In practice all values are strictly inside `(0, 1)`.

---

## Assignment criteria

Scores are assigned by editorial judgment against four published frameworks and
one rule-of-thumb band:

| Evidence source | Role in scoring |
|---|---|
| **Frey & Osborne (2017)** – "The Future of Employment" – Oxford Martin School | Primary anchor; SOC-level susceptibility scores mapped to skills where the SOC-skill link is unambiguous. |
| **ILO Working Paper 140 (2025)** – "Generative AI and Jobs" | Distinguishes transformation (high augmentation) from replacement (high automation); used to separate *emerging_ai_native* from *at_risk_routine*. |
| **McKinsey Global Institute (2023)** – "The economic potential of generative AI" | Task-level automation potential by activity type; cross-checks Frey & Osborne for clerical tasks. |
| **ONET task descriptors** | Used to decide whether the dominant task of a skill is *routine cognitive*, *non-routine cognitive*, or *manual*, which drives the band. |

### Band rules

| Band | Score range | Assigned to |
|---|---|---|
| **High** | 0.70 – 0.90 | Routine-cognitive or clerical tasks: data entry, bookkeeping, form processing, scheduling. Automation is already mature (RPA, document AI). Capped at 0.90 because full unattended deployment at scale is still not universal. |
| **Medium-high** | 0.50 – 0.69 | Structured analytical tasks where AI assists heavily but a human sign-off is required: SQL queries, basic data visualisation, standard RPA scripting. |
| **Medium** | 0.30 – 0.49 | Tasks mixing analysis with judgment, communication, or domain context: process mapping, logistics planning, customer service. |
| **Low** | 0.10 – 0.29 | Oversight, auditing, ethical judgment, stakeholder negotiation, and creative framing: risk & compliance review, AI literacy training, responsible-AI auditing, prompt engineering strategy. Human accountability is legally or operationally required. |

### Emerging AI-native skills

For skills in the `emerging_ai_native` category the coefficient is
context-dependent: skills that *produce* AI outputs (e.g. training pipelines,
model deployment) sit in the *medium* band because they are themselves
automatable by the next generation of tools; skills that *govern* or *audit* AI
outputs (e.g. responsible AI, explainability review) sit in the *low* band
because oversight cannot be fully automated without circularity.

---

## How the coefficient is used in scoring

In `src/pipelines/trends/score.py`:

```
E = automation_exposure(s)
k = 1.5
if V(s, t) < 0:
    V_fast = V(s, t) * (1 + E * k)   # amplifies decline for high-exposure skills
else:
    V_fast = V(s, t) * (1 + (1 - E) * k)  # amplifies rise for low-exposure skills
V_fast = clamp(V_fast, -2.0, 2.0)
```

A high `automation_exposure` in the *fast* scenario causes declining skills to
fall faster and rising skills to rise less, because AI systems displace the
very skills that underpin those trends.

---

## Audit and update policy

- The coefficient for each skill is recorded in `src/data/seed/canonical_skills.csv`
  alongside the assigned `category`.
- When a skill is added or re-categorised, a new entry is appended to
  `docs/decisions.md` under `## M1` citing the evidence source and the score.
- Scores are **not** derived from a model; they are editorial. Any change
  requires a human decision entry in the decisions log.
