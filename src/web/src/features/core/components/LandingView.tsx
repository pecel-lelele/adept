import {
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Check,
  Compass,
  Grid3x3,
  KeyRound,
  Leaf,
  Radar,
  Route,
  ScanLine,
  ShieldCheck,
  Users,
} from "lucide-react";
import Link from "next/link";
import { getTranslations } from "next-intl/server";
import type { CSSProperties, ReactNode } from "react";

import { SiteFooter, SiteHeader } from "@/components/shell/Site";
import { FeatureArt, type FeatureArtVariant } from "@/components/viz/FeatureArt";
import { OrgScene } from "@/components/viz/OrgScene";
import { PathScene } from "@/components/viz/PathScene";
import { call, getApi, type Schemas } from "@/lib/api";
import { getAccount } from "@/lib/auth/account";

import { AudienceRoot, AudienceToggle, type Audience } from "./AudienceSwitch";
import { CvPreview } from "./CvPreview";
import { LandingMotion } from "./LandingMotion";
import { Marquee, Stepper, type StepItem } from "./LandingParts";

type Overview = Schemas["PlatformOverview"];
type T = Awaited<ReturnType<typeof getTranslations<"ui.landing">>>;

const ME_FEATURES: [FeatureArtVariant, "f1" | "f2" | "f3" | "f4" | "f5" | "f6"][] = [
  ["cv", "f1"],
  ["radar", "f2"],
  ["match", "f3"],
  ["scenario", "f4"],
  ["path", "f5"],
  ["sdg", "f6"],
];
const TEAM_FEATURES: [FeatureArtVariant, "tf1" | "tf2" | "tf3" | "tf4" | "tf5" | "tf6"][] = [
  ["roster", "tf1"],
  ["matrix", "tf2"],
  ["target", "tf3"],
  ["gantt", "tf4"],
  ["coins", "tf5"],
  ["review", "tf6"],
];

/** One card per app feature, each with its own looping line-art object. */
function FeatureGrid({
  className,
  items,
}: {
  className: string;
  items: { art: FeatureArtVariant; title: string; body: string }[];
}) {
  return (
    <div className={`a-features ${className}`}>
      {items.map((f, i) => (
        <article className="a-feature" key={f.title} data-reveal style={{ "--i": i % 3 } as CSSProperties}>
          <FeatureArt variant={f.art} />
          <h3>{f.title}</h3>
          <p>{f.body}</p>
        </article>
      ))}
    </div>
  );
}

/** Bars for the fastest-moving skills, scaled to the largest move shown. */
function SkillMoves({ title, skills }: { title: string; skills: Overview["top_rising"] }) {
  const max = Math.max(...skills.map((s) => Math.abs(s.velocity)), 0.001);
  return (
    <div className="a-live-moves">
      <span className="a-eyebrow">{title}</span>
      {skills.map((s) => (
        <div className="a-live-move" key={s.skill_id} data-dir={s.direction}>
          <span>{s.label}</span>
          <div>
            <i style={{ width: `${Math.round((Math.abs(s.velocity) / max) * 100)}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="a-live-stat">
      <strong data-count={value}>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

/** Live data for each "how it works" step, from GET /meta/overview. */
function visuals(t: T, o: Overview | null, team: boolean): ReactNode[] {
  if (!o) return [];
  const live = (
    <p className="a-live-foot">
      <ShieldCheck size={13} aria-hidden />
      {t("vLive", { date: o.meta.snapshot_date, sources: o.meta.sources.map((s) => s.name).join(", ") })}
    </p>
  );
  const bank = (
    <div className="a-live">
      <div className="a-live-big">
        <strong data-count={o.skills_in_bank}>{o.skills_in_bank}</strong>
        <span>{t("vBank")}</span>
      </div>
      <p className="a-live-note">{t("vTracked", { count: o.skills_tracked })}</p>
    </div>
  );
  const radar = (
    <div className="a-live">
      <div className="a-live-split" role="img" aria-label={t("vSplit", { rising: o.rising, stable: o.stable, declining: o.declining })}>
        <span data-dir="rising" style={{ flex: o.rising }} />
        <span data-dir="stable" style={{ flex: o.stable }} />
        <span data-dir="declining" style={{ flex: o.declining }} />
      </div>
      <p className="a-live-note">{t("vSplit", { rising: o.rising, stable: o.stable, declining: o.declining })}</p>
      <SkillMoves title={t("vRising")} skills={o.top_rising} />
      {live}
    </div>
  );
  const roles = (
    <div className="a-live">
      <p className="a-live-note">{t("vRoles", { count: o.roles })}</p>
      <ul className="a-live-roles">
        {o.top_roles.map((r) => (
          <li key={r.role_id}>
            <span>{r.label}</span>
            <b>{t("vOutlook", { value: r.outlook.toFixed(2) })}</b>
            <span className="a-estimate">{t("vEstimate")}</span>
          </li>
        ))}
      </ul>
      {live}
    </div>
  );
  const plan = (
    <div className="a-live">
      <div className="a-live-stats">
        <Stat value={o.courses} label={t("vCourses")} />
        <Stat value={o.free_courses} label={t("vFree")} />
        <Stat value={o.hrd_claimable_courses} label={t("vHrd")} />
        <Stat value={o.providers} label={t("vProviders")} />
      </div>
      <p className="a-live-note">
        <Leaf size={13} aria-hidden /> {t("vGoals", { count: o.sdg_goals_linked })}
      </p>
    </div>
  );
  return team ? [null, bank, roles, plan] : [bank, radar, roles, plan];
}

/**
 * Public home, after the partner design (frontend/adept): editorial hero with a figure, a
 * capability band, the CV upload, a "how it works" stepper fed by live data, an explainer,
 * questions and a closing call to action. The "For me ⇄ For my team" switch re-themes the
 * page (light / deep green) and swaps the audience-specific parts.
 */
export async function LandingView({ audience }: { audience: Audience }) {
  const t = await getTranslations("ui.landing");
  const ta = await getTranslations("ui.auth");
  const [account, overview] = await Promise.all([
    getAccount(),
    getApi().then((api) => call(api.GET("/api/v1/meta/overview"))),
  ]);
  const home = account ? (account.kind === "org_admin" ? "/org" : "/app") : null;
  // For logged-in individual users the team CTAs go to "Join an organisation" instead of the
  // default dashboard; org_admin users already have a team workspace so send them straight there.
  const teamHome = account ? (account.kind === "org_admin" ? "/org" : "/app/join") : null;
  const o = overview.ok ? overview.data : null;

  const meData = visuals(t, o, false);
  const teamData = visuals(t, o, true);
  const meArt: FeatureArtVariant[] = ["cv", "radar", "match", "path"];
  const teamArt: FeatureArtVariant[] = ["roster", "cv", "matrix", "gantt"];
  const meSteps: StepItem[] = [1, 2, 3, 4].map((n, i) => ({
    title: t(`step${n}` as "step1"),
    label: `me-${n}`,
    detail: t(`step${n}Detail` as "step1Detail"),
    art: <FeatureArt variant={meArt[i] ?? "cv"} />,
    data: meData[i],
  }));
  const teamSteps: StepItem[] = [1, 2, 3, 4].map((n, i) => ({
    title: t(`tStep${n}` as "tStep1"),
    label: `team-${n}`,
    detail: t(`tStep${n}Detail` as "tStep1Detail"),
    art: <FeatureArt variant={teamArt[i] ?? "invite"} />,
    data: teamData[i],
  }));
  const faqs = [1, 2, 3, 4, 5, 6].map((n) => ({ q: t(`q${n}` as "q1"), a: t(`a${n}` as "a1") }));
  const teamFaqs = [1, 2, 3, 4, 5].map((n) => ({ q: t(`tq${n}` as "tq1"), a: t(`ta${n}` as "ta1") }));

  const signup = (
    <>
      <Link className="a-btn is-small a-for-me" href="/auth/signup">
        {ta("signUp")} <ArrowUpRight size={15} aria-hidden />
      </Link>
      <Link className="a-btn is-small a-for-team" href="/auth/signup?mode=organisation">
        {ta("signUp")} <ArrowUpRight size={15} aria-hidden />
      </Link>
    </>
  );

  return (
    <AudienceRoot initial={audience}>
      <LandingMotion />
      <SiteHeader signup={signup} audienceSwitch={<AudienceToggle />} />
      <main id="a-main">

      {/* ---- for me ---- */}
      <div className="a-for-me">
        <section className="a-wrap a-hero2">
          <div className="a-hero2-copy">
            <span className="a-eyebrow is-square">{t("heroEyebrow")}</span>
            <h1 className="a-display">
              <span>{t("line1")}</span>
              <span className="is-muted">{t("line2")}</span>
              <span className="a-highlight">{t("highlight")}</span>
            </h1>
            <p className="a-hero2-lead">{t("sub")}</p>
            <div className="a-hero2-ctas">
              <a className="a-btn" href="#start">
                {t("ctaUpload")} <ArrowRight size={17} aria-hidden />
              </a>
              <a className="a-link" href="#how">
                {t("ctaHow")} <ArrowUpRight size={16} aria-hidden />
              </a>
            </div>
          </div>
          <figure className="a-fig a-tilt">
            <PathScene />
            <div className="a-fig-bottom">
              <span>{t("figFrom")}</span>
              <i />
              <ArrowRight size={15} aria-hidden />
              <span>{t("figTo")}</span>
            </div>
          </figure>
        </section>
        <Marquee
          lead={t("marqueeLead")}
          strong={t("marqueeStrong")}
          items={[
            { label: t("m1"), icon: <ScanLine size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("m2"), icon: <Radar size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("m3"), icon: <Compass size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("m4"), icon: <Route size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("m5"), icon: <Leaf size={22} strokeWidth={1.4} aria-hidden /> },
          ]}
        />
        <section className="a-wrap a-section" aria-labelledby="start-heading">
          <div className="a-section-intro" data-reveal>
            <div>
              <span className="a-eyebrow is-square">{t("startEyebrow")}</span>
              <h2 id="start-heading" className="a-section-title">
                {t("startTitle")} <span>{t("startTitleMuted")}</span>
              </h2>
            </div>
            <p>{t("startBody")}</p>
          </div>
          <CvPreview />
        </section>
      </div>

      {/* ---- for my team ---- */}
      <div className="a-for-team">
        <section className="a-teamhero">
          <div className="a-wrap a-teamhero-in">
            <div className="a-teamhero-copy">
              <span className="a-eyebrow is-square">{t("forTeamEyebrow")}</span>
              <h1 className="a-display">
                <span>{t("tLine1")}</span> <span className="is-muted">{t("tLine2")}</span>{" "}
                <span className="a-highlight">{t("tHighlight")}</span>
              </h1>
              <p className="a-hero2-lead">{t("tSub")}</p>
              <div className="a-hero2-ctas">
                <Link className="a-btn" href={teamHome ?? "/auth/signup?mode=organisation"}>
                  {t("tCta")} <ArrowRight size={17} aria-hidden />
                </Link>
                <Link className="a-link" href={teamHome ?? "/auth/login?mode=organisation"}>
                  {t("tSignIn")} <ArrowUpRight size={16} aria-hidden />
                </Link>
              </div>
            </div>
            <div className="a-teamhero-art a-tilt">
              <OrgScene />
            </div>
          </div>
        </section>
        <Marquee
          lead={t("marqueeLead")}
          strong={t("tMarqueeStrong")}
          items={[
            { label: t("tm1"), icon: <KeyRound size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("tm2"), icon: <Grid3x3 size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("tm3"), icon: <Users size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("tm4"), icon: <BookOpen size={22} strokeWidth={1.4} aria-hidden /> },
            { label: t("tm5"), icon: <Leaf size={22} strokeWidth={1.4} aria-hidden /> },
          ]}
        />
        {o ? (
          <section className="a-wrap a-statband" aria-label={t("statsLabel")} data-reveal>
            <div className="a-statband-row">
              {(
                [
                  [Radar, o.skills_tracked, t("sSkillsLabel"), t("sSkills")],
                  [ArrowUpRight, o.rising, t("sRisingLabel"), t("sRising")],
                  [BookOpen, o.hrd_claimable_courses, t("sHrdLabel"), t("sHrd", { total: o.courses })],
                  [Leaf, o.sdg_goals_linked, t("sGoalsLabel"), t("sGoals")],
                ] as const
              ).map(([Icon, value, label, sub]) => (
                <div key={label} className="a-statband-item">
                  <span className="a-statband-icon" aria-hidden>
                    <Icon size={18} strokeWidth={1.7} />
                  </span>
                  <strong data-count={value}>{value}</strong>
                  <b>{label}</b>
                  <span>{sub}</span>
                </div>
              ))}
            </div>
            <p className="a-statband-foot">
              {t("sFoot", { date: o.meta.snapshot_date, sources: o.meta.sources.map((x) => x.name).join(", ") })}
            </p>
          </section>
        ) : null}
      </div>

      <section id="features" className="a-wrap a-section" aria-labelledby="features-heading">
        <div className="a-section-intro" data-reveal>
          <div>
            <span className="a-eyebrow is-square">{t("featEyebrow")}</span>
            <h2 id="features-heading" className="a-section-title">
              <span className="a-for-me">
                {t("featTitleA")}
                <br />
                <span>{t("featTitleB")}</span>
              </span>
              <span className="a-for-team">
                {t("tFeatTitleA")}
                <br />
                <span>{t("tFeatTitleB")}</span>
              </span>
            </h2>
          </div>
          <p>
            <span className="a-for-me">{t("featBody")}</span>
            <span className="a-for-team">{t("tFeatBody")}</span>
          </p>
        </div>
        <FeatureGrid className="a-for-me" items={ME_FEATURES.map(([art, key]) => ({ art, title: t(key), body: t(`${key}Body`) }))} />
        <FeatureGrid className="a-for-team is-bento" items={TEAM_FEATURES.map(([art, key]) => ({ art, title: t(key), body: t(`${key}Body`) }))} />
      </section>

      <section id="how" className="a-section a-band" aria-labelledby="how-heading">
        <div className="a-wrap">
          <div data-reveal>
          <span className="a-eyebrow is-square">{t("howEyebrow")}</span>
          <h2 id="how-heading" className="a-section-title">
            <span className="a-for-me">
              {t("howTitleA")}
              <br />
              <span>{t("howTitleB")}</span>
            </span>
            <span className="a-for-team">
              {t("tHowTitleA")}
              <br />
              <span>{t("tHowTitleB")}</span>
            </span>
          </h2>
          </div>
          <div className="a-for-me">
            <Stepper steps={meSteps} />
          </div>
          <div className="a-for-team">
            <Stepper steps={teamSteps} />
          </div>
        </div>
      </section>

      <section className="a-wrap a-section a-explain" data-reveal>
        <div>
          <span className="a-eyebrow is-square">{t("explainEyebrow")}</span>
          <h2 className="a-section-title">
            {t("explainTitleA")}
            <br />
            <span>{t("explainTitleB")}</span>
          </h2>
          <p className="a-explain-body">{t("explainBody")}</p>
          <ul className="a-checklist">
            {[t("explain1"), t("explain2"), t("explain3")].map((line) => (
              <li key={line}>
                <Check size={15} aria-hidden /> {line}
              </li>
            ))}
          </ul>
          <Link className="a-link" href="/about">
            {t("navAbout")} <ArrowUpRight size={16} aria-hidden />
          </Link>
        </div>
        <figure className="a-fig is-sage">
          <FeatureArt variant="match" className="is-hero" />
        </figure>
      </section>

      <section id="faq" className="a-section a-band" aria-labelledby="faq-heading">
        <div className="a-wrap a-faq" data-reveal>
          <div>
            <span className="a-eyebrow is-square">{t("faqEyebrow")}</span>
            <h2 id="faq-heading" className="a-section-title">
              {t("faqTitleA")}
              <br />
              <span>{t("faqTitleB")}</span>
            </h2>
            <p className="a-faq-body">
              <Link className="a-link" href="/about">
                {t("faqBody")} <ArrowUpRight size={16} aria-hidden />
              </Link>
            </p>
          </div>
          <div className="a-faq-list a-for-me">
            {faqs.map((f, i) => (
              <details key={f.q} className="a-faq-item">
                <summary>
                  <span className="a-num">0{i + 1}</span>
                  <span>{f.q}</span>
                  <span className="a-faq-plus" aria-hidden />
                </summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
          <div className="a-faq-list a-for-team">
            {teamFaqs.map((f, i) => (
              <details key={f.q} className="a-faq-item">
                <summary>
                  <span className="a-num">0{i + 1}</span>
                  <span>{f.q}</span>
                  <span className="a-faq-plus" aria-hidden />
                </summary>
                <p>{f.a}</p>
              </details>
            ))}
          </div>
        </div>
      </section>

      <section className="a-wrap a-closing" data-reveal>
        <div>
          <span className="a-eyebrow is-square">{t("closeEyebrow")}</span>
          <h2 className="a-section-title">
            <span className="a-for-me">
              {t("closeTitleA")}
              <br />
              {t("closeTitleB")}
            </span>
            <span className="a-for-team">
              {t("tCloseTitleA")}
              <br />
              {t("tCloseTitleB")}
            </span>
          </h2>
        </div>
        <a className="a-btn a-for-me" href="#start">
          {t("closeCta")} <ArrowRight size={17} aria-hidden />
        </a>
        <Link className="a-btn a-for-team" href={teamHome ?? "/auth/signup?mode=organisation"}>
          {t("tCta")} <ArrowRight size={17} aria-hidden />
        </Link>
      </section>

      </main>
      <SiteFooter
        note={o ? <span>{t("estimate", { date: o.meta.snapshot_date })}</span> : null}
      />
    </AudienceRoot>
  );
}
