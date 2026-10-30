import Link from "next/link";
import { getTranslations } from "next-intl/server";

import { SiteFooter, SiteHeader } from "@/components/shell/Site";

export async function PublicInfoView({ kind }: { kind: "terms" | "faq" }) {
  const t = await getTranslations("publicPages");
  const faq = await getTranslations("ui.landing");
  return <div className="a-page"><SiteHeader /><main id="a-main" className="a-wrap a-section" style={{ maxWidth: "54rem" }}>
    <h1>{t(kind)}</h1><p>{t(kind === "terms" ? "intro" : "faqIntro")}</p>
    {kind === "terms" ? <>
      <p className="a-muted a-small">{t("updated")}</p>
      {(["scope", "estimates", "data", "conduct"] as const).map((key) => <section className="a-card" key={key}>
        <h2>{t(`${key}Title`)}</h2><p>{t(key)}</p>
      </section>)}
    </> : <>
      {[1,2,3,4,5,6].map((n) => <details className="a-faq-item" key={n}><summary>{faq(`q${n}` as "q1")}</summary><p>{faq(`a${n}` as "a1")}</p></details>)}
      <h2>{t("teamTitle")}</h2>
      {[1,2,3,4,5].map((n) => <details className="a-faq-item" key={n}><summary>{faq(`tq${n}` as "tq1")}</summary><p>{faq(`ta${n}` as "ta1")}</p></details>)}
    </>}
    <p><Link href="/privacy">{t("privacy")}</Link></p>
    <p><a href="https://github.com/pecel-lelele/adept/issues" target="_blank" rel="noreferrer">{t("contact")}</a></p>
  </main><SiteFooter /></div>;
}
