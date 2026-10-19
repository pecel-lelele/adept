import { getTranslations } from "next-intl/server";

/** Marks every skeleton page; remove once the feature renders real data. */
export async function StubBanner({ feature, endpoint }: { feature: string; endpoint?: string }) {
  const t = await getTranslations("common.stub");
  return (
    <div className="mb-4 rounded-md border border-dashed border-amber-400 bg-amber-50 px-3 py-2 font-mono text-xs text-amber-900">
      {endpoint ? t("banner", { feature, endpoint }) : t("static", { feature })}
    </div>
  );
}
