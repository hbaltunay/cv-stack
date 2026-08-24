FROM nvcr.io/nvidia/tritonserver:24.06-py3

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1001 triton && \
    useradd --uid 1001 --gid triton \
            --shell /bin/false \
            --no-create-home \
            triton

RUN mkdir -p /model_repository /opt/tritonserver/logs && \
    chown -R triton:triton /model_repository /opt/tritonserver/logs && \
    chmod 755 /model_repository && \
    chmod 700 /opt/tritonserver/logs

USER triton

EXPOSE 8000 8001 8002    
