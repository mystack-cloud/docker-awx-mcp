# syntax=docker/dockerfile:1
FROM python:3.12-slim

LABEL org.opencontainers.image.title="docker-awx-mcp"
LABEL org.opencontainers.image.description="AWX / Ansible Automation Platform MCP server (stdio + HTTP + restricted HTTP)"
LABEL org.opencontainers.image.source="https://github.com/mystack-cloud/docker-awx-mcp"
LABEL org.opencontainers.image.licenses="Apache-2.0"

ARG AWX_MCP_VERSION=1.2.0
# awx-mcp-server still uses Server.list_tools (mcp 1.x). mcp 2.x breaks HTTP mode.
ARG MCP_VERSION_CONSTRAINT='mcp>=1.0.0,<2'

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Defaults for mystack test AWX; override at runtime
    AWX_PLATFORM=awx \
    AWX_VERIFY_SSL=true \
    LOG_LEVEL=info \
    AWX_MCP_POLICY_FILE=/etc/awx-mcp/policy.yaml

COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /usr/local/bin/uv

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 --shell /usr/sbin/nologin awxmcp

RUN uv pip install --system "awx-mcp-server==${AWX_MCP_VERSION}" "${MCP_VERSION_CONSTRAINT}" pyyaml \
    && uv cache clean

COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
COPY restricted /opt/awx-mcp-restricted/restricted
COPY policy.default.yaml /opt/awx-mcp-restricted/policy.default.yaml
# Default policy path used when no ConfigMap is mounted
RUN mkdir -p /etc/awx-mcp \
    && cp /opt/awx-mcp-restricted/policy.default.yaml /etc/awx-mcp/policy.yaml \
    && chown -R awxmcp:awxmcp /etc/awx-mcp /opt/awx-mcp-restricted

ENV PYTHONPATH=/opt/awx-mcp-restricted

USER awxmcp
WORKDIR /home/awxmcp

EXPOSE 8000

# STDIO MCP is the default (Cursor / Claude). Override with MODE=http or http-restricted.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD []
