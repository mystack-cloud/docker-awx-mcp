# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.title="docker-awx-mcp"
LABEL org.opencontainers.image.description="AWX / Ansible Automation Platform MCP server (stdio + HTTP)"
LABEL org.opencontainers.image.source="https://github.com/mystack-cloud/docker-awx-mcp"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ARG AWX_MCP_VERSION=1.2.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Defaults for mystack test AWX; override at runtime
    AWX_PLATFORM=awx \
    AWX_VERIFY_SSL=true \
    LOG_LEVEL=info

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin awxmcp

RUN uv pip install --system "awx-mcp-server==${AWX_MCP_VERSION}" \
    && uv cache clean

COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh

USER awxmcp
WORKDIR /home/awxmcp

EXPOSE 8000

# STDIO MCP is the default (Cursor / Claude). Override with MODE=http for remote.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
