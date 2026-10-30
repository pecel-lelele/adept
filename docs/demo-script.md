# Demo film and pitch video script

The **demo film** (planned 3 min 11 s, 1920×1080, 30 fps) is built in a local, gitignored
Remotion workspace at `submission/demo-video/`. That workspace is not a judge-facing link.
The [delivery checklist](submission-deliverables.md) links the team's existing video folder;
the final exported file and anonymous viewing access still require verification.
It follows one person, **Sofia Tan** (a synthetic CV), from uploading her CV to a saved learning plan,
with motion graphics for the parts you cannot see on screen. It has an AI voice-over (ElevenLabs stock voice, video only),
sound effects, a music bed and soft light sweeps. App scenes use screens captured from the local app;
each one can be swapped for a **live screen recording** (see "Combine with the live demo").

## Where the film sits in the 5–7 minute pitch video

Target total: **6:00**, leaving a minute before the 7:00 penalty. The film opens with the problem
(hook, "Why now", Sofia), so it can lead the video and the slides follow it.

| Time | Part | Content | Format |
|---|---|---|---|
| 0:00–3:11 | **Film** | Problem → why now (WEF, Jensen Huang, Malaysia) → Sofia → product walkthrough (live recording inside the app scenes) → why Adept → outro | Remotion `AdeptDemo` |
| 3:11–3:50 | How it works | Architecture diagram; AI models named; guardrails (catalogue-only AI, sources, no hiring decisions) | Slides |
| 3:50–4:35 | SDG impact and KPI | Main SDG 4; relevant 5, 8, 9, 10; targets 4.4, 4.3, 8.2, 8.5; KPI: planning time vs manual, target ≥20% less | Slides |
| 4:35–5:20 | Feasibility and risk | Hardest risks (trend data noise, AI inventing courses) and fallbacks | Slides |
| 5:20–6:00 | Close | Team, live prototype URL, GitHub link, one closing line | Slide |

If the video runs long, cut scene 6 (trend engine, 15 s) or scene 13 (for teams, 12 s) first.

## Copy rules

- One idea per line, twelve words or fewer on screen.
- Numbers instead of adjectives ("6 hours a week, RM 0").
- Same words as the app ("Rising", "Estimate", "UN Goals").
- Say what the person can do ("see", "choose", "follow"), never promise an outcome ("get the job").
- Label forecasts as estimates. Mark the CV as synthetic once.

## Film storyline

The values below are storyboard examples from an older local build, not verified results
for the current revision. Re-record and update visible scores/counts after the matching
and scenario work is merged. Do not claim the historical storyboard proves current behaviour.

Times are approximate (transitions overlap by half a second). **VO** is the voice-over line.

| # | Time | Scene | On screen | VO | Motion |
|---|---|---|---|---|---|
| 1 | 0:00 | **Hook** (motion graphic) | "AI is changing work faster than people can retrain." · **56%** use AI at work · **26%** trained · source line | "AI is changing work faster than people can retrain. In Malaysia, fifty-six percent of professionals already use AI at work. Only twenty-six percent have been trained to use it." | Words rise in time with the voice; numbers count up; bars grow. Wipe + warm light sweep. |
| 1b | 0:11 | **Why now** (motion graphic) | Global estimates: **+170M jobs, −92M displaced by 2030** (WEF, 8 January 2025; multiple macrotrends) · Jensen Huang's opinion (Milken, 6 May 2025) · **Up to 697,000** Malaysian jobs potentially affected (Malay Mail, 24 June 2026; AI, digitalisation and green economy; conditional on insufficient upskilling) | "The World Economic Forum projects major job creation and displacement from global economic and technology shifts. Jensen Huang urges workers to learn AI tools. In Malaysia, the human resources minister warns that AI, digitalisation and the green economy could significantly affect up to six hundred and ninety-seven thousand jobs over three to five years without upskilling." | Three source cards; keep estimate, geography, date and conditions visible. Re-time the revised narration. |
| 2 | 0:33 | **Meet Sofia** (motion graphic) | Her synthetic CV floats in · "Meet Sofia Tan. Process automation analyst · 4 years · Malaysia" · skill chips · an **AI agent at work** card ticking off her usual tasks · "What should she learn next?" | "Meet Sofia Tan. She builds automation for a living… Now AI agents can do much of that work in minutes. So what should she learn next?" | CV drifts; chips pop; agent tasks spin and tick; question rises. |
| 3 | 0:46 | **Adept reveal** | Logo draws in · "See where your skills can take you in the AI era." · Profile → Radar → Match → Plan | "Adept shows where your skills can take you in the AI era, in four steps." | Logo build, green light sweep, step rail lights up. |
| 4 | 0:51 | **1 · Upload a CV** (app) | Landing page → scroll to upload → CV page flies into the drop zone → consent tick → Upload → "Reading the CV…" → **55% Process Automation Analyst · 7 skills found** | "Sofia drops her CV onto Adept. No account needed. It's read in memory, and never stored. In seconds, she sees her best-fit future role…" | Cursor, click ripples and sounds; camera scroll and zoom; callout. |
| 5 | 1:03 | **1 · Confirm skills** (app) | The 7 skills "found in CV", each with a level · then "Ready now: Process Automation Analyst, 52%" | "Adept found seven skills in her CV. She checks each one, and sets her own level. This role is ready now." | Highlight on the skill list; crossfade to ranking. |
| 6 | 1:10 | **Behind the radar** (motion graphic) | AI research papers (arXiv, weekly) + job-market outlook (BLS) → AI model links each paper to 110 skills → this week vs last week → Rising 15 · Steady 76 · Declining 19 · chips: snapshot date, source on every result, estimate label, weekly refresh job | "Behind the radar, Adept reads new AI research every week. An AI model links each paper to a hundred and ten skills, and compares it with the week before… Every result shows its source and its date." | Nodes pop in; lines draw; dots flow along them. |
| 7 | 1:26 | **2 · Radar** (app) | KPI strip highlighted · click **Fast** · "Fast AI pace: 20 skills declining" | "The skills radar shows what's rising right now. Switch to a faster AI pace, and the estimate changes." | Zoom, click, crossfade between scenarios. |
| 8 | 1:35 | **3 · Matches** (app + overlay) | Top card · formula overlay: 45% × skills she has + 25% × demand trend + 30% × her interests = **52%** · skills to close | "Every future role gets a match score she can look inside: the skills she has, demand for the role, and her interests. It also shows exactly which skills she's missing." | Formula parts pop in one by one. |
| 9 | 1:47 | **Trend replay** (motion graphic) | Snapshot toggle 13 Oct → 20 Oct · five roles' scores move (Data Analyst 40% → 35%) · reason chips (▼ Python research, ▲ Human–AI collaboration) · then the real replay card from the app | "When a new week of data arrives, the scores update. Python research fell, so roles that need Python slipped. Adept shows exactly what moved, and why." | Toggle slides; bars and numbers tween; chips pop; app card rises over a dimmed background. |
| 10 | 2:00 | **UN Goals weight** (app) | Cursor drags "How much should the UN Goals count?" to 50% · **Compliance Analytics Officer #4 → #2** | "If social impact matters to her, she can let the UN Goals count. Compliance Analytics Officer jumps from fourth to second." | Drag animation; crossfade; scroll to the new #2. |
| 11 | 2:10 | **4 · Plan** (app) | 6 h/week · RM 0 of RM 300 · click "Choose this role and save the plan" · four free Microsoft Learn courses in order · "Gaps our catalogue cannot close yet" | "Then Adept builds her a learning plan: six hours a week, and it costs her nothing. She saves it… Every course is real… Where no course exists, Adept says so. It never invents one." | Zoom, click, long scroll down the plan, highlight on the gaps card. |
| 12 | 2:26 | **SDG impact** (app) | Goals 4, 8, 9 lit · **Targets 4.4 · 4.3 · 8.2 · 8.5, plus 9.5** | "Her plan hits the exact targets this challenge cares about: relevant skills, affordable learning, productivity, and decent work." | Zoom and highlight. |
| 13 | 2:34 | **For teams** (app) | Team skill-gap heatmap → "AI-ready back office" programme (5 accepted · 3 waiting) → an employee's agreement | "HR teams use the same engine to see where their team is short, send a funded learning programme, and let every employee review it, and choose what HR can see." | Three screens crossfade with zooms. |
| 13b | 2:46 | **Why Adept** | Three cards: For people (a clear next step, in minutes) · For organisations (training budget aimed at real gaps) · For Malaysia (a workforce that keeps pace with AI; SDG targets 4.4, 4.3, 8.2, 8.5; goal of 20% faster planning, to be measured) | "For people, Adept turns uncertainty into a clear next step, in minutes. For organisations, training budgets go to the gaps that really matter. And for Malaysia, a workforce that keeps pace with AI: quality education, and decent work." | Cards rise one by one with the voice. |
| 14 | 3:01 | **Outro** | Four principles (sources, estimates, grounded AI, people decide) → logo · "Make your next move." | "Sources on every result. Estimates labelled. People make the decisions. Adept. Make your next move." | Cards pop then clear; logo builds; light sweep; ding. |

## Evidence register

Sources checked on 30 October 2026. Publication dates below are not the recording date
or the observation date of Adept's trend snapshot.

| Scene / claim | Source and publication / event date | Meaning and limitation |
|---|---|---|
| 1: 56% use AI; 26% trained | [Hays Malaysia](https://www.hays.com.my/press-release/content/future-of-work-malaysia-technology-ai-impact), 7 March 2025 | Historical reported survey shares; the 30 percentage-point difference does not measure the share of AI users lacking training. |
| 1b: 170M created, 92M displaced by 2030 | [WEF release](https://www.weforum.org/press/2025/01/future-of-jobs-report-2025-78-million-new-job-opportunities-by-2030-but-urgent-upskilling-needed-to-prepare-workforces/), 8 January 2025 | Global projections across technology, economic, demographic and green-transition drivers; not AI-only effects or observed losses. |
| 1b: Huang on learning AI | [Milken event transcript](https://milkeninstitute.org/sites/default/files/2025-05/new-innovation-economy-conversation-nvidia-ceo-jensen-huang_Transcript_GC25.pdf), event 6 May 2025, around 06:20 | Speaker opinion, not a measured statistic. Primary transcript supports a paraphrase; no unverified Reuters quotation is needed. |
| 1b: up to 697,000 Malaysian jobs affected | [Malay Mail, Anis Zalani](https://www.malaymail.com/news/malaysia/2026/06/24/malaysia-records-42807-job-losses-as-697000-roles-at-risk-from-ai-without-urgent-upskilling-says-hr-minister/224963), 24 June 2026 | Minister's conditional warning over three to five years, attributed to a TalentCorp study; AI, digitalisation and green economy. Not 697,000 observed job losses. |
| App scores, course counts, durations and SDG/ranking changes | Record the final revision, snapshot and synthetic intake with each new capture | Storyboard values require revalidation; they are not independent labour-market statistics. |
| At least 20% faster planning | Proposed matched manual/Adept evaluation | Target only; no collected baseline or achieved reduction is asserted. |

Presentation production tools and outstanding asset credits are declared in
[technical declaration section 4.4](submission-technical-declaration.md#44-content-and-presentation-tools).

## Combine with the live demo

The handbook requires a **live** walkthrough of the working build, so scenes 4, 5, 7, 8, 10, 11, 12 and
13 accept real screen recordings.

1. Deploy the app. Record the screen at **1920×1080** on the production build (not the dev server,
   which shows a red "Issue" badge), browser zoom 100%, bookmarks bar hidden, no other tabs.
2. Use a fresh account and upload Sofia's synthetic CV, so the numbers match the voice-over.
   Interests: automation, process improvement, data. Time: 6 h/week. Tick "My employer is
   registered with HRD Corp".
3. Record one clip per app scene following the click path above. Move the mouse slowly and pause one
   second after each click.
4. Put the clips in `demo-video/public/live/` and set them in the `recordings` prop of `AdeptDemo`
   (use the local workspace's README; its contents are not part of the submitted source).
5. Also keep one uncut 20–30 second recording of **radar → matches → change the snapshot date → the
   scores move**. That is the "most important working feature" judges want to see live.
