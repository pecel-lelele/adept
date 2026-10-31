"use client";

import { ArrowRight, FileUp, Lock, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useRef, useState, type DragEvent, type FormEvent } from "react";

import { Ring, scoreColour } from "@/components/viz/Ring";
import { EstimateLabel } from "@/components/EstimateLabel";
import type { Schemas } from "@/lib/api";
import { CV_SKILLS_KEY, clearCvHandoff, cvFile, writeCvHandoff, type CvFile } from "@/features/profile/cv-handoff";
import "./cv-preview.css";

type Preview = Schemas["GuestPreview"];
type RatedSkill = { skill_id: string; label: string; level: number | null };

/** Skills found on the landing page, picked up by the intake after sign-up. */
export { CV_SKILLS_KEY } from "@/features/profile/cv-handoff";
const MAX_BYTES = 5 * 1024 * 1024;
const DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
const TYPES = ["application/pdf", "text/plain", DOCX];
/** Some browsers leave `type` empty for .docx files; fall back to the extension. */
const EXTENSIONS = /\.(pdf|docx|txt)$/i;

/**
 * Upload → explicit self-assessment → saved outlook. Only confirmed levels reach matching
 * or the sign-up handoff. The CV is read in memory by the API and never stored.
 */
export function CvPreview() {
  const t = useTranslations("ui.landing");
  const cvText = useTranslations("ui.cvReview");
  const [file, setFile] = useState<File | null>(null);
  const [consent, setConsent] = useState(false);
  const [drag, setDrag] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Preview | null>(null);
  const [step, setStep] = useState<"upload" | "rate" | "results">("upload");
  const [skills, setSkills] = useState<RatedSkill[]>([]);
  const [truncated, setTruncated] = useState(false);
  const [processedFile, setProcessedFile] = useState<CvFile | null>(null);
  const input = useRef<HTMLInputElement>(null);
  const firstUnrated = useRef<HTMLButtonElement>(null);

  function clearHandoff() {
    try { window.localStorage.removeItem(CV_SKILLS_KEY); } catch { /* Storage disabled. */ }
    try { clearCvHandoff(window.sessionStorage); } catch { /* Storage disabled. */ }
  }

  function reset() {
    setStep("upload"); setResult(null); setFile(null); setSkills([]); setError("");
    setTruncated(false); setProcessedFile(null); clearHandoff();
  }

  function pick(next: File | undefined) {
    setError("");
    if (!next) return;
    setResult(null); setSkills([]); clearHandoff();
    if (next.size > MAX_BYTES || !(TYPES.includes(next.type) || EXTENSIONS.test(next.name))) {
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
      setSkills(data.skills.map((s) => ({ skill_id: s.skill_id, label: s.label, level: null })));
      setTruncated(data.truncated);
      setProcessedFile(cvFile(file.name, data.truncated));
      setFile(null);
      setStep("rate");
      clearHandoff();
    } catch {
      setError(t("errorGeneric"));
    } finally {
      setBusy(false);
    }
  }

  async function save(e: FormEvent) {
    e.preventDefault();
    if (!skills.length || !skills.every((s) => s.level !== null)) {
      setError(t("rateRequired"));
      firstUnrated.current?.focus();
      return;
    }
    setBusy(true); setError("");
    try {
      const response = await fetch("/api/preview", {
        method: "PUT",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ skills: skills.map(({ skill_id, level }) => ({ skill_id, level })) }),
      });
      if (!response.ok) { setError(t("outlookError")); return; }
      const data = (await response.json()) as Preview;
      setResult(data);
      setStep("results");
      if (processedFile) {
        try { writeCvHandoff(window.sessionStorage, { file: processedFile, skills: data.skills.map(({ skill_id, level }) => ({ skill_id, level })) }); }
        catch { /* Storage disabled. */ }
      }
      try {
        window.localStorage.setItem(
          CV_SKILLS_KEY,
          JSON.stringify(skills.map(({ skill_id, level }) => ({ skill_id, level }))),
        );
      } catch {
        /* storage blocked: the intake simply starts empty */
      }
    } catch {
      setError(t("outlookError"));
    } finally {
      setBusy(false);
    }
  }

  function onDragEnter(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!busy) setDrag(true);
  }

  function onDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setDrag(false);
    if (!busy) pick(e.dataTransfer.files[0]);
  }

  const trends = result?.skill_trends ?? [];
  const count = (d: string) => trends.filter((x) => x.direction === d).length;

  return (
    <section className="a-upload" id="start" aria-labelledby="start-title">
      <header className="a-upload-head">
        <span className="a-upload-step">{step === "upload" ? 1 : step === "rate" ? 2 : 3}</span>
        <strong id="start-title">{t("startHere")}</strong>
        <span className="a-muted a-small" style={{ marginLeft: "auto" }}>
          {t("free")}
        </span>
      </header>

      {step === "upload" ? (
        <form
          className="a-upload-drop"
          data-drag={drag}
          onSubmit={submit}
          onClick={(e) => {
            if (!busy && e.target instanceof HTMLElement && !e.target.closest("button, label, input")) input.current?.click();
          }}
          onDragEnter={onDragEnter}
          onDragOver={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (!busy) setDrag(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            e.stopPropagation();
            setDrag(false);
          }}
          onDrop={onDrop}
          aria-busy={busy}
        >
          <span className="a-upload-icon">
            <FileUp size={20} aria-hidden />
          </span>
          <h2>{file ? file.name : t("dropTitle")}</h2>
          <p className="a-muted a-small">{t("dropBody")}</p>
          <input ref={input} type="file" accept=".pdf,.docx,.txt,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document" hidden onChange={(e) => {
            pick(e.target.files?.[0]);
            // Clear the input so choosing the same file again still fires a change.
            e.target.value = "";
          }} />
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
      ) : step === "rate" ? (
        <form className="cv-rating a-stack" onSubmit={save} aria-busy={busy}>
          {truncated ? <p className="a-notice" role="status">{cvText("truncated")}</p> : null}
          {skills.length ? <>
            <div className="cv-rating-heading">
              <div><h2>{t("rateTitle")}</h2><p className="a-muted a-small" id="cv-level-help">{t("rateHelp")}</p></div>
              <span className="a-chip" role="status">{t("ratedCount", { rated: skills.filter((s) => s.level !== null).length, total: skills.length })}</span>
            </div>
            <div className="cv-rating-list">
              {skills.map((skill) => (
                <fieldset key={skill.skill_id} className="cv-rating-row" aria-describedby="cv-level-help">
                  <legend>{skill.label}</legend>
                  <div className="cv-rating-options">
                    {[1, 2, 3, 4, 5].map((level) => (
                      <button type="button" key={level} aria-pressed={skill.level === level} disabled={busy}
                        ref={skill === skills.find((s) => s.level === null) && level === 1 ? firstUnrated : undefined}
                        aria-label={t("rateLevel", { level })}
                        onClick={() => { setSkills((prev) => prev.map((s) => s.skill_id === skill.skill_id ? { ...s, level } : s)); setError(""); }}>
                        {level}
                      </button>
                    ))}
                  </div>
                </fieldset>
              ))}
            </div>
            {error ? <p id="cv-rating-error" className="a-notice" data-tone="error" role="alert">{error}</p> : null}
            <button type="submit" className="a-btn" disabled={busy} aria-describedby={error ? "cv-rating-error" : undefined}>
              {busy ? t("savingOutlook") : t("saveOutlook")} <ArrowRight size={16} aria-hidden />
            </button>
          </> : <>
            <p className="a-notice" role="status">{t("noneFound")}</p>
            <Link className="a-btn" href="/app/onboarding">{t("manualSkills")} <ArrowRight size={16} aria-hidden /></Link>
          </>}
          <button type="button" className="a-link cv-text-button" disabled={busy} onClick={reset}>{t("tryAgain")}</button>
        </form>
      ) : step === "results" && result ? (
        <div className="a-upload-result" aria-live="polite">
          <div className="cv-rating-heading">
            <h2>{t("outlookTitle")}</h2>
            <button type="button" className="a-link cv-text-button" onClick={() => { setStep("rate"); setError(""); clearHandoff(); }}>{t("editLevels")}</button>
          </div>
          {truncated ? <p className="a-notice" role="status">{cvText("truncated")}</p> : null}
          <div className="a-free">
            <div className="a-free-role">
              {result.top_role ? (
                <>
                  <Ring value={result.top_role.score} size={104} stroke={9} caption={t("fit")} colour={scoreColour(result.top_role.score)} />
                  <EstimateLabel scenario={result.meta.scenario} />
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
          <div className="cv-assessment">
            {(["strengths", "gaps"] as const).map((group) => {
              const items = result.skills.filter((s) => group === "strengths" ? s.level >= 3 : s.level <= 2);
              return <section key={group} className="cv-assessment-group" data-kind={group}>
                <h3>{t(group)}</h3><p className="a-muted a-small">{t(group === "strengths" ? "strengthsHelp" : "gapsHelp")}</p>
                {items.length ? <ul>{items.map((s) => <li key={s.skill_id}><span>{s.label}</span><b>{s.level}/5</b></li>)}</ul> : <p className="a-muted a-small">{t(group === "strengths" ? "noStrengths" : "noGaps")}</p>}
              </section>;
            })}
          </div>
          {result.top_role ? <div className="a-locked">
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
          </div> : (
            <Link className="a-btn" href="/app/onboarding">{t("manualSkills")} <ArrowRight size={16} aria-hidden /></Link>
          )}
          <button type="button" className="a-link cv-text-button" onClick={reset}>
            {t("tryAgain")}
          </button>
        </div>
      ) : null}
      <footer className="a-upload-foot">
        <ShieldCheck size={14} aria-hidden /> {t("safe")}{" "}
        <Link className="a-link" href="/privacy">
          {t("privacyLink")}
        </Link>
        <span style={{ display: "block" }}>{t("sampleNote")}</span>
      </footer>
    </section>
  );
}
