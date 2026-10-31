"use client";

import { Briefcase, FileUp, GraduationCap, Repeat, Search, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRouter, useSearchParams } from "next/navigation";
import { startTransition, useEffect, useMemo, useRef, useState, useTransition, type DragEvent } from "react";

import { errorMessage } from "@/lib/api/error-message";

import { SourceBadge } from "@/components/SourceBadge";
import { CV_SKILLS_KEY } from "@/features/core/components/CvPreview";
import type { ApiResult, Schemas } from "@/lib/api";

import { resolveSkillAction, saveIntakeAction, uploadCvAction, type IntakeInput } from "../actions";
import { canResolveSkill, createSessionResolver, filterCatalogueSkills, normaliseSkillQuery } from "../skill-search";
import { clearIntakeDraft, intakeDraftKey, readIntakeDraft, writeIntakeDraft } from "../intake-draft";

type Option = Schemas["SkillOption"];
type Picked = { skill_id: string; level: number; fromCv?: boolean };
type Segment = IntakeInput["segment"];
const STYLES = ["video", "reading", "hands-on", "classroom", "mixed"] as const;

const MAX_CV_BYTES = 5 * 1024 * 1024;
const CV_MIME_TYPES = [
  "application/pdf",
  "text/plain",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const CV_EXTENSIONS = /\.(pdf|docx|txt)$/i;

const SEGMENTS: { id: Segment; icon: typeof Briefcase }[] = [
  { id: "working", icon: Briefcase },
  { id: "graduate", icon: GraduationCap },
  { id: "switcher", icon: Repeat },
];
const TOTAL = 4;

/** Four short steps: stage → interests → time & budget → skills (CV or skill bank). */
export function IntakeWizard({
  catalogue,
  interests,
  initial,
  userId,
}: {
  catalogue: Option[];
  interests: string[];
  initial: Schemas["Profile"] | null;
  userId: string;
}) {
  const t = useTranslations("ui.intake");
  const router = useRouter();
  const draftKey = intakeDraftKey(userId);
  const returnTo = useSearchParams().get("returnTo");
  const te = useTranslations("ui.apiErrors");
  const cvText = useTranslations("ui.cvReview");
  const [step, setStep] = useState(1);
  const [segment, setSegment] = useState<Segment>(initial?.segment ?? "working");
  const [picked, setPicked] = useState<string[]>(initial?.interests ?? []);
  const [hours, setHours] = useState(initial?.hours_per_week || 6);
  const [budget, setBudget] = useState(initial?.budget_myr ?? 300);
  const [hrd, setHrd] = useState(initial?.hrd_eligible ?? false);
  const [style, setStyle] = useState<IntakeInput["learning_style"]>(initial?.learning_style ?? "mixed");
  const [skills, setSkills] = useState<Picked[]>(
    (initial?.skills ?? []).map((s) => ({ skill_id: s.skill_id, level: s.level })),
  );
  const [query, setQuery] = useState("");
  const [resolution, setResolution] = useState<{
    key: string; result: ApiResult<Schemas["SkillResolutionResponse"]>;
  } | null>(null);
  const [resolving, startResolve] = useTransition();
  const resolverRef = useRef<ReturnType<typeof createSessionResolver<ApiResult<Schemas["SkillResolutionResponse"]>>> | null>(null);
  const [error, setError] = useState("");
  const [cvBusy, startCv] = useTransition();
  const [cvStatus, setCvStatus] = useState<{ empty: boolean; truncated: boolean } | null>(null);
  const [saving, startSave] = useTransition();
  const fileRef = useRef<HTMLInputElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const stepHeadingRef = useRef<HTMLHeadingElement>(null);
  const focusStepOnChange = useRef(false);
  const [isDragging, setIsDragging] = useState(false);

  function onDragEnter(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!cvBusy) setIsDragging(true);
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!cvBusy) setIsDragging(true);
  }

  function onDragLeave(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function onDropFile(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (cvBusy) return;
    const file = e.dataTransfer.files[0];
    if (!file) return;
    onFile(file);
  }
  const [draftReady, setDraftReady] = useState(false);
  const submitted = useRef(false);

  useEffect(() => {
    if (!userId) return;
    let draft = null;
    try {
      draft = readIntakeDraft(window.sessionStorage, draftKey, new Set(catalogue.map((s) => s.id)), interests);
    } catch { /* Storage may be unavailable even before getItem. */ }
    startTransition(() => {
      if (draft) {
        setSegment(draft.segment); setPicked(draft.interests); setHours(draft.hours_per_week);
        setBudget(draft.budget_myr); setHrd(draft.hrd_eligible); setStyle(draft.learning_style);
        setSkills(draft.skills); setStep(Math.min(TOTAL, Math.max(1, draft.step)));
      }
      setDraftReady(true);
    });
  }, [catalogue, interests, draftKey, userId]);

  useEffect(() => {
    if (!focusStepOnChange.current) return;
    stepHeadingRef.current?.focus();
    focusStepOnChange.current = false;
  }, [step]);

  useEffect(() => {
    if (!draftReady || submitted.current) return;
    try {
      writeIntakeDraft(window.sessionStorage, draftKey, {
        segment, interests: picked, hours_per_week: hours, budget_myr: budget,
        hrd_eligible: hrd, learning_style: style, skills: skills.map(({ skill_id, level }) => ({ skill_id, level })), step,
      });
    } catch { /* The wizard works without session storage. */ }
  }, [draftReady, draftKey, segment, picked, hours, budget, hrd, style, skills, step]);

  /** Skills found by the CV preview on the home page, before the account existed. */
  function cvSkillsFromHome(): Picked[] {
    try {
      const raw = window.localStorage.getItem(CV_SKILLS_KEY);
      if (!raw) return [];
      const known = new Set(catalogue.map((o) => o.id));
      return (JSON.parse(raw) as { skill_id: string; level: number }[])
        .filter((s) => known.has(s.skill_id))
        .map((s) => ({ skill_id: s.skill_id, level: Math.min(5, Math.max(1, s.level || 3)), fromCv: true }));
    } catch {
      return [];
    }
  }

  function goNext() {
    if (step === TOTAL - 1 && skills.length === 0) {
      const found = cvSkillsFromHome();
      if (found.length) setSkills(found);
    }
    focusStepOnChange.current = true;
    setStep((s) => s + 1);
  }

  const labels = useMemo(() => new Map(catalogue.map((o) => [o.id, o.label])), [catalogue]);
  const results = useMemo(() => {
    const chosen = new Set(skills.map((s) => s.skill_id));
    return filterCatalogueSkills(catalogue, query, chosen);
  }, [query, catalogue, skills]);
  const resolved = resolution?.key === normaliseSkillQuery(query) ? resolution.result : null;
  const suggestions = resolved?.ok ? resolved.data.candidates.filter(
    (candidate) => labels.has(candidate.skill_id) && !skills.some((s) => s.skill_id === candidate.skill_id),
  ) : [];

  function resolveSearch() {
    const key = normaliseSkillQuery(query);
    if (!canResolveSkill(key)) return;
    resolverRef.current ??= createSessionResolver(resolveSkillAction);
    startResolve(async () => {
      const request = resolverRef.current?.(key);
      if (!request) return;
      const result = await request;
      setResolution({ key, result });
    });
  }

  function addSkill(id: string, level = 3, fromCv = false) {
    setSkills((prev) => (prev.some((s) => s.skill_id === id) ? prev : [...prev, { skill_id: id, level, fromCv }]));
    setQuery("");
    setError("");
  }

  function onFile(file: File | undefined) {
    if (!file) return;
    if (file.size > MAX_CV_BYTES || !(CV_MIME_TYPES.includes(file.type) || CV_EXTENSIONS.test(file.name))) {
      setError(t("uploadTypeError"));
      return;
    }
    const form = new FormData();
    form.set("file", file);
    setError("");
    setCvStatus(null);
    startCv(async () => {
      const result = await uploadCvAction(form);
      if (result.error) {
        setError(errorMessage(te, result.error));
        return;
      }
      setCvStatus({ empty: !result.skills?.length, truncated: result.truncated ?? false });
      for (const s of result.skills ?? []) addSkill(s.skill_id, s.level, true);
    });
  }

  function finish() {
    if (!skills.length) {
      setError(t("needSkill"));
      return;
    }
    startSave(async () => {
      const result = await saveIntakeAction({
        segment,
        interests: picked,
        hours_per_week: hours,
        budget_myr: budget,
        hrd_eligible: hrd,
        learning_style: style,
        skills: skills.map(({ skill_id, level }) => ({ skill_id, level })),
      }, returnTo ?? undefined);
      if (result?.error) setError(errorMessage(te, result.error));
      else if (result.redirectTo) {
        submitted.current = true;
        try { clearIntakeDraft(window.sessionStorage, draftKey); } catch { /* Storage disabled. */ }
        try {
          window.localStorage.removeItem(CV_SKILLS_KEY);
        } catch {
          /* ignore */
        }
        router.replace(result.redirectTo);
      }
    });
  }

  return (
    <div className="a-wizard">
      <div>
        <span className="a-eyebrow">{t("stepOf", { step, total: TOTAL })}</span>
        <h1 className="a-h1">{t("title")}</h1>
      </div>
      <div className="a-progress" aria-hidden>
        {Array.from({ length: TOTAL }, (_, i) => (
          <i key={i} data-on={i < step} />
        ))}
      </div>

      <section className="a-card a-stack">
        {step === 1 ? (
          <fieldset style={{ border: 0, margin: 0, padding: 0 }} className="a-stack">
            <legend className="a-card-head" style={{ marginBottom: 12 }}>
              <h2 ref={stepHeadingRef} tabIndex={-1}>{t("segmentTitle")}</h2>
            </legend>
            <div className="a-choice-grid">
              {SEGMENTS.map(({ id, icon: Icon }) => (
                <label className="a-choice" key={id}>
                  <input type="radio" name="segment" checked={segment === id} onChange={() => setSegment(id)} />
                  <span className="a-choice-icon">
                    <Icon size={18} aria-hidden />
                  </span>
                  <strong>{t(id)}</strong>
                  <span>{t(`${id}Body`)}</span>
                </label>
              ))}
            </div>
          </fieldset>
        ) : null}

        {step === 2 ? (
          <fieldset style={{ border: 0, margin: 0, padding: 0 }} className="a-stack">
            <legend className="a-card-head" style={{ marginBottom: 4 }}>
              <h2 ref={stepHeadingRef} tabIndex={-1}>{t("interestsTitle")}</h2>
            </legend>
            <p className="a-muted a-small" style={{ margin: 0 }}>
              {t("interestsHint")}
            </p>
            <div className="a-pills">
              {interests.map((tag) => (
                <label className="a-pill" key={tag}>
                  <input
                    type="checkbox"
                    checked={picked.includes(tag)}
                    onChange={(e) =>
                      setPicked((prev) => (e.target.checked ? [...prev, tag] : prev.filter((p) => p !== tag)))
                    }
                  />
                  <span>{tag}</span>
                </label>
              ))}
            </div>
          </fieldset>
        ) : null}

        {step === 3 ? (
          <div className="a-stack">
            <div className="a-card-head" style={{ marginBottom: 0 }}>
              <h2 ref={stepHeadingRef} tabIndex={-1}>{t("timeTitle")}</h2>
            </div>
            <label className="a-field">
              {t("hours")}
              <span className="a-range-value">{hours} h</span>
              <input className="a-range" type="range" min={1} max={40} value={hours} onChange={(e) => setHours(Number(e.target.value))} />
            </label>
            <label className="a-field">
              {t("budget")}
              <span className="a-range-value">RM {budget}</span>
              <input className="a-range" type="range" min={0} max={3000} step={50} value={budget} onChange={(e) => setBudget(Number(e.target.value))} />
            </label>
            <fieldset className="a-field" style={{ border: 0, padding: 0, margin: 0 }}>
              <legend style={{ marginBottom: 8 }}>{t("styleTitle")}</legend>
              <div className="a-pills">
                {STYLES.map((s) => (
                  <label key={s} className="a-pill">
                    <input type="radio" name="learning_style" value={s} checked={style === s} onChange={() => setStyle(s)} />
                    <span>{t(`style.${s}`)}</span>
                  </label>
                ))}
              </div>
            </fieldset>
            <label className="a-check">
              <input type="checkbox" checked={hrd} onChange={(e) => setHrd(e.target.checked)} />
              {t("hrd")}
            </label>
          </div>
        ) : null}

        {step === 4 ? (
          <div className="a-stack">
            <div className="a-card-head" style={{ marginBottom: 0 }}>
              <h2 ref={stepHeadingRef} tabIndex={-1}>{t("skillsTitle")}</h2>
              <span className="a-chip">{t("chosen", { count: skills.length })}</span>
            </div>
            <p className="a-muted a-small" style={{ margin: 0 }}>
              {t("skillsHint")}
            </p>
            <div
              style={{ display: "contents" }}
              onDragEnter={onDragEnter}
              onDragOver={onDragOver}
              onDragLeave={onDragLeave}
              onDrop={onDropFile}
            >
              <button type="button" className="a-drop" data-drag={isDragging} onClick={() => fileRef.current?.click()} disabled={cvBusy}>
                <FileUp size={22} aria-hidden />
                {cvBusy ? t("uploading") : t("upload")}
              </button>
              <input
                ref={fileRef}
                type="file"
                accept=".pdf,.docx,.txt,application/pdf,text/plain,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                hidden
                onChange={(e) => {
                  onFile(e.target.files?.[0]);
                  // Clear the input so re-uploading the same file still fires a change.
                  e.target.value = "";
                }}
              />
            </div>
            {cvStatus && (cvStatus.empty || cvStatus.truncated) ? (
              <div className="a-notice" role="status">
                {cvStatus.empty ? <p>{cvText("none")}</p> : null}
                {cvStatus.truncated ? <p>{cvText("truncated")}</p> : null}
              </div>
            ) : null}
            <label className="a-field" style={{ position: "relative" }}>
              <span className="a-sr">{t("search")}</span>
              <Search size={16} aria-hidden style={{ position: "absolute", left: 14, top: 15, color: "var(--a-muted)" }} />
              <input
                className="a-input"
                ref={searchRef}
                style={{ paddingLeft: 38 }}
                placeholder={t("search")}
                value={query}
                maxLength={80}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && results[0]) {
                    e.preventDefault();
                    addSkill(results[0].id);
                  }
                }}
              />
            </label>
            {query.trim() ? (
              <div className="a-results" role="listbox" aria-label={t("search")}>
                {results.length ? (
                  results.map((o) => (
                    <button type="button" role="option" aria-selected={false} key={o.id} onClick={() => addSkill(o.id)}>
                      {o.label}
                      <small>{o.group}</small>
                    </button>
                  ))
                ) : (
                  <p className="a-muted a-small" style={{ padding: 10, margin: 0 }}>
                    {t("noResults")}
                  </p>
                )}
              </div>
            ) : null}
            {canResolveSkill(query) ? (
              <button type="button" className="a-btn is-ghost" disabled={resolving} onClick={resolveSearch}>
                {resolving ? t("resolving") : t("resolve")}
              </button>
            ) : null}
            {resolved ? (
              <div className="a-stack">
                {resolved.ok ? (
                  <>
                    <p className="a-small a-muted" role="status">{t("suggestionHint")}</p>
                    {suggestions.length ? suggestions.map((candidate) => (
                      <button type="button" className="a-btn is-ghost" key={candidate.skill_id}
                        onClick={() => addSkill(candidate.skill_id)}>
                        {t("addSuggestion", { label: candidate.label })} · {t(`resolverMethod.${candidate.method}`)}
                      </button>
                    )) : <p className="a-small a-muted" role="status">{t("noSuggestions")}</p>}
                    <SourceBadge sources={resolved.data.meta.sources} snapshotDate={resolved.data.meta.snapshot_date} />
                  </>
                ) : <p className="a-notice" role="alert">{errorMessage(te, resolved.code)}</p>}
              </div>
            ) : null}
            {skills.length ? (
              <div className="a-skillpick">
                <span className="a-small a-muted">
                  {t("level")} · {t("levels")}
                </span>
                {skills.map((s) => (
                  <div className="a-skillrow" key={s.skill_id}>
                    <strong title={labels.get(s.skill_id)}>
                      {labels.get(s.skill_id) ?? s.skill_id}
                      {s.fromCv ? <span className="a-chip" style={{ marginLeft: 8 }}>{t("fromCv")}</span> : null}
                    </strong>
                    <span className="a-levels" role="group" aria-label={t("level")}>
                      {[1, 2, 3, 4, 5].map((n) => (
                        <button
                          type="button"
                          key={n}
                          aria-pressed={s.level === n}
                          onClick={() =>
                            setSkills((prev) => prev.map((p) => (p.skill_id === s.skill_id ? { ...p, level: n } : p)))
                          }
                        >
                          {n}
                        </button>
                      ))}
                    </span>
                    <button
                      type="button"
                      className="a-iconbtn"
                      aria-label={t("remove", { skill: labels.get(s.skill_id) ?? s.skill_id })}
                      onClick={() => setSkills((prev) => prev.filter((p) => p.skill_id !== s.skill_id))}
                    >
                      <X size={16} aria-hidden />
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {error ? (
          <p className="a-notice" data-tone="error" role="alert">
            {error}
          </p>
        ) : null}
      </section>

      <div className="a-wizard-nav">
        <button type="button" className="a-btn is-ghost" disabled={step === 1 || saving} onClick={() => { focusStepOnChange.current = true; setStep((s) => s - 1); }}>
          {t("back")}
        </button>
        {step < TOTAL ? (
          <button type="button" className="a-btn" onClick={goNext}>
            {t("next")}
          </button>
        ) : (
          <button type="button" className="a-btn" disabled={saving || cvBusy} aria-busy={saving} onClick={finish}>
            {saving ? t("saving") : t("finish")}
          </button>
        )}
      </div>
    </div>
  );
}
