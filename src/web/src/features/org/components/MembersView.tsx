import { getTranslations } from "next-intl/server";

import { ApiError, Badge, Card, CardContent, PageHeader, StubBanner } from "@/components";

import { fetchMembers } from "../api";

export async function MembersView() {
  const t = await getTranslations("org");
  const result = await fetchMembers();
  return (
    <section>
      <StubBanner feature="F7 Organisation mode" endpoint="GET /api/v1/org/members" />
      <PageHeader title={t("membersTitle")} />
      {!result.ok ? (
        <ApiError message={result.message} />
      ) : (
        <Card>
          <CardContent className="divide-y pt-2 text-sm">
            {result.data.members.map((m) => (
              <div key={m.id} className="flex items-center justify-between py-2">
                <span>
                  {m.display_name}
                  <span className="ml-2 text-xs text-muted-foreground">{m.current_role_id ?? ""}</span>
                </span>
                <Badge variant={m.intake_status === "complete" ? "success" : "outline"}>
                  {t(`intake.${m.intake_status}`)}
                </Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </section>
  );
}
