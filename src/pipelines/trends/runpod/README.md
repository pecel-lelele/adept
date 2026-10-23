# MiniLM on RunPod Serverless

The deployed queue-based endpoint is https://api.runpod.ai/v2/ta14jd0by2ijl2, using the
public image `ghcr.io/pecel-lelele/adept-minilm:latest`. A live test on 24 October
2026 completed with two 384-dimensional vectors. Follow
[deployment and operations](DEPLOYMENT_HANDOFF.md) for build, credentials, recovery,
Replit production setup and publication acceptance.

## Worker contract

- Model: `sentence-transformers/all-MiniLM-L6-v2`.
- Pinned revision: `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.
- Protocol: authenticated RunPod `POST /runsync`, polling `GET /status/<job_id>`.
- API routes: `POST /run`, `POST /runsync`, `GET /status/<job_id>` and `GET /health` at
  the endpoint URL above.
- Input: `input.texts`, 1–64 non-empty strings of at most 4,096 characters each.
- Output: model, revision, dimensions and normalized 384-dimensional embeddings.
- Data: public research sentences and catalogue labels; no CVs or private identities.

The client validates model/revision, vector count, dimensions and finite non-zero values.
Remote failures stop the refresh; there is no implicit fallback to GLM credentials or local
inference. Existing cosine threshold 0.55, trend formulas and publication rules are unchanged.

## Execution boundaries

[Publish MiniLM](../../../../.github/workflows/publish-minilm.yml) is manual-dispatch only
from the trusted `main` branch. It is separate from
[Trends refresh](../../../../.github/workflows/trends-refresh.yml), which runs the batch
pipeline on Mondays and manual dispatch. Only the RunPod worker installs PyTorch and model
weights; the GitHub pipeline runner installs ordinary client dependencies. The image loads
weights offline from `/opt/minilm` and preserves the Dockerfile entrypoint.

Replit's API serves stored snapshots; app requests do not start MiniLM inference.
Use zero active workers and one maximum worker for batch work. The request smoke test is
independent of database publication: the first integrated refresh failed on Replit's private
development hostname `helium`. Use a reachable production connection for Actions.
Preflight now checks database access before any ingestion or inference.

The [pipeline configuration example](.env.example) lists the process variables. GitHub's
database secret is named `TREND_DATABASE_URL`, mapped to `DATABASE_URL` at runtime;
the endpoint ID is a repository variable and its dedicated API key is a repository secret.
Export these for local runs; sentence-transformers is only needed on the caller when
explicitly selecting `TRENDS_EMBEDDING_BACKEND=local`.

## Six-stage pipeline

Public arXiv / catalogue → HTML cleaning and sentence splitting → 384-dimensional vectors
→ cosine mention matching and existing trend formula → vector checks and snapshot validation
→ atomic PostgreSQL publication read by the API. Re-embed taxonomy labels when changing
model weights or revision.

References: [RunPod requests](https://docs.runpod.io/serverless/endpoints/send-requests),
[container build](https://docs.runpod.io/serverless/workers/create-dockerfile),
[model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
