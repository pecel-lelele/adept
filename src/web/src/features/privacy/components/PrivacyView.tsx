import { getTranslations } from "next-intl/server";

import { SiteFooter, SiteHeader } from "@/components/shell/Site";

import styles from "./privacy.module.css";

const sections = ["controller", "purposes", "providers", "transfers", "retention", "rights"] as const;

export async function PrivacyView() {
  const t = await getTranslations("privacy");
  return (
    <div className="a-page">
      <SiteHeader />
      <main id="a-main" className={styles.notice}>
        <h1>{t("title")}</h1>
        <p>{t("intro")}</p>
        {sections.map((section) => (
          <section key={section} aria-labelledby={`privacy-${section}`}>
            <h2 id={`privacy-${section}`}>{t(`${section}.title`)}</h2>
            <p>{t(`${section}.body`)}</p>
          </section>
        ))}
        <a href="https://www.pdp.gov.my/ppdpv1/en/data-subject-rights/">
          {t("rights.reference")}
        </a>
      </main>
      <SiteFooter />
    </div>
  );
}
