# podinfo

WIP - Application source code with a full CI Jenkins pipeline driving a GitOps deployment workflow

Lightweight [FastAPI](https://fastapi.tiangolo.com/) service that exposes process metadata (hostname, platform, version, git SHA), a small HTML dashboard, health checks, and an echo endpoint.

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/)

## Run locally

```bash
cd app-source
uv sync
uv run podinfo
```

Open [http://localhost:8080](http://localhost:8080).

After you change dependencies, run `uv sync` and commit `uv.lock`.

## Docker

**Build** (optional: bake version and Git SHA into the image):

```bash
docker build \
  --build-arg APP_VERSION=1.2.3 \
  --build-arg GIT_SHA=$(git rev-parse HEAD) \
  -t podinfo:latest .
```

**Run** (set environment and theme as needed):

```bash
docker run --rm -p 8080:8080 \
  -e APP_ENV=prod \
  -e THEME_COLOR=yellow \
  podinfo:latest
```

The app listens on port **8080**. You can override any variable at runtime with `-e`.

## Endpoints

| Method | Path | Notes |
|--------|------|--------|
| GET | `/` | Dashboard |
| GET | `/health` | `{"status": "ok"}` |
| GET | `/version` | Version and git SHA |
| GET | `/info` | Hostname, platform, environment, theme |
| GET | `/echo?message=…` | Echo with UTC timestamp |

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `APP_VERSION` | `unknown` | Version label |
| `GIT_SHA` | `unknown` | Git commit |
| `APP_ENV` | `dev` | Environment name |
| `THEME_COLOR` | `blue` | Dashboard background |

## License

See `LICENSE` in this repository.
