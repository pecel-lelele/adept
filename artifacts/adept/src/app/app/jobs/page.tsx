import { JobBoardView } from "@/features/jobs";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

const MODES = ["onsite", "hybrid", "remote"] as const;

export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const { scenario, role, q, mode, page } = await searchParams;
  const m = firstParam(mode);
  return (
    <JobBoardView
      scenario={parseScenario(scenario)}
      roleId={firstParam(role) || undefined}
      q={firstParam(q) || undefined}
      workMode={MODES.find((x) => x === m)}
      page={Math.min(100, Math.max(1, Number(firstParam(page)) || 1))}
    />
  );
}
