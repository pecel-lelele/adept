# Public impact evidence (F8)

`GET /api/v1/impact/summary` is public and read-only. It reads canonical reference rows,
the selected trend snapshot and the repository's explicitly synthetic demo profiles.
It never reads the caller's private profile and performs no model inference or writes.

- Coverage counts all catalogue roles and distinguishes target roles. Free learning courses,
  their listed hours, languages and resolved official SDG links are recounted on request.
- The verification window ends at the newest stored course verification date, independently
  of the trend snapshot. Every source keeps its own retrieval date.
- The five demo profiles run through the production ranker/pathway engine; Moderate and Fast
  use the same dated snapshot. Results describe synthetic calculations, not human outcomes.
- The fairness check swaps synthetic names and career segments through the production
  profile whitelist. It is a limited regression check, not proof of population fairness.
- No cost/budget metric or claim of a human pilot is returned. Free-share predicates use
  stored learning prices; they do not promise a free certificate or funding approval.
- Public context is stored in `src/data/seed/impact/public_evidence.json`, with short exact
  quotations, publication dates where known, publisher links and actual retrieval dates.
- `RecommendationMeta` preserves real research observation dates and fallback status. The
  page explicitly discloses October 2024 replay evidence rather than implying current research.

Pipeline: public references + synthetic profiles → validate/resolve IDs and dates → counts,
hours, mappings and ranked-role features → production methods → recount/source/no-cost/
counterfactual regressions → dated public page and `src/scripts/impact_evidence.py` report.

The report is generated from the same service as the API. Run with explicit fixture/provider
settings for local review; do not infer production verification from this static report.
