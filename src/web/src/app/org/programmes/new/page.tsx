import { getTranslations } from "next-intl/server";

import { ErrorState, PageHeader } from "@/components";
import { fetchProgrammeOptions } from "@/features/org/programmes/api";
import { ProgrammeWizard } from "@/features/org/programmes/components/ProgrammeWizard";
import { currentWorkspace } from "@/lib/auth/workspace";
import { firstParam, parseScenario, type SearchParams } from "@/lib/scenario";

/** HR onboarding for a new programme: objective → roles → people → constraints → generate. */
export default async function Page({ searchParams }: { searchParams: Promise<SearchParams> }) {
  const params = await searchParams;
  const t = await getTranslations("org.programmes");
  const [options, workspace] = await Promise.all([fetchProgrammeOptions(), currentWorkspace()]);
  return (
    <div className="a-view">
      <PageHeader eyebrow={t("eyebrow")} title={t("newTitle")} description={t("newDesc")} />
      {options.ok ? <ProgrammeWizard options={options.data} orgId={workspace ?? undefined} initialRole={firstParam(params.role)} initialMember={firstParam(params.member)} initialScenario={parseScenario(params.scenario)} /> : <ErrorState failure={options} />}
    </div>
  );
}
