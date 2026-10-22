import { getTranslations } from "next-intl/server";

import { PageHeader } from "@/components";
import { ErrorState } from "@/components/ErrorState";

import { fetchMyOrg } from "../api";
import { JoinCodeCard } from "./JoinCodeCard";
import { OrgSettingsForm } from "./OrgSettingsForm";

/** Organisation settings: name, type, industry and size, beside the join code. */
export async function OrgSetupView() {
  const t = await getTranslations("ui.org");
  const tp = await getTranslations("ui.page");
  const org = await fetchMyOrg();
  if (!org.ok) return <ErrorState failure={org} />;
  return (
    <div className="a-view">
      <PageHeader eyebrow={org.data.name} title={t("settingsTitle")} description={tp("settingsDesc")} />
      <div className="a-split">
        <OrgSettingsForm org={org.data} />
        {org.data.join_code ? (
          <aside className="a-card is-sage">
            <JoinCodeCard code={org.data.join_code} />
            <p className="a-small a-muted" style={{ margin: "14px 0 0" }}>
              {t("inviteBody")}
            </p>
          </aside>
        ) : null}
      </div>
    </div>
  );
}
