# Mentor follow-up: where Adept stands (23 Oct 2026)

Follow-up to the session with Ravenna Chen Yaohui. This covers each action item, what the
product now does, and what is still open. Numbers come from the app's own data as of today.

## Action items

| Action item | Status | What exists now |
|---|---|---|
| Pitch structure: team, problem, solution, target clients, business model, risk/collaboration | **Open (pitch work)** | Problem, solution and demo are ready. Business model and risk/collaboration slides still need writing (suggestions below). |
| Show impact without real users (simulation + surveys) | **Partly** | The product can now measure a before/after on real jobs (below). Surveys are not done yet. |
| Link course completion to company job positions or certifications | **Done** | Each plan shows live openings for the role and how many match the person's skills before and after the plan. It also lists optional certification exams with official prices. |
| Show the path to real jobs after training | **Done, with limits** | 1,210 current openings from 127 employers, linked to roles and plans. Adept links to the employer's ad; it does not place people. |

## What changed in the app

- **Job openings.** Current openings come from employers' public career-site feeds (Agoda, AIA, Citi, Intel, AMD, Micron, PwC, Flex, Jabil and 118 others) and remote-job boards. They are stored in the database and refreshed by a pipeline.
- **Openings in the plan.** Each opening shows which of its skills the person already has, which their plan covers, and the match before and after the plan.
- **Job sources.** We read only feeds that employers publish for this purpose. JobStreet's terms forbid scraping, and LinkedIn and Indeed have no public jobs API, so neither is used. Careerjet and Jooble are wired in and start working with a free publisher key; they would add local Malaysian listings legally.
- **Certification exams.** 14 exams: Microsoft, AWS, Google Cloud, IIBA and IAPP. Each has the issuer's own price for Malaysia, converted at the Bank Negara rate, and is linked to the role skills it covers.
  - On a personal plan the person pays the exam provider.
  - On a team programme the company pays.
- **Plan page.** One summary, two tiles (certification, job openings) and the learning steps. Everything else is folded into one-line sections.
- **CV reading.** "Wording to review" no longer lists company names, job titles or sentences. For skills phrased differently from the catalogue, Adept suggests the closest skill by meaning (Gemini embeddings stored in Postgres with pgvector). The person adds the suggestion with one click.

## On reimbursement

The current employee reimbursement flow (request, approval, receipt, payout) is not how most Malaysian companies upskill teams.

- **HR usually buys directly.** HR picks the programme and pays the provider directly, often using an HRD Corp grant the employer applies for, or buys company-wide licences.
- **Reimbursement is the exception.** It mostly covers individual cases, such as a degree or a certification exam the employee chooses.

**Recommendation:**
- Make "HR selects and pays" the default team flow.
- Reduce the employee side to "request a course" (HR approves and buys it).
- Keep reimbursement only for exam fees after a pass, if at all.
- Do not present reimbursement as a selling point.

## What the real job data told us

- **The role list misses large job families.** About 60% of current openings fit none of Adept's 28 target roles. The biggest gaps are finance and accounting (~110 openings), engineering technicians (~100), sales (~70) and software engineering (~60). Adding a few of these roles would make Adept useful to far more people.
- **Some target roles are rare in employer feeds.** Process Automation Analyst (Sofia's best match) has 2 openings today. Data Analyst has 17 and Compliance Analytics Officer has 39. For the demo, either use a role with more openings or explain that this role is mostly advertised on JobStreet and LinkedIn.

## Suggestions for the pitch

- **Business model (to validate, not final):**
  - free for individuals;
  - a per-employee yearly licence for companies, sold to HR and L&D;
  - an institution licence for TVET colleges and universities.

  Set the price only after asking HR managers what they pay today for training platforms.
- **Impact without users:**
  - Run all synthetic CVs through the app and report the change in openings that match each person's skills, before and after their plan. The app computes this now.
  - Add a short survey: about 10 working adults and 5 HR or L&D managers, on time spent choosing training and on willingness to pay.
- **Risk and collaboration (end of the pitch):**
  - Risks: data coverage (job sources), keeping course prices current, and privacy of CVs (read in memory, never stored).
  - Partners that address them: TalentCorp or PERKESO (MYFutureJobs data), HRD Corp (training grants) and employer hiring partners.
