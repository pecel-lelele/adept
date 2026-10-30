import { fetchJobsSummary } from "@/features/jobs";
import { fetchMatches } from "@/features/matching/api";
import { fetchSkillCatalogue } from "@/features/profile/api";
import type { ScenarioId } from "@/lib/api";

/**
 * Catalogue labels for the role and skill ids that SDG links come "via". Labels come only from
 * API catalogue responses (skill bank, role openings, the person's own matches); an id with no
 * catalogue label is shown as the id rather than an invented name.
 */
export async function entityLabels(scenario: ScenarioId, includeMatches: boolean): Promise<Map<string, string>> {
  const [skills, jobs, matches] = await Promise.all([
    fetchSkillCatalogue(),
    fetchJobsSummary(scenario),
    includeMatches ? fetchMatches(scenario) : Promise.resolve(null),
  ]);
  const labels = new Map<string, string>();
  if (skills.ok) for (const s of skills.data.skills) labels.set(`skill:${s.id}`, s.label);
  if (jobs.ok) for (const r of jobs.data.roles) labels.set(`role:${r.role_id}`, r.role_label);
  if (matches?.ok) for (const m of matches.data.matches) labels.set(`role:${m.role_id}`, m.label);
  return labels;
}
