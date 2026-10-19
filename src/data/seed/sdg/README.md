# SDG seed (F6, M3)

| File | Rows | Source |
|---|---|---|
| `sdg_goals.csv` | 17 goals | UN Statistics Division SDG API, written by `pipelines.sdg.run` (`retrieved_at` per row) |
| `sdg_targets.csv` | 169 targets, official wording | same |
| `role_sdg_map.csv` | every role in `taxonomy/roles.csv` | Adept mapping: target, one-line reason, `strength` (direct / enabling) |
| `skill_sdg_map.csv` | every skill in `taxonomy/skills.csv` | same |
| `org_regions.csv` | synthetic demo organisations → Malaysian state | synthetic, for the region SDG view |

Regenerate goals and targets: `PYTHONPATH=src .venv/bin/python -m pipelines.sdg.run`.

`reviewed_by` / `reviewed_at` are empty on purpose: the mappings are drafts until a human
reviewer signs them off, and the UI labels them "pending review" until then.
`tests/api/sdg` fails if any role or skill lacks a link or a link names an unknown target.
