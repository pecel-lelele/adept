# RunPod deployment handoff

The code is ready for deployment; no RunPod endpoint has been created. Your friend needs a
RunPod account with credits, a container registry, Docker, and the existing Adept database
configuration. No application-code edits are needed for the normal deployment.

## 1. Get this branch

```bash
git fetch origin
git switch feat/jobs-live-openings
git pull --ff-only
```

Install the repository's ordinary requirements in its Python 3.11 environment. The pipeline
caller does not need PyTorch; the model and its dependencies belong in the worker image.

## 2. Build and publish the worker

From the repository root, replace `YOUR_REGISTRY` once with your Docker Hub username or
other registry namespace, then use the same image name in RunPod:

```bash
docker login
docker build --platform linux/amd64 -f src/pipelines/trends/runpod/Dockerfile -t YOUR_REGISTRY/adept-minilm:v1 .
docker push YOUR_REGISTRY/adept-minilm:v1
```

The first build downloads PyTorch/CUDA libraries and the pinned MiniLM weights. It can take
time and disk space. The resulting image contains the weights, so each worker does not need
to download the model again. Use a public image, or configure registry credentials in RunPod.

## 3. Configure RunPod

Create a **queue-based Serverless endpoint** with the image above. Use a GPU compatible with
the image's PyTorch 2.8 / CUDA 12.8 runtime. Start with **0 active workers** and **1 maximum
worker**; raise the limit only if more parallel throughput is needed. Keep the image's
entrypoint. No database URL, CV data, or Adept API secrets belong in this worker.

Use the endpoint test tool to submit the JSON in `test_input.json`:

```json
{"input":{"texts":["Human-AI collaboration design","Research on supervised AI agents and human feedback."]}}
```

A successful completed response contains `output.model`, `output.revision`,
`output.dimensions: 384`, and two embeddings of 384 finite numbers. Wait for this smoke test
to pass before enabling the scheduled pipeline. Save the endpoint ID and create a RunPod
API key permitted to run that endpoint.

## 4. Test from the codebase

Set the existing `DATABASE_URL` for Adept's PostgreSQL, then set these environment variables
in the pipeline process (PowerShell example):

```powershell
$env:TRENDS_EMBEDDING_BACKEND='runpod'
$env:TRENDS_RUNPOD_ENDPOINT_ID='YOUR_ENDPOINT_ID'
$env:TRENDS_RUNPOD_API_KEY='YOUR_RUNPOD_API_KEY'
$env:PYTHONPATH='src/api;src'
python -m pipelines.trends.embed_taxonomy
python -m pipelines.trends.run --dry-run
```

The taxonomy command writes catalogue vectors. The dry run does not publish a snapshot,
but can fetch and cache public research and write ingestion signals. It needs two observed
weeks to validate a changed trend snapshot. An insufficient-history message is a data
readiness issue, not proof that RunPod failed. Once validation passes, publish with:

```powershell
python -m pipelines.trends.run
```

Keep keys in environment variables or secret stores, never in source files or browser settings.

## 5. Enable GitHub's weekly refresh

In repository **Settings → Secrets and variables → Actions**, configure:

| Kind | Name | Value |
|---|---|---|
| Secret | `TREND_DATABASE_URL` | Existing Adept PostgreSQL connection URL |
| Secret | `TRENDS_RUNPOD_API_KEY` | Friend's RunPod API key |
| Variable | `TRENDS_RUNPOD_ENDPOINT_ID` | The endpoint ID, without a URL |

Open the **Trends refresh** workflow in Actions and run it manually once. It then runs on its
existing Monday schedule. Missing configuration skips the run; remote failures stop it;
both leave the last valid published snapshot available with its original date.

RunPod is the default backend. Set `TRENDS_EMBEDDING_BACKEND=local` explicitly only for local
CPU development, with sentence-transformers installed. Adi's RunPod chat endpoint and the
Gemini CV-suggestion model are separate; their settings do not need to change.
