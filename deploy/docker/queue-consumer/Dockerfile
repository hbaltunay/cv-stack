FROM python:3.13.11-slim

RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN groupadd --gid 1001 app && \
    useradd --uid 1001 --gid app \
            --shell /bin/false \
            app && \
    mkdir -p /home/app && \
    chown app:app /home/app

WORKDIR /app

RUN chown app:app /app

COPY --chown=app:app ./app ./app

USER app

COPY pyproject.toml ./

RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app

# ENTRYPOINT ["python3", "app/main.py"]
