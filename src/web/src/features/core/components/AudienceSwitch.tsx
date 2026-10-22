"use client";

import { useTranslations } from "next-intl";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

export type Audience = "me" | "team";

const AudienceContext = createContext<{ audience: Audience; set: (a: Audience) => void }>({
  audience: "me",
  set: () => undefined,
});

/**
 * Wraps the landing. The audience re-themes the whole page (light for individuals, dark for
 * teams) like a theme toggle and swaps the content; both views are server-rendered, so the
 * flip is instant. The choice is mirrored in the URL (?for=teams) so it can be shared.
 */
export function AudienceRoot({ initial, children }: { initial: Audience; children: ReactNode }) {
  const [audience, setAudience] = useState<Audience>(initial);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (audience === "team") url.searchParams.set("for", "teams");
    else url.searchParams.delete("for");
    window.history.replaceState(null, "", url.pathname + url.search + url.hash);
  }, [audience]);

  return (
    <AudienceContext.Provider value={{ audience, set: setAudience }}>
      <main
        className="a-page a-audience"
        data-audience={audience}
        data-mode={audience === "team" ? "organisation" : "individual"}
      >
        {children}
      </main>
    </AudienceContext.Provider>
  );
}

/** "For me ⇄ For my team" pill switch; the labels are buttons too. */
export function AudienceToggle() {
  const t = useTranslations("ui.landing");
  const { audience, set } = useContext(AudienceContext);
  const team = audience === "team";
  return (
    <div className="a-switch-row" role="group" aria-label={t("switchLabel")}>
      <button type="button" className="a-switch-label" aria-pressed={!team} onClick={() => set("me")}>
        {t("forMe")}
      </button>
      <button
        type="button"
        role="switch"
        aria-checked={team}
        aria-label={t("forTeam")}
        className="a-switch"
        onClick={() => set(team ? "me" : "team")}
      >
        <span className="a-switch-knob" />
      </button>
      <button type="button" className="a-switch-label" aria-pressed={team} onClick={() => set("team")}>
        {t("forTeam")}
      </button>
    </div>
  );
}
