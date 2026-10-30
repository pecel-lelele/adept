# Documentation

New here? Read the [project README](../README.md) first, then [architecture](architecture.md).

## Understand the product

| Guide | Purpose |
|---|---|
| [Project context](project-context.md) | Competition brief, users and scope |
| [Solution design](solution-design.md) | Product approach and user journeys |
| [Architecture](architecture.md) | Services, data flow and workspace boundaries |
| [Skill exposure methodology](skill-exposure-methodology.md) | How trend coefficients are computed and read |
| [Diagrams](diagrams/index.html) | System diagrams (open in a browser) |

## Work on the code

| Guide | Purpose |
|---|---|
| [Tasks](tasks.md) | Feature areas and scope |
| [Team rules](team-rules.md) | Collaboration and engineering agreements |
| [Decisions](decisions.md) | Append-only record of methods, data and implementation choices |

Each feature also has a `FEATURE.md` next to its code describing its API and method.

## Run and deploy

| Guide | Purpose |
|---|---|
| [Replit deployment](replit-deployment.md) | Production deployment and configuration |
| [Replit proxy verification](replit-proxy-verification.md) | Checking the trusted-proxy setup |
| [Review runbook](review-runbook.md) | Data refresh and demo preparation |
| [Demo script](demo-script.md) | Live demo walkthrough |

## Folders

| Folder | Contents |
|---|---|
| [demo-cvs/](demo-cvs/README.md) | Synthetic demo CVs and their profiles (read by the app and tests) |
| [reference/](reference/critical-occupations.md) | Malaysia critical-occupations reference list (read by matching) |
| [evidence/](evidence/) | Generated measurements: KPI timings, impact evidence, CV flow test |
| [submission/](submission/) | Hackathon report, technical declaration and checklists |

Run results belong in PR descriptions and CI; old one-off reports are in Git history.
Use lowercase kebab-case filenames and repository-relative links.
