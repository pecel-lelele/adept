# Domain 1 rubric check

Checked on 23 October 2026 against the local build of `main` (after PR #10 and #11) with synthetic
accounts only. Scores are our own estimate of where judges are likely to land. Nobody can see the other
~100 teams' work, so treat this as a readiness check, not a ranking.

## Verdict

Adept covers the whole Domain 1 chain with working software. Few teams will have trend replay,
explainable scores, costed pathways, SDG-weighted ranking **and** an HR mode. That depth can put us in
the top group. Three things can still cost us a final-round place:

1. **No live URL yet.** The handbook requires a deployed link; a screen recording does not replace it.
   This is the biggest risk to Feasibility (25%).
2. **The story is too broad.** Judges reward one sharp user and one moment of need. Lead with one
   person (the demo uses Sofia Tan's synthetic CV), not four user groups.
3. **A few things look broken on camera** (see "Fix before recording").

## Score by criterion

| Criterion (weight) | Today | After the fixes | Why |
|---|---|---|---|
| Innovation & Creativity (30%) | Strong | Very strong | Trend replay explains *why* scores moved. The UN Goals slider changes the ranking, not just a badge. Two AI-pace scenarios with ranges. Catalogue-only assistant (Adi). Employer programmes with employee consent. Existing tools (TalentCorp's MyMahir, course platforms) cover parts; our pitch is the closed loop. |
| Problem-Solution Fit (25%) | Very strong | Very strong | All six must-haves work end to end, in three languages. "You decide" wording and "never makes hiring decisions" keep people in charge. |
| Feasibility of Build (25%) | At risk | Strong | Working build, 487 automated tests, CI, Docker. **Missing: a public URL.** Hardest risk and fallback are documented. |
| Clarity of Proposal (20%) | Medium | Strong | Content is right but the wording is hedged. A cold listener must be able to repeat who the user is, the problem, and what they walk away with. |

## The six must-haves: proof on camera

| Must-have | Where | Proof shot in the demo film |
|---|---|---|
| 1. Skills profile intake | `/` CV upload; `/app/onboarding` | Sofia's CV → "55% Process Automation Analyst · 7 skills found" in seconds; 7 skills "found in CV" to confirm |
| 2. AI-trend signal layer | `/app/radar`; weekly `trends-refresh.yml` | 15 rising · 76 steady · 19 declining · 110 skills · source and date on screen |
| 3. Matching with score and gap | `/app/matches` | Score parts 54% / 62% / 40% → 52%; skills to close |
| 4. Personalised pathway | `/app/pathway` | Four free courses in order, 6 h/week, RM 0 of RM 300; gaps the catalogue cannot close |
| 5. SDG mapping | `/app/sdg`, SDG chips, UN Goals slider | Targets 4.4, 4.3, 8.2, 8.5 (+9.5) on Sofia's plan; slider moves Compliance Analytics Officer #4 → #2 |
| 6. Uncertainty | Moderate / Fast toggle; ranges; "Estimate" labels | Fast scenario: 19 → 20 skills declining |

## SDG coverage across the whole app

Counted from `src/data/seed/sdg/` (curated role and skill links, each with a reason and evidence) plus the
links the app computes for every plan (skills built → 4.4; free or within budget → 4.3). The app marks
goals 4, 5, 8, 9 and 10 as its focus goals and shows all 17.

| Goal | Domain role | Role links | Skill links | Judge targets covered | Status |
|---|---|---|---|---|---|
| SDG 4 Quality Education | **Main** | 6 | 75 | **4.4** (72 skill + 4 role links, plus every plan), **4.3** (2 links, plus every free or in-budget plan) | Strong |
| SDG 8 Decent Work | Relevant | 24 | 57 | **8.2** (16 role + 10 skill), **8.5** (4 role + 39 skill) | Strong |
| SDG 9 Industry & Innovation | Relevant | 14 | 11 | 9.5 mainly | Good |
| SDG 10 Reduced Inequalities | Relevant | 4 | 7 | 10.2 | Thin |
| SDG 5 Gender Equality | Relevant | **0** | **1** | 5.b (AI literacy, counted at team or region level only) | **Weak** |

**All four judge targets (4.4, 4.3, 8.2, 8.5) are covered.** SDG 5 and SDG 10 are relevant goals for the
domain but barely appear. A judge who opens the SDG page for most roles will not see them.

Suggested fix (owner M3, with team review): add evidence-backed links that do not use anyone's gender or
background (the fairness rule forbids that), for example:
- **5.b** (technology that empowers women) for more digital and AI skills, counted at team, cohort or
  region level, as the existing AI-literacy link already does;
- **10.2 / 10.3** (inclusion, equal opportunity) computed at plan level, like 4.3: free or HRD
  Corp-funded plans and plans in Bahasa Melayu or Chinese lower barriers to access.

## Fix before recording (in order of impact)

1. **Deploy and get a public URL** (Replit is a sponsor). Record on a production build; the dev server
   shows a red "Issue" badge from React hydration warnings.
2. **Refresh the trend snapshot from live data** (M1). The radar shows "Historical data… replayed here
   as the 2026-10-20 snapshot". Run the pipeline on this week's arXiv feed.
3. **Smooth the weekly signal** (M1). One-week arXiv change is noisy: "Python programming", "AI ethics"
   and "AI literacy" show as *declining*, which judges may question. A 4-week window reads as more credible.
4. **CV "Wording to review" list is noisy** (M2). After uploading Sofia's CV, the list shows section
   headings and fragments ("PROFESSIONAL EXPERIENCE", "handling.", "idation", "Malaysia",
   "Fictional employer"), and even "robotic process automation (RPA)", which *was* matched. It sits
   above the real skill list in onboarding, so a judge sees noise first.
5. **Raw skill IDs on the radar** (M1/M2). Sofia's "Your skills" panel shows `rpa` and `sql` as
   "Not tracked": the CV extractor's skill IDs are missing from the trend snapshot's skill list.
6. **Replay chip wording** (M2). A role can move *up* while its only chip says a skill *fell* (it rose
   because other roles dropped). Consider "Rose because other roles fell".
7. **Short pathways** ("about 2 weeks", 7.7 h): most catalogue items are short Microsoft Learn modules.
   Present it as "her first 8 hours", not "become a Process Automation Analyst in 2 weeks".
8. **SDG 5 and 10 coverage** (M3), see above.

## Rules we must not break on camera

- Only synthetic people (Sofia Tan's CV, the Demo Bank Operations team). The film says so on screen.
- Every number shown carries its source and date; keep the "Estimate" label in frame.
- Name the AI: all-MiniLM-L6-v2 (skill signals), Runpod GLM-5.3 with Gemini fallback (Adi). The film's
  voice-over is AI-generated (Kokoro); say so in the video description.
- Keep the pitch video between 5:00 and 7:00 (−1 point per 30 seconds over).
