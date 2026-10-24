FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    HF_HOME=/opt/huggingface \
    MINILM_MODEL_PATH=/opt/minilm
WORKDIR /app
COPY src/pipelines/trends/runpod/requirements.txt /tmp/worker-requirements.txt
RUN pip install --no-cache-dir -r /tmp/worker-requirements.txt
COPY src/pipelines/trends/encoder.py /app/src/pipelines/trends/encoder.py
COPY src/pipelines/trends/runpod/ /app/src/pipelines/trends/runpod/
RUN python -c "from sentence_transformers import SentenceTransformer; from pipelines.trends.encoder import MODEL_ID, MODEL_REVISION; SentenceTransformer(MODEL_ID, revision=MODEL_REVISION, device='cpu', trust_remote_code=False).save('/opt/minilm')"
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
ENTRYPOINT ["python", "-u", "-m", "pipelines.trends.runpod.handler"]
