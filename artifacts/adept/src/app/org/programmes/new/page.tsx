import { getTranslations } from "next-intl/server";

import { ApiError, PageHeader } from "@/components";
import { fetchProgrammeOptions } from "@/features/org/programmes/api";
import { ProgrammeWizard } from "@/features/org/programmes/components/ProgrammeWizard";
import { currentWorkspace } from "@/lib/auth/workspace";

/** HR onboarding for a new programme: objective → roles → people → constraints → generate. */
export default async function Page() {
  const t = await getTranslations("org.programmes");
  const [options, workspace] = await Promise.all([fetchProgrammeOptions(), currentWorkspace()]);
  return (
    <div className="a-view">
      <PageHeader eyebrow={t("eyebrow")} title={t("newTitle")} description={t("newDesc")} />
      {options.ok ? <ProgrammeWizard options={options.data} orgId={workspace ?? undefined} /> : <ApiError message={options.message} />}
    </div>
  );
}
