import { getTranslations } from "next-intl/server";

import { ApiError, PageHeader } from "@/components";
import { fetchProgrammeOptions } from "@/features/org/programmes/api";
import { ProgrammeWizard } from "@/features/org/programmes/components/ProgrammeWizard";

/** HR onboarding for a new programme: objective → roles → people → constraints → generate. */
export default async function Page() {
  const t = await getTranslations("org.programmes");
  const options = await fetchProgrammeOptions();
  return (
    <div className="a-view">
      <PageHeader eyebrow={t("eyebrow")} title={t("newTitle")} description={t("newDesc")} />
      {options.ok ? <ProgrammeWizard options={options.data} /> : <ApiError message={options.message} />}
    </div>
  );
}
