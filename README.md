# Hub community plugins

Plugins wrapped around a project that already exists on GitHub.
PhotoPrism is the first one. The application stays the upstream image.
This folder adds the CLI, the MCP server and the OpenAPI, then publishes
the image Hub downloads.

```
plugins/<id>/homelab-plugin.json          # official image and install image
plugins/<id>/docker-compose.backend.yml   # Hub installs this
plugins/<id>/openapi.yaml                 # REST API
plugins/<id>/src/cli/
plugins/<id>/src/mcp/
plugins/<id>/src/Dockerfile               # FROM the official image
plugins/<id>/src/publish.sh               # push the install image
```

Log in once with `docker login ghcr.io`, then run `src/publish.sh`.
Hub installs `ghcr.io/riccardograssi/<id>:hub`.
