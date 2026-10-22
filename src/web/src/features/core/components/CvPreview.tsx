"use client";

import { ArrowRight, FileUp, Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRef, useState, type DragEvent, type FormEvent } from "react";

import { Ring, scoreColour } from "@/components/viz/Ring";
import type { Schemas } from "@/lib/api";

type Preview = Schemas["GuestPreview"];

/** Skills found on the landing page, picked up by the intake after sign-up. */
export const CV_SKILLS_KEY = "adept.cv-skills";
const MAX_BYTES = 5 * 1024 * 1024;
const TYPES = ["application/pdf", "text/plain"];

/**
 * Landing CV preview: anyone can upload a CV and see part of the result straight away (skills
 * found, how they trend, the best-fit role). Everything else is shown blurred with a sign-up
 * prompt. The CV is read in memory by the API and never stored.
 */
export function CvPreview() {
  const t = useTranslations("ui.landing");
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Preview | null>(null);
  const input = useRef<HTMLInputElement>(null);

  function pick(next: File | undefined) {
    setError("");
    setResult(null);
    if (!next) return;
    if (next.size > MAX_BYTES || !TYPES.includes(next.type)) {
      setFile(null);
      setError(t("errorType"));
      return;
    }
    setFile(next);
  }

  async function submit(e?: FormEvent) {
    e?.preventDefault();
    if (!file) {
      input.current?.click();
      return;
    }
    if (!consent) {
      setError(t("errorConsent"));
      return;
    }
    const form = new FormData();
    form.set("file", file);
    form.set("synthetic_consent", "true");
    setBusy(true);
    setError("");
    try {
      const response = await fetch("/api/preview", { method: "POST", body: form });
      if (!response.ok) {
        setError(t("errorGeneric"));
        return;
      }
      const data = (await response.json()) as Preview;
      setResult(data);
      try {
        window.localStorage.setItem(
          CV_SKILLS_KEY,
          JSON.stringify(data.skills.map((s) => ({ skill_id: s.skill_id, level: s.level }))),
        );
      } catch {
        /* storage blocked: the intake simply starts empty */
      }
    } catch {
      setError(t("errorGeneric"));
    } finally {
      setBusy(false);
    }
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    setDrag(false);
    if (!busy) pick(e.dataTransfer.files[0]);
  }

  const trends = result?.skill_trends ?? [];
  const count = (d: string) => trends.filter((x) => x.direction === d).length;

  return (
    <section className="a-upload" id="start" aria-labelledby="start-title">
      <header className="a-upload-head">
        <span className="a-upload-step">1</span>
        <strong id="start-title">{t("startHere")}</strong>
        <span className="a-muted a-small" style={{ marginLeft: "auto" }}>
          {t("free")}
        </span>
      </header>

      {!result ? (
        <form
          className="a-upload-drop"
          data-drag={drag}
          onSubmit={submit}
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={onDrop}
          aria-busy={busy}
        >
          <span className="a-upload-icon">
            <FileUp size={20} aria-hidden />
          </span>
          <h2>{file ? file.name : t("dropTitle")}</h2>
          <p className="a-muted a-small">{t("dropBody")}</p>
          <input ref={input} type="file" accept=".pdf,.txt,application/pdf,text/plain" hidden onChange={(e) => pick(e.target.files?.[0])} />
          <label className="a-check" style={{ maxWidth: 440, textAlign: "left" }}>
            <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
            {t("consentCv")}
          </label>
          <div className="a-hero-actions" style={{ justifyContent: "center" }}>
            {file ? (
              <>
                <button type="submit" className="a-btn" disabled={busy}>
                  {busy ? t("reading") : t("choose")} <ArrowRight size={16} aria-hidden />
                </button>
                <button type="button" className="a-btn is-ghost" disabled={busy} onClick={() => input.current?.click()}>
                  {t("tryAgain")}
                </button>
              </>
            ) : (
              <button type="button" className="a-btn" onClick={() => input.current?.click()}>
                <FileUp size={16} aria-hidden /> {t("choose")}
              </button>
            )}
          </div>
          {busy ? <span className="a-loader" aria-hidden /> : null}
          {error ? (
            <p className="a-notice" data-tone="error" role="alert" style={{ margin: 0 }}>
              {error}
            </p>
          ) : null}
        </form>
      ) : (
        <div className="a-upload-result" aria-live="polite">
          <div className="a-free">
            <div className="a-free-role">
              {result.top_role ? (
                <>
                  <Ring value={result.top_role.score} size={104} stroke={9} caption={t("fit")} colour={scoreColour(result.top_role.score)} />
                  <div style={{ minWidth: 0 }}>
                    <span className="a-eyebrow">{t("bestFit")}</span>
                    <h3>{result.top_role.label}</h3>
                    <span className="a-chip">{t("found", { count: result.skills.length })}</span>
                  </div>
                </>
              ) : (
                <p className="a-muted">{t("noneFound")}</p>
              )}
            </div>
            {trends.length ? (
              <div className="a-free-trend">
                <span className="a-eyebrow">{t("trendTitle")}</span>
                <div className="a-trend-split" role="img" aria-label={`${count("rising")} ${t("rising")}, ${count("stable")} ${t("stable")}, ${count("declining")} ${t("declining")}`}>
                  {(["rising", "stable", "declining"] as const).map((d) =>
                    count(d) ? <span key={d} data-dir={d} style={{ flex: count(d) }} /> : null,
                  )}
                </div>
                <div className="a-chips">
                  {trends.slice(0, 8).map((s) => (
                    <span key={s.skill_id} className="a-chip" data-tone={s.direction === "rising" ? "up" : s.direction === "declining" ? "down" : undefined}>
                      {s.direction === "rising" ? "▲" : s.direction === "declining" ? "▼" : "•"} {s.label}
                    </span>
                  ))}
                </div>
              </div>
            ) : null}
          </div>

          <div className="a-locked">
            <div className="a-locked-content" aria-hidden="true">
              {[t("lockedRoles"), t("lockedGap"), t("lockedPlan"), t("lockedImpact")].map((label, i) => (
                <div className="a-ghost" key={label}>
                  <span className="a-eyebrow">{label}</span>
                  <span className="a-ghost-ring" />
                  <i style={{ width: `${70 - i * 8}%` }} />
                  <i style={{ width: `${48 + i * 6}%` }} />
                  <i style={{ width: `${60 - i * 5}%` }} />
                </div>
              ))}
            </div>
            <div className="a-locked-cta">
              <span className="a-upload-icon">
                <Lock size={18} aria-hidden />
              </span>
              <h3>{t("lockedTitle")}</h3>
              <p>{t("lockedBody", { count: result.other_role_count })}</p>
              <div className="a-hero-actions" style={{ justifyContent: "center" }}>
                <Link className="a-btn" href="/auth/signup?next=/app/onboarding">
                  {t("unlock")} <ArrowRight size={16} aria-hidden />
                </Link>
                <Link className="a-btn is-ghost" href="/auth/login">
                  {t("haveAccount")}
                </Link>
              </div>
            </div>
          </div>
          <button type="button" className="a-link" style={{ border: 0, background: "none", cursor: "pointer", justifySelf: "start" }} onClick={() => { setResult(null); setFile(null); }}>
            {t("tryAgain")}
          </button>
        </div>
      )}
      <footer className="a-upload-foot">
        <ShieldCheck size={14} aria-hidden /> {t("safe")}
      </footer>
    </section>
  );
}
