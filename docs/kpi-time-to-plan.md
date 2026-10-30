# Offline planning KPI protocol

Status: protocol and calculator only; no human trials or achieved reduction yet.
The calculator does not import Adept, connect to a database or call a model.

1. Use the five synthetic cases in `docs/demo-cvs/` and three anonymous testers T1-T3.
   Each tester completes both workflows for every case: 15 matched pairs, 30 trials.
2. Freeze the revision, catalogue, snapshot, target roles and complete intake settings.
   Record these in an anonymous session note. Use the same constraints in both workflows.
3. Counterbalance order: alternate manual-first and Adept-first across cases/testers.
   Use the same instructions and time limit. Separate practice from measured trials.
4. Start the stopwatch at intake start. Stop when the tester saves a sourced, actionable
   target-role plan (manual: save the equivalent written plan). Include normal thinking,
   loading and correction time; record failures and timeouts rather than dropping them.
5. An independent reviewer marks validity: catalogue IDs resolve, prerequisite ordering is
   respected, source/snapshot metadata is present, time/cost constraints and uncovered gaps
   are disclosed. The script accepts that review; it does not validate plans itself.
6. Generate an empty template with `python src/scripts/kpi_time_to_plan.py --template`.
   Save stdout as a local JSON file, fill durations/status/review results, then run
   `python src/scripts/kpi_time_to_plan.py path/to/trials.json`. Keep participant identities,
   private notes and real CVs out of the file and repository.

Output reports attempts, failures, valid-plan share and median valid-plan minutes per workflow.
Reduction is `100 * (paired manual median - paired Adept median) / paired manual median`,
using only matched cases valid in both workflows. Negative reduction means slower.
Absent baselines produce null. Missing/unrun/failed cases are visible; a fast successful
subset cannot establish the target for the entire study. Inspect validity and failures
alongside time and disclose all exclusions. Fifteen pairs are descriptive pilot evidence,
not an independent estimate of population impact; three testers are not fifteen people.

Do not use `users.created_at` as intake start or the mutable `pathway_plans.saved_at` as first
plan completion. Account age, returning users and overwritten plans confound that proxy.
Collect stopwatch trials first; no production SQL, migration or telemetry change is needed.

Test with `python -m unittest discover -s tests/scripts -v` (standard library only).
