"use client";

import { ArrowRight } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";

/** Capability band that scrolls slowly (pausable; still for reduced motion). */
export function Marquee({
  lead,
  strong,
  items,
}: {
  lead: string;
  strong: string;
  items: { label: string; icon: ReactNode }[];
}) {
  const t = useTranslations("ui.landing");
  const [paused, setPaused] = useState(false);
  return (
    <section className="a-marquee" aria-label={`${lead} ${strong}`}>
      <div className="a-marquee-label">
        {lead}
        <br />
        <b>{strong}</b>
      </div>
      <div className="a-marquee-window">
        <div className="a-marquee-track" data-paused={paused}>
          {[0, 1].map((n) => (
            <div className="a-marquee-set" key={n} aria-hidden={n === 1}>
              {items.map(({ label, icon }) => (
                <span key={label}>
                  {icon}
                  {label}
                </span>
              ))}
            </div>
          ))}
        </div>
      </div>
      <button
        type="button"
        className="a-marquee-pause"
        onClick={() => setPaused(!paused)}
        aria-label={paused ? t("play") : t("pause")}
        aria-pressed={paused}
      >
        {paused ? "▶" : "Ⅱ"}
      </button>
    </section>
  );
}

export type StepItem = { title: string; label: string; detail: string; art?: ReactNode; data?: ReactNode };

const STEP_MS = 5500;
const RESUME_MS = 6000;

/**
 * Vertical stepper (partner design): pick a step on the left, read it on the right. It plays
 * through on its own while on screen; picking a step holds it a little longer, then it
 * carries on. Each panel pairs a line-art object with live data from the API.
 */
export function Stepper({ steps }: { steps: StepItem[] }) {
  const t = useTranslations("ui.landing");
  const [active, setActive] = useState(0);
  const [pausedAt, setPausedAt] = useState(0);
  const [visible, setVisible] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const playing = visible;

  useEffect(() => {
    const el = root.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    const io = new IntersectionObserver(([entry]) => setVisible(Boolean(entry?.isIntersecting)), { threshold: 0.35 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  useEffect(() => {
    if (!playing || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    // After the visitor picks a step, give them time to read it before moving on.
    const wait = pausedAt ? STEP_MS + RESUME_MS : STEP_MS;
    const id = window.setTimeout(() => {
      setPausedAt(0);
      setActive((a) => (a + 1) % steps.length);
    }, wait);
    return () => window.clearTimeout(id);
  }, [playing, active, pausedAt, steps.length]);

  const choose = (i: number) => {
    setPausedAt((n) => n + 1);
    setActive(i);
  };
  const onKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key !== "ArrowDown" && e.key !== "ArrowUp" && e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    e.preventDefault();
    const forward = e.key === "ArrowDown" || e.key === "ArrowRight";
    const next = (active + (forward ? 1 : steps.length - 1)) % steps.length;
    choose(next);
    refs.current[next]?.focus();
  };
  if (!steps.length) return null;
  return (
    <div
      ref={root}
      className="a-stepper"
      data-playing={playing}
    >
      <div className="a-stepper-list" role="tablist" aria-orientation="vertical" aria-label={t("autoplay")}>
        {steps.map((s, i) => (
          <button
            key={s.title}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="tab"
            id={`how-tab-${s.label}`}
            aria-selected={active === i}
            aria-controls={`how-panel-${s.label}`}
            tabIndex={active === i ? 0 : -1}
            onClick={() => choose(i)}
            onKeyDown={onKey}
          >
            <span className="a-num">0{i + 1}</span>
            <span>{s.title}</span>
            <ArrowRight size={17} aria-hidden />
            {active === i ? <i className="a-stepper-progress" key={`${active}-${pausedAt}`} style={{ animationDuration: `${pausedAt ? STEP_MS + RESUME_MS : STEP_MS}ms` }} aria-hidden /> : null}
          </button>
        ))}
      </div>
      <div className="a-stepper-panels">
        {steps.map((st, i) => (
          <div
            key={st.label}
            className="a-stepper-panel"
            id={`how-panel-${st.label}`}
            role="tabpanel"
            aria-labelledby={`how-tab-${st.label}`}
            aria-hidden={active !== i}
            data-active={active === i}
            inert={active !== i}
          >
            <div className="a-stepper-copy">
              <span className="a-eyebrow">{t("stepOf", { n: i + 1, total: steps.length })}</span>
              <h3>{st.title}</h3>
              <p>{st.detail}</p>
              {st.data ? <div className="a-stepper-visual">{st.data}</div> : null}
            </div>
            {st.art ? <div className="a-stepper-art">{st.art}</div> : null}
          </div>
        ))}
      </div>
    </div>
  );
}
