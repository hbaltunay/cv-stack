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

ENV HOME=/home/app

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/home/app/.local/bin:$PATH"
ENV PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml ./

RUN uv sync --no-cache