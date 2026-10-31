# SDG seed (F6, M3)

| File | Rows | Source |
|---|---|---|
| `sdg_goals.csv` | 17 goals | UN Statistics Division SDG API, written by `pipelines.sdg.run` (`retrieved_at` per row) |
| `sdg_targets.csv` | 169 targets, official wording | same |
| `role_sdg_map.csv` | every role in `taxonomy/roles.csv` | Adept mapping: target, one-line reason, `strength` (direct / enabling), `evidence_source` / `evidence_url` / `evidence_note` (UN indicator metadata, ILO, UNESCO) |
| `skill_sdg_map.csv` | every skill in `taxonomy/skills.csv` | same |
| `org_regions.csv` | synthetic demo organisations → Malaysian state | synthetic, for the region SDG view |

Regenerate goals and targets: `PYTHONPATH=src .venv/bin/python -m pipelines.sdg.run`.

`reviewed_by` / `reviewed_at` are empty on purpose: the mappings are drafts until a human
reviewer signs them off. The UI does not show a draft or "pending review" tag (M4-100); review status stays in the data and docs.
`tests/api/sdg` fails if any role or skill lacks a link or a link names an unknown target.

The 2026-10-30 current-occupation additions have enabling links to target 4.4. Its
[UN indicator metadata](https://unstats.un.org/sdgs/metadata/files/Metadata-04-04-01.pdf)
was reopened on that date; `provenance.json` records the evidence retrieval date separately
from the mapping release date and preserves the original date for other evidence. The links
describe a possible learning alignment, not an official endorsement or a measured SDG result.

Five official tech occupations have draft enabling links to 4.4 (digital employment skills)
and 8.2 (conditional technological upgrading). Five existing tech directions also gain 4.4
links. Git and Selenium have separate skill links to 4.4. The official
[target 8.2 page](https://sdgs.un.org/goals/goal8) was opened on 2026-10-30. These hypotheses
do not establish job growth, hiring readiness or observed productivity gains.
