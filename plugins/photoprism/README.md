# PhotoPrism

Wrapped from the existing project https://github.com/photoprism/photoprism.
The official image is `photoprism/photoprism:latest`.

`src/Dockerfile` starts from that image and copies in the CLI, the MCP server
and `openapi.yaml`. It does not replace the PhotoPrism command. The REST API
is the one PhotoPrism already serves. Swagger for the status call is the
OpenAPI file in this folder.

Inside the container:

```
plugin-cli health
plugin-mcp
```

`src/publish.sh` builds `ghcr.io/riccardograssi/photoprism:hub` and pushes it.
Hub installs that tag. Set `PHOTOPRISM_ADMIN_PASSWORD` on the site before install.
