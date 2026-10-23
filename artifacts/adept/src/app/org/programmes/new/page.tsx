import { asyncView } from "@/lib/next-compat/async-view";
import { getTranslations } from "@/lib/next-compat/intl";

import { ApiError, PageHeader } from "@/components";
import { fetchProgrammeOptions } from "@/features/org/programmes/api";
import { ProgrammeWizard } from "@/features/org/programmes/components/ProgrammeWizard";
import { currentWorkspace } from "@/lib/auth/workspace";

/** HR onboarding for a new programme: objective → roles → people → constraints → generate. */
async function PageAsync() {
  const t = await getTranslations("org.programmes");
  const [options, workspace] = await Promise.all([fetchProgrammeOptions(), currentWorkspace()]);
  return (
    <div className="a-view">
      <PageHeader eyebrow={t("eyebrow")} title={t("newTitle")} description={t("newDesc")} />
      {options.ok ? <ProgrammeWizard options={options.data} orgId={workspace ?? undefined} /> : <ApiError message={options.message} />}
    </div>
  );
}

export default asyncView(PageAsync);
