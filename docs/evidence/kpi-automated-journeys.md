# Automated synthetic journey timings

Measured 2026-10-31T20:14:15.822239+00:00; base `1e1073f03d27ad4a095ecaf6e0b0d5bd63fb53af` with task changes.
Sample: 5 personas, 15 API journeys; 0 human trials.

CV -> questionnaire -> fixture confirmation -> radar -> matches -> saved pathway.
Target selection uses the first ranked stored role ID; this is an automation choice.

| Persona | Completed / attempted | Median journey seconds |
|---|---:|---:|
| imran | 3/3 | 0.085 |
| sofia | 3/3 | 0.083 |
| meera | 3/3 | 0.082 |
| adrian | 3/3 | 0.085 |
| nur-hana | 3/3 | 0.084 |

Local TestClient, CSV/in-memory storage and historical fixture fallback. No browser, network transit, human review, paid model or manual baseline. First run includes cold caches; later runs share process caches. Structural checks are not independent human plan-validity review.

Step times, statuses and input hashes: [JSON](kpi-automated-journeys.json).
Human trials remain in [the unfilled template](kpi-trials-template.json).
The [calculator](kpi-human-summary.json) reports no baseline or achieved reduction.
No speed-up or human plan-validity KPI can be inferred from these measurements.

The [initial raw-ID run](kpi-automated-initial-raw-id-attempts.json) is retained:
10/15 completed; five uploads received HTTP 429 because raw fixture IDs shared
an anonymous rate bucket. The current run uses real signed fixture sessions,
with the production limiter enabled. These are separate runs, not pooled results.
