FROM python:3.11-slim
WORKDIR /workspace
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/src/api:/workspace/src
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/api src/api
COPY src/db src/db
COPY src/data/seed src/data/seed
COPY src/docker/boot.py src/docker/boot.py
RUN useradd --create-home adept
USER adept
EXPOSE 8000
CMD ["python", "src/docker/boot.py"]

