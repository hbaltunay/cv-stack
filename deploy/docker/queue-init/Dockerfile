FROM python:3.13.11-slim

RUN apt-get update && \
    apt-get upgrade -y --no-install-recommends && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN groupadd --gid 1001 queue && \
    useradd --uid 1001 --gid queue \
            --shell /bin/false \
            queue && \
    mkdir -p /home/queue && \
    chown queue:queue /home/queue

WORKDIR /queue

RUN chown queue:queue /queue

USER queue

COPY pyproject.toml ./

RUN pip install --no-cache-dir .
