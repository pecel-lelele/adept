# RunPod deployment handoff

The Docker image is built and published automatically to **GitHub Container Registry** by
the `publish-minilm.yml` workflow on every push to `main`. No local Docker build is needed
unless you are iterating on the worker code itself.

Image: `ghcr.io/pecel-lelele/adept-minilm:latest`

---

## 1. Verify the image is published

Open the repository on GitHub → **Packages** (right sidebar). Confirm `adept-minilm` is
listed and the `latest` tag is recent. If it is missing, go to
**Actions → Publish MiniLM worker** and click **Run workflow**.

---

## 2. Create a RunPod Serverless endpoint

1. Log in to [RunPod](https://www.runpod.io/) and open **Serverless → + New Endpoint**.
2. **Container image**: `ghcr.io/pecel-lelele/adept-minilm:latest`
   - The image is public; RunPod does not need registry credentials.
3. **GPU type**: any CUDA-capable GPU (RTX 3090, A4000, or lower-tier for cost savings).
   The image includes CUDA 12.8 / PyTorch 2.8 weights baked in at build time.
4. **Worker count**: Min workers `0`, Max workers `1` (sufficient for the weekly batch).
5. **Container disk**: 10 GB (weights are ~90 MB, PyTorch libraries fill the rest).
6. **Environment variables** (in the RunPod console — do not commit):
   - `MINILM_DEVICE=cuda` (auto-selected; set to `cpu` only to test without a GPU)
7. Leave all other settings at their defaults. Click **Deploy**.
8. Copy the **Endpoint ID** (short alphanumeric string shown in the endpoint row).

Test with the built-in RunPod playground → paste this input:
```json
{"input":{"texts":["Human-AI collaboration design","Research on supervised AI agents."]}}
```
A successful response contains `output.model`, `output.revision`, `output.dimensions: 384`
and two arrays of 384 finite floats. Wait for `COMPLETED` before wiring the pipeline.

---

## 3. Add the endpoint to the project

### A. Local `.env`

Fill in the two values in your root `.env`:
```env
TRENDS_RUNPOD_ENDPOINT_ID=your-endpoint-id   # short ID from the RunPod console
TRENDS_RUNPOD_API_KEY=rpa_xxxx               # RUNPOD_API_KEY from Account → API Keys
```

### B. GitHub Actions secrets/variables

In **Settings → Secrets and variables → Actions**:

| Kind     | Name                      | Value                                     |
|----------|---------------------------|-------------------------------------------|
| Secret   | `TREND_DATABASE_URL`      | Adept PostgreSQL connection URL           |
| Secret   | `TRENDS_RUNPOD_API_KEY`   | Your RunPod API key                       |
| Variable | `TRENDS_RUNPOD_ENDPOINT_ID` | The endpoint ID (no https://, just the ID) |

These are already consumed by `trends-refresh.yml`; the weekly cron will skip
automatically when any of them is missing.

### C. Replit deployment

When the app runs on Replit, the **trend pipeline runs as a GitHub Actions job, not inside
Replit itself**. The Replit app only reads stored `trend_snapshots` from the PostgreSQL
database; it never calls the RunPod MiniLM endpoint directly during a web request.

Configure the Replit environment (Secrets panel) with the **database connection** (same
`DATABASE_URL` that GitHub Actions writes to) so the Next.js frontend and FastAPI backend
can serve the pre-computed snapshots. No RunPod variables belong in Replit; they live only
in GitHub Actions secrets.

---

## 4. Smoke-test from the codebase (optional)

Once the endpoint ID and API key are in `.env`, verify the round-trip locally (requires
Python 3.11 and the root `requirements.txt`):

```powershell
$env:PYTHONPATH='src/api;src'
python -m pipelines.trends.embed_taxonomy
python -m pipelines.trends.run --dry-run
```

The dry run fetches public research, encodes it via RunPod, and validates the result without
publishing. An "insufficient history" message means the database has fewer than two weeks of
snapshots — this is normal for a fresh database and does not indicate a RunPod failure.

---

## 5. Enable the weekly refresh

Go to **Actions → Trends refresh → Run workflow** once to verify the full pipeline. It
publishes a new snapshot if validation passes, or exits cleanly without touching the
database on any failure.

The cron (`cron: "41 3 * * 1"`) runs every Monday at 03:41 UTC automatically after that.

---

## Notes on the image

| Component            | Value                                                  |
|----------------------|--------------------------------------------------------|
| Image                | `ghcr.io/pecel-lelele/adept-minilm:latest`             |
| Base OS              | `python:3.11-slim`                                     |
| Model                | `sentence-transformers/all-MiniLM-L6-v2`               |
| Revision (pinned)    | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`             |
| Dimensions           | 384                                                    |
| Max batch            | 64 texts per request                                   |
| PyTorch              | 2.8.0 + CUDA 12.8                                      |

The image contains baked-in weights; workers start without downloading the model.
`MINILM_DEVICE=cpu` can be set in the RunPod endpoint environment to test on CPU workers.
