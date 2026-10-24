# MiniLM deployment and operations

## Verified state on 24 October 2026

| Component | Location / evidence |
|---|---|
| Public worker image | `ghcr.io/pecel-lelele/adept-minilm:latest` |
| Queue-based Serverless endpoint | https://api.runpod.ai/v2/ta14jd0by2ijl2 |
| Pinned model | `sentence-transformers/all-MiniLM-L6-v2`, revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` |
| Image publication | [Successful publisher](https://github.com/pecel-lelele/adept/actions/runs/40007781487), source commit `ee2c4fa3134445e52e4597acb32a4e997ae8ff1e` |
| Published image digest | `sha256:026b380da15af9314b244111f916653893160458c6092227c84b52aa796689a2` |
| Live inference | `COMPLETED`; correct model/revision; two 384-dimensional vectors. One test observed 79,821 ms queue/startup delay and 231 ms execution; these are not latency guarantees. |
| First integrated refresh | [Run 40013352381](https://github.com/pecel-lelele/adept/actions/runs/40013352381) fetched 366 papers and counted mentions, then failed saving to database host `helium`. No new snapshot was published. |

The worker is deployed. Inference, database reachability and snapshot publication are
separate acceptance checks. A successful embedding test does not prove a production write.

## 1. Architecture and credentials

GitHub Actions runs the batch pipeline: public research â†’ RunPod embeddings â†’ deterministic
scoring â†’ validation â†’ PostgreSQL publication. Replit's web/API serves saved snapshots;
opening an app page does not invoke MiniLM. Adi's GLM chat and Gemini CV embeddings use
separate provider settings.

| Where | Exact name | Value / purpose |
|---|---|---|
| GitHub repository secret | `TREND_DATABASE_URL` | Reachable connection string for the production database read by the published app. |
| GitHub repository secret | `TRENDS_RUNPOD_API_KEY` | Dedicated MiniLM key with permission to invoke the endpoint. |
| GitHub repository variable | `TRENDS_RUNPOD_ENDPOINT_ID` | `ta14jd0by2ijl2`; only the ID. |
| Pipeline environment | `DATABASE_URL` | Workflow maps the `TREND_DATABASE_URL` secret to this variable. |
| Pipeline environment | `TRENDS_EMBEDDING_BACKEND` | Workflow sets `runpod`; `local` is explicit CPU development. |
| RunPod worker | `MINILM_DEVICE` | Automatically chooses CUDA when available; `cpu` is a test option. |
| Replit app | `DATABASE_URL` | Development and published production environments can have different connections. |

Enter credentials directly into secret stores. MiniLM reads its dedicated key and never
falls back to Adi's `RUNPOD_API_KEY`. Database URLs, GLM and Gemini keys do not belong in
the worker container.

### Replit development versus production

Host `helium` is Replit's private development database; GitHub-hosted runners cannot
resolve or access it. Renaming the secret does not make that database reachable.

For the Replit production route, the account owner must **Publish** the app first.
With current Helium infrastructure, publishing creates a separate production database
when the development database contains data. In the legacy flow, enable production database
creation in Publishing settings; copy only intended catalogue and synthetic demo data.
Then open **Database â†’ Production â†’ Settings / Connection details** and use that production
connection in GitHub's `TREND_DATABASE_URL`, verifying external access. Keep development
configuration intact; do not replace the hostname in an existing URL manually.

If production is not ready, test the pipeline inside the Replit environment that owns the
development database, or use a separately configured PostgreSQL reachable by both app and
runner. Moving data or adding another scheduler is separate work. See
[Replit's development/production guide](https://docs.replit.com/features/data-and-storage/development-and-production).

## 2. Build and publish

The [publisher](../../../../../../../.github/workflows/publish-minilm.yml) is manual-dispatch only
from the trusted repository's `main` branch. The guarded job builds `linux/amd64` and
uses job-scoped `packages: write` with `GITHUB_TOKEN` to publish `latest` and
`sha-<commit>` tags. PRs, forks and other branches cannot reach publishing credentials.
The first verified image was published from the deployment branch; future publications
require a reviewed manual dispatch from `main`.

The pinned worker dependencies and model weights are built into the image. The first
build downloads these; registry push and cache export add time. The verified publication
took about 11 minutes, including about five minutes exporting one cache layer. Image builds
do not run for app page loads or inference requests.

GHCR package visibility is separate from repository visibility. The current package is
public and its manifest was anonymously checked with HTTP 200. Private images need RunPod
registry credentials; an inference API key cannot authenticate an image pull. Prefer a
published commit tag or digest for reproducibility. Preserve the image's entrypoint.

Optional manual build from the repository root:

```bash
docker login YOUR_REGISTRY
docker build --platform linux/amd64 -f artifacts/api-server/python/src/pipelines/trends/runpod/Dockerfile -t YOUR_REGISTRY/adept-minilm:v1 artifacts/api-server/python
docker push YOUR_REGISTRY/adept-minilm:v1
```

## 3. RunPod settings and inference test

Use a **queue-based Serverless endpoint**, a GPU compatible with the pinned CUDA runtime,
**Active workers = 0**, and **Max workers = 1** for this batch workload. No custom start
command is required.

Open **Serverless â†’ adept-minilm â†’ Requests**, paste [test_input.json](test_input.json), and
click **Run** once:

```json
{"input":{"texts":["Human-AI collaboration design","Research on supervised AI agents and human feedback."]}}
```

Let the request complete. Expect `status: COMPLETED`, the pinned model/revision,
`output.dimensions: 384` and two finite non-zero vectors. A worker saying Running
alone does not establish inference success. Zero active workers allows automatic scale-down
after the job; no continuous test or cancellation of a completed request is needed.

API callers send this body to `POST /runsync` with bearer authentication. The client
polls `GET /status/<job_id>` if queued and validates model/revision, count, dimensions
and values. The live base is `https://api.runpod.ai/v2/ta14jd0by2ijl2`; other routes are
`POST /run` and `GET /health`. Use `TRENDS_RUNPOD_API_KEY`, never the separate GLM chat
credential. Each request allows 1â€“64 non-empty texts, at most 4,096 characters each.

## 4. Automatic refresh and acceptance

1. In repository **Settings â†’ Secrets and variables â†’ Actions**, add the two secrets and
   one variable from section 1. A secret named only `DATABASE_URL` is not read here.
2. Open **Actions â†’ Trends refresh â†’ Run workflow â†’ main**.
3. Inspect the `refresh` job: dependency installation, **Verify database access before
   inference**, then **Ingest, score, validate and publish**.
4. Require `Published snapshot YYYY-MM-DD.` in the log and that date in the
   database-backed Radar. Skipped work or demo fixtures do not establish publication.

The schedule is Mondays **03:41 UTC / 11:41 WITA**; manual runs are also supported.
Missing settings produce a notice and skip work, so a run can be green without inference.
Preflight checks that transactions are writable and the role can read/write the required
trend tables and use their ID sequences. Ten-second connection/query timeouts and a
one-minute step limit bound this work before fetching research or invoking RunPod; failures
do not log credentials. This does not replace applying migrations or snapshot validation.

Publication needs fresh research, two distinct observed weeks, at least 50 evidenced skills,
known IDs and finite numeric values. Inference can succeed while data-readiness validation
fails. Failures leave the previous published snapshot intact; ingestion audit rows may
already exist. No Replit redeploy is needed per snapshot when the API reads the same database.

## 5. Recovery and costs

| Symptom | Action |
|---|---|
| Image pull denied / unauthorized | Check GHCR package visibility or RunPod registry credentials. |
| No workers start after failures | Inspect Workers system/container logs. If Max workers was reduced to 0, restore 1 after fixing the cause, then send one test. |
| Green workflow, no snapshot | Inspect the missing-configuration notice and the publication log. |
| Database host `helium` cannot resolve | Use a reachable production connection, or run the pipeline inside the owning Replit environment. |
| Inference works, validation fails | Inspect observation weeks and skill coverage; do not fabricate history or bypass the gate. |

To preserve credits, defer publication and repeated refresh attempts until the production
database is ready. RunPod flex workers scale to zero; active workers remain billed while
warm. Running workers are billed through startup, processing and their idle timeout; storage
can have separate charges. Replit Autoscale uses request-based app compute, Reserved VM
runs continuously, and production database usage is separate. Database compute pauses
after inactivity, while stored data can still contribute to usage. Check the account's
billing controls rather than assuming zero visitors means zero total charges.

References: [RunPod requests](https://docs.runpod.io/serverless/endpoints/send-requests),
[recovery](https://docs.runpod.io/serverless/troubleshooting),
[RunPod billing](https://docs.runpod.io/serverless/pricing),
[Replit publishing costs](https://docs.replit.com/billing/deployment-pricing).

## 6. Local pipeline checks

Outside Replit, install ordinary repository requirements. Securely export an
externally reachable `DATABASE_URL` and the dedicated MiniLM key in the pipeline
process; PowerShell:

```powershell
$env:TRENDS_EMBEDDING_BACKEND='runpod'
$env:TRENDS_RUNPOD_ENDPOINT_ID='ta14jd0by2ijl2'
$env:PYTHONPATH='src/api;src'
python -m pipelines.trends.preflight
python -m pipelines.trends.embed_taxonomy
python -m pipelines.trends.run --dry-run
```

Inside the owning Replit development workspace, its injected `helium` connection
is valid there. Skip the external-runner preflight, which deliberately rejects
that private hostname. After migrating/seeding that development database, run:

```bash
cd artifacts/api-server/python
export PYTHONPATH=src/api:src
export TRENDS_EMBEDDING_BACKEND=runpod
export TRENDS_RUNPOD_ENDPOINT_ID=ta14jd0by2ijl2
.venv/bin/python -m pipelines.trends.embed_taxonomy
.venv/bin/python -m pipelines.trends.run --dry-run
```

Keep the dedicated key in workspace Secrets. These commands can write development
data and spend inference credits; they do not update the published app's separate
production database. The scheduled Actions workflow always retains its preflight.

Taxonomy embedding writes catalogue vectors. A dry run can fetch/cache research and write
ingestion signals but never publishes a snapshot. After validation passes, run
`python -m pipelines.trends.run` to publish. Local CPU development explicitly sets
`TRENDS_EMBEDDING_BACKEND=local` and installs sentence-transformers separately.
