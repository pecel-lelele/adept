# Automated synthetic journey timings

Measured 2026-10-30T06:39:12.709799+00:00; base `cb8bbf0f697e6b937aa46389ab0c18d545a15e96` with task changes.
Sample: 5 personas, 15 API journeys; 0 human trials.

CV -> questionnaire -> fixture confirmation -> radar -> matches -> saved pathway.
Target selection uses the first ranked stored role ID; this is an automation choice.

| Persona | Completed / attempted | Median journey seconds |
|---|---:|---:|
| imran | 3/3 | 0.151 |
| sofia | 3/3 | 0.093 |
| meera | 3/3 | 0.091 |
| adrian | 3/3 | 0.236 |
| nur-hana | 3/3 | 0.127 |

Local TestClient, CSV/in-memory storage and historical fixture fallback. No browser, network transit, human review, paid model or manual baseline. First run includes cold caches; later runs share process caches. Structural checks are not independent human plan-validity review.

Step times, statuses and input hashes: [JSON](kpi-automated-journeys.json).
Human trials remain in [the unfilled template](kpi-trials-template.json).
The [calculator](kpi-human-summary.json) reports no baseline or achieved reduction.
No speed-up or human plan-validity KPI can be inferred from these measurements.

The [initial raw-ID run](kpi-automated-initial-raw-id-attempts.json) is retained:
10/15 completed; five uploads received HTTP 429 because raw fixture IDs shared
an anonymous rate bucket. The current run uses real signed fixture sessions,
with the production limiter enabled. These are separate runs, not pooled results.
