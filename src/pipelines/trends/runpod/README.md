# MiniLM on RunPod Serverless

For the teammate deploying it, follow [DEPLOYMENT_HANDOFF.md](DEPLOYMENT_HANDOFF.md).

This worker hosts `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), pinned to
revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`. It encodes public arXiv sentences
and catalogue labels. The existing Adept pipeline keeps the 0.55 cosine threshold,
trend scoring, validation and atomic publication. It never sends CVs to this worker.
The API continues serving stored snapshots; no GPU is needed for web requests.

## Build and deploy

The worker image is automatically built and published to GitHub Container Registry by the
`publish-minilm.yml` GitHub Actions workflow on push to `main`:

`ghcr.io/pecel-lelele/adept-minilm:latest`

RunPod can pull directly from this public registry image without credentials.

To build and push manually instead, from the repository root:

```bash
docker build --platform linux/amd64 -f src/pipelines/trends/runpod/Dockerfile -t YOUR_REGISTRY/adept-minilm:v1 .
docker push YOUR_REGISTRY/adept-minilm:v1
```

The Dockerfile copies only the encoder and worker files; it does not package `.env`,
the database, CVs or application credentials. Weights are downloaded during the build,
then loaded from the image once per worker. Check the selected GPU supports the CUDA runtime
in the pinned PyTorch wheel. `MINILM_DEVICE=cpu` can be used to exercise the CPU path.

Create a **queue-based Serverless endpoint** in RunPod using that image. Start with
zero active workers and one maximum worker for the weekly batch workload; a warm
worker is optional if cold-start latency matters. RunPod resources are billed by RunPod.
No endpoint is created or billed by this code change.

For a local worker smoke test (with Docker and the built image available):

```bash
docker run --rm --gpus all YOUR_REGISTRY/adept-minilm:v1 --test_input '{"input":{"texts":["Human-AI collaboration design"]}}'
```

## Connect the existing pipeline

Export the values from this folder's `.env.example` in the process running the pipeline.
Do not put the key in `NEXT_PUBLIC_*`, commit it, or use the LLM endpoint setting: this
worker exposes RunPod's `/runsync` protocol, not an OpenAI chat endpoint.

```bash
export TRENDS_EMBEDDING_BACKEND=runpod
export TRENDS_RUNPOD_ENDPOINT_ID=YOUR_ENDPOINT_ID
export TRENDS_RUNPOD_API_KEY=YOUR_KEY
export PYTHONPATH=src/api:src
python -m pipelines.trends.embed_taxonomy
python -m pipelines.trends.run --dry-run
# When the dry run validates against your configured database:
python -m pipelines.trends.run
```

On PowerShell use `$env:NAME='value'` and `$env:PYTHONPATH='src/api;src'`.
Install the repository's ordinary pipeline dependencies on the caller. PyTorch and
sentence-transformers are needed only by the worker when using the RunPod backend.
For scheduled refreshes, put the same variables in the job's environment using repository
secrets; the workflow requires `TREND_DATABASE_URL` and `TRENDS_RUNPOD_API_KEY` repository secrets,
plus the `TRENDS_RUNPOD_ENDPOINT_ID` repository variable. It skips refresh when these are
missing rather than silently running a local model.

The client batches at most 64 texts, polls queued cold starts with a bounded deadline,
and verifies model revision, dimension, vector count and finite values. A failed remote
call stops ingestion before publication; it does not silently switch models or publish
partial trend estimates. Set `TRENDS_EMBEDDING_BACKEND=local` explicitly for local CPU development;
RunPod is the default backend. Re-embed taxonomy labels when changing model weights or revision.

## Six-stage pipeline

Public arXiv / catalogue → HTML cleaning and sentence splitting → 384-d MiniLM vectors
→ existing cosine matching and trend formula → vector checks, regression tests and
snapshot validation → PostgreSQL snapshots served by the existing API.

References: [RunPod handlers](https://docs.runpod.io/serverless/workers/handler-functions),
[container build](https://docs.runpod.io/serverless/workers/create-dockerfile),
[requests](https://docs.runpod.io/serverless/endpoints/send-requests),
[model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
