# Final-round status and responsibilities

Reviewed against the supplied finalist guide and templates on 30 October 2026. This is an evidence register, not a declaration that the deployed application has passed final acceptance.

## Ownership corrections

| Issue | Current owner | Evidence / remaining acceptance |
|---|---|---|
| #49 | keanullimen | Human KPI run and recorded observations; automated tests cannot replace participants. |
| #50 | keanullimen | Final tools declaration/export, team-confirmed credits, signatures and submission packaging. |
| #51 | keanullimen | Wire verified MyCOL records into runtime badges; a CSV alone does not satisfy UI acceptance. |
| #52 | LouSens | Original heatmap 6ff6087. Batch profiles and actual observation dates implemented; raw skill gaps are not scenario forecasts. |
| #53 | LouSens | Original regional aggregation d1e66fb / 8621183. Distinct-person minimum and rare-cell suppression implemented. |
| #54 | LouSens | Original daemon timeout 0ed867e. Direct bounded F2 read replaces abandoned workers. |
| #55 | Darren | Validate deployed proxy/XFF behaviour with the actual Replit boundary; local middleware tests are insufficient. |
| #56 | LouSens | Catalogue originals 4fba9cf / 01c7d5c / 0279b99. Coverage labels and three verified current occupations implemented. Malay provider-course metadata still needs verification. |
| #57 | Rayen | Workspace GET mutation replaced by origin-checked, membership-checked POST. |
| #58 | Rayen | Container verification and infrastructure draft; mixed historical authorship, not blanket attribution to Rayen. |
| #59 | Rayen | Navigation fixes integrated and synthetic browser journeys added; review all manager/member flows on deployed revision. |
| #60 | LouSens | Stable admin IDs, new-write learning foreign keys, funding RLS and atomic removal cleanup implemented. Existing orphan audit and production role privileges remain rollout checks. |
| #61 | LouSens | App/dashboard controls dispatch the published RunPod MiniLM workflow. Production configuration, authorized paid run and published-snapshot evidence remain pending. |

Assignee means acceptance owner, not proof that they caused a problem. Issue bodies contain commit-level provenance. Cross-feature integration and final verification remain with LouSens; teammates should review the relevant diff and evidence before approving.

## Beyond opened issues

- Terms/FAQ routes, progressive disclosure and EN/MS/ZH copy added; privacy wording reflects optional provider processing.
- Join codes, login return paths, role/scenario/cohort context, membership errors, manager/member routing and Adi destinations corrected.
- DOSM national labour observations are separate from role forecasts, with real observation/retrieval dates and a versioned fallback. No request-time external refresh.
- Jobs refiltered offline to the configured geographic policy; empty searches retain stored dates instead of claiming today's freshness.
- Scheduled jobs/catalogue sync writes require explicit deployment database secrets. No ambient production database was migrated or seeded during this review.
- Build revision/dirty identity and loopback-only synthetic account tools added; fairness uses the production parser/scorer and shared reference distribution.
- Final report and declaration sources aligned to the supplied Phase 2 templates. The previous preliminary report is preserved under docs/archive.

## Evidence that still needs a person or deployment

1. Human KPI measurements, actual model latency/cost, and end-to-end production refresh. Do not substitute local timings or invent participants/results.
2. Team-confirmed tool use (ElevenLabs confirmed strictly for demo-video voiceover narration, not in the application), private registration/contact details, IP declarations and signatures.
3. Final PDF export/layout review, pitch/demo recording, public sharing permissions, final deployment revision and external link checks.
4. Verified Malay-language course delivery, duration, pricing and eligibility before adding catalogue records.
5. Production DB migration approval, legacy orphan counts/constraint validation, non-BYPASSRLS application role, stable admin IDs and GitHub/RunPod secret configuration.

See [review runbook](review-runbook.md) for isolated verification and rollout steps. PR descriptions carry exact test results; an open PR is not production acceptance. No merge, deployment or paid production inference is implied by these changes.
