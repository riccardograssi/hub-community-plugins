ARG OFFICIAL_IMAGE=photoprism/photoprism:latest
FROM ${OFFICIAL_IMAGE}

USER root
RUN if ! command -v python3 >/dev/null 2>&1; then \
      (apt-get update && apt-get install -y --no-install-recommends python3 && rm -rf /var/lib/apt/lists/*) \
      || (apk add --no-cache python3); \
    fi
COPY src/cli /opt/opendevtools/cli
COPY src/mcp /opt/opendevtools/mcp
COPY openapi.yaml /opt/opendevtools/openapi.yaml
COPY src/sso.json /opt/opendevtools/sso.json
RUN chmod 0755 /opt/opendevtools/cli/plugin_cli.py /opt/opendevtools/mcp/server.py \
 && ln -sf /opt/opendevtools/cli/plugin_cli.py /usr/local/bin/plugin-cli \
 && ln -sf /opt/opendevtools/mcp/server.py /usr/local/bin/plugin-mcp
ENV HUB_SSO=1 \
    HUB_SSO_PATH=/api/auth/sso \
    PLUGIN_NAME=photoprism \
    PLUGIN_API_BASE=http://127.0.0.1:2342 \
    PLUGIN_HEALTH_PATH=/api/v1/status
