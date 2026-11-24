# Isolated, non-root sandbox image for executing agent-modified code & tests.
# Build:
#   docker build -f docker/sandbox.Dockerfile -t pr-crew-sandbox .
# Run safely (no network, limited CPU/RAM):
#   docker run --rm --network=none --memory=512m --cpus=1 \
#     -v "$(pwd)/target_repo:/workspace" pr-crew-sandbox pytest -v

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir pytest==8.3.3 ruff==0.7.0

RUN useradd --create-home --shell /bin/bash agent
WORKDIR /workspace
RUN chown agent:agent /workspace

USER agent
ENV PYTHONPATH=/workspace/src
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["pytest", "-v"]
