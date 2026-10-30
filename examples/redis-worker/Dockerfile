# Reference worker image. Build context is the repository root so the
# RaceTrace SDK can be installed from source:
#   docker build -f examples/redis-worker/Dockerfile .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY sdk/python /src/sdk
COPY examples/redis-worker /src/refworker
RUN pip install --no-cache-dir /src/sdk /src/refworker && rm -rf /src

USER nobody
ENTRYPOINT ["python", "-m", "refworker"]
CMD ["work"]
