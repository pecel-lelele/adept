import { getTranslations } from "next-intl/server";

import { ErrorState } from "@/components/ErrorState";

import { fetchMyOrg } from "../api";
import { OrgSettingsForm } from "./OrgSettingsForm";
import { JoinCodeCard } from "./JoinCodeCard";

/** Organisation settings: name, type, industry, size, and the join code. */
export async function OrgSetupView() {
  const t = await getTranslations("ui.org");
  const org = await fetchMyOrg();
  if (!org.ok) return <ErrorState failure={org} />;
  return (
    <div className="a-stack" style={{ maxWidth: 760 }}>
      <h1 className="a-h1">{t("settingsTitle")}</h1>
      {org.data.join_code ? (
        <section className="a-card">
          <JoinCodeCard code={org.data.join_code} />
        </section>
      ) : null}
      <OrgSettingsForm org={org.data} />
    </div>
  );
}
