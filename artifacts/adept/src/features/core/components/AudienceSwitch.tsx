"use client";

import { Building2, UserRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { flushSync } from "react-dom";

export type Audience = "me" | "team";

const AudienceContext = createContext<{ audience: Audience; set: (a: Audience) => void }>({
  audience: "me",
  set: () => undefined,
});

type ViewTransitionDoc = Document & {
  startViewTransition?: (update: () => void) => { ready: Promise<void> };
};

/**
 * Wraps the landing. The audience swaps the whole page: white and personal for individuals,
 * sage with deep forest-green blocks for organisations. Switching lands on the other view's
 * hero, which wipes down like a curtain (View Transitions, where supported).
 * The choice is mirrored in the URL (?for=teams) so it can be shared.
 */
export function AudienceRoot({ initial, children }: { initial: Audience; children: ReactNode }) {
  const [audience, setAudience] = useState<Audience>(initial);

  useEffect(() => {
    const url = new URL(window.location.href);
    if (audience === "team") url.searchParams.set("for", "teams");
    else url.searchParams.delete("for");
    window.history.replaceState(null, "", url.pathname + url.search);
  }, [audience]);

  const set = (next: Audience) => {
    if (next === audience) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const doc = document as ViewTransitionDoc;
    // Land on the other audience's hero, wherever the visitor was on this page.
    const swap = () => {
      flushSync(() => setAudience(next));
      window.scrollTo({ top: 0, behavior: "instant" as ScrollBehavior });
    };
    if (reduced || !doc.startViewTransition) {
      swap();
      return;
    }
    doc
      .startViewTransition(swap)
      .ready.then(() => {
        document.documentElement.animate(
          { clipPath: ["inset(0 0 100% 0)", "inset(0 0 0% 0)"] },
          { duration: 650, easing: "cubic-bezier(.65,0,.35,1)", pseudoElement: "::view-transition-new(root)" },
        );
      })
      .catch(() => undefined);
  };

  return (
    <AudienceContext.Provider value={{ audience, set }}>
      <div
        className="a-page a-audience"
        data-audience={audience}
        data-mode={audience === "team" ? "organisation" : "individual"}
      >
        {children}
      </div>
    </AudienceContext.Provider>
  );
}

/**
 * "Individual | Organisation" segmented control (partner design): two icon buttons; the chosen
 * one fills in. Labels show on wide screens; phones keep the icons.
 */
export function AudienceToggle() {
  const t = useTranslations("ui.landing");
  const { audience, set } = useContext(AudienceContext);
  const options = [
    { id: "me" as const, label: t("forMe"), Icon: UserRound },
    { id: "team" as const, label: t("forTeam"), Icon: Building2 },
  ];
  return (
    <div className="a-aud" role="radiogroup" aria-label={t("switchLabel")} data-audience={audience}>
      {options.map(({ id, label, Icon }) => (
        <button
          key={id}
          type="button"
          role="radio"
          aria-checked={audience === id}
          title={label}
          onClick={() => set(id)}
        >
          <Icon size={15} strokeWidth={1.8} aria-hidden />
          <span>{label}</span>
        </button>
      ))}
    </div>
  );
}
