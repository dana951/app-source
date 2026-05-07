# podinfo

Application source code with a CI/CD GitHub Actions + Jenkins pipelines driving a GitOps deployment workflow


This repository is part of the [**eks-gitops-platform**](https://github.com/dana951/eks-gitops-platform) project - GitOps CI/CD workflow on AWS EKS. 

> For a full platform test drive, fork/clone all repositories listed in [`project repositories`](https://github.com/dana951/eks-gitops-platform#project-repositories) into your own GitHub account, then update configs to point to your clones.

## What This Repo Delivers

- Lightweight [FastAPI](https://fastapi.tiangolo.com/) service exposing process metadata (hostname, platform, version, git SHA), a small HTML dashboard, health checks, and an echo endpoint.
- CI/CD workflow using GitHub Actions for build/validation and Jenkins for environment-based testing and promotion orchestration.

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


## Configurations

<details>
<summary><strong>Credentials - Jenkins GitHub App authentication</strong></summary>

Use a GitHub App for Jenkins authentication to GitHub.

Prerequisite:
- Install the [GitHub Branch Source](https://plugins.jenkins.io/github-branch-source/) plugin (typically via JCasC).

Setup steps:
1. Create a GitHub App for Jenkins.
2. Configure repository permissions:
   - Contents: Read and write
   - Pull requests: Read and write
   - Metadata: Read-only (required)
3. Install the app on your clone of the [`gitops-manifests`](https://github.com/dana951/gitops-manifests) repository.
4. Download the GitHub App private key (`.pem`) and copy the App ID.
5. Convert the private key for Jenkins:

```bash
openssl pkcs8 -topk8 -nocrypt -in downloaded-key.pem
```

6. In Jenkins, go to `Manage Jenkins` -> `Credentials` -> `GitHub App`, then add the App ID and converted key.

</details>

<details>
<summary><strong>Runtime - Self-hosted GitHub runners on Kubernetes (ARC)</strong></summary>

In this platform, GitHub Actions workflows trigger Jenkins, and Jenkins runs inside the EKS cluster.  
Using self-hosted GitHub runners in the same Kubernetes environment provides direct, reliable connectivity to Jenkins and other internal cluster services.

It also enables secure access to private AWS resources through IRSA, so workflows can use short-lived IAM credentials.

For full setup steps, see [Setup of self-hosted GitHub runners on Kubernetes (ARC)](https://github.com/dana951/eks-gitops-platform#appendix-setup-of-self-hosted-github-runners-on-kubernetes-arc).

</details>

## License

See `LICENSE` in this repository.
