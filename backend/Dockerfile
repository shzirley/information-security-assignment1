FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 veltrix

WORKDIR /app
COPY requirements.txt constraints-tested.txt ./
RUN python -m pip install -r requirements.txt

COPY app ./app
COPY kyc ./kyc
COPY migrations ./migrations
COPY fixtures ./fixtures
COPY scripts/start_cloud.py scripts/cloud_manage.py ./scripts/
COPY alembic.ini manage.py ./

USER veltrix
EXPOSE 10000
CMD ["python", "scripts/start_cloud.py"]
