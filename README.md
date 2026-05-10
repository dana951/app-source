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

<details>
<summary><strong>Argo CD configuration for Jenkins access</strong></summary>

Configure Argo CD API access for Jenkins so pipelines can wait for **Application** sync and health. That confirms ephemeral preview environments are ready for tests and that staging and production deployments have synced successfully.

1. In argocd - create Service Account for jenkins:
- Edit the argocd-cm ConfigMap in your Kubernetes cluster
```bash
kubectl -n argocd edit configmap argocd-cm
```
- Add a user under the data section with apiKey permissions
```bash
data:
  accounts.jenkins: apiKey
```
2. Configure RBAC Permissions -
Give this new jenkins account the necessary permissions (like sync and get) by:
create a project role and bint it to jenkins account (in POC we use 'default' project)
- Edit the AppProject resource (in Argo CD, project-level roles are stored inside the AppProject)
```bash
kubectl edit appproject default -n argocd
```
- Add the Role to the AppProject. Find the spec section and add a roles block. It should look like this:
```bash
spec:
  # ... existing config ...
  roles:
  - name: jenkins-role
    description: Role for Jenkins CI/CD
    policies:
    - p, proj:default:jenkins-role, applications, get, *, allow
    - p, proj:default:jenkins-role, applications, sync, *, allow

```
Note: The proj:default:jenkins-role part is the standard format for project-scoped policies
- Bind the User (Jenkins account) to the Role - Now you must tell Argo CD that the jenkins account belongs to that specific project role. This is done in the global RBAC ConfigMap
```bash
kubectl edit cm argocd-rbac-cm -n argocd
```
- Update the policy.csv to include the group binding
```bash
data:
  policy.csv: |
    g, jenkins, proj:default:jenkins-role
```
3. Generate the Token
```bash
argocd account generate-token --account jenkins
```
4. Add the Token to Jenkins
- In Jenkins, go to Manage Jenkins > Credentials
- Add a new credential
```bash
Kind: Secret text
Secret: Paste the token you just generated
ID: argocd-token (This is what you'll use in your Jenkinsfile)
```

5. Build docker image with argocd cli (from alpine/k8s:1.35.4)
- Build the image (see Dockerfile.dev)
```bash
docker build -t devuser103/devtools:1.0.0 . -f Dockerfile.dev
docker push devuser103/devtools:1.0.0
docker run -it --rm devuser103/devtools:1.0.0 sh
argocd version
```

</details>

<details>
<summary><strong>Add Slack Notification to Jenkins</strong></summary>

Add Slack Notification to jenkins
1. Create a Slack App
Go to https://api.slack.com/apps and click "Create New App". Use this manifest:
```yaml
display_information:
  name: Jenkins
features:
  bot_user:
    display_name: Jenkins
    always_online: true
oauth_config:
  scopes:
    bot:
      - channels:read
      - chat:write
      - chat:write.customize
      - reactions:write
settings:
  org_deploy_enabled: false
  socket_mode_enabled: false
  token_rotation_enabled: false
```

2.  Install the app to your workspace and get the token
a. In your Slack app settings → OAuth & Permissions → Install to Workspace
b. opy the Bot User OAuth Token (starts with xoxb-)
c. In Slack, invite the Jenkins bot to your channel: /invite @Jenkins

3. Add the token to Jenkins credentials
Manage Jenkins → Credentials → System → Global Credentials → Add Credentials
```bash
Kind: Secret text
Secret: paste the xoxb- token
ID: slack-webhook-url
```
4. Configure Jenkins global Slack settings
Manage Jenkins → System → Slack
- Workspace: your Slack workspace name (e.g. your-company)
- Credential: select the secret text you just created
- Tick Custom slack app bot user
- Add default channel (e.g. #ci-cd)
- Click Test Connection - you should see a message in the channel
5. JCasC
- Add the slack plugin to controller.installPlugins 
- Below is how to add the slack configuration to JCasC section in jenkins helm values.yaml
```bash
credentials:
  system:
    domainCredentials:
      - credentials:
          - string:
              scope: GLOBAL
              id: slack-webhook-url
              secret: '${SLACK_TOKEN}'        # inject from env/secret
              description: Slack bot token

unclassified:
  slackNotifier:
    teamDomain: your-workspace-name
    tokenCredentialId: slack-webhook-url
    botUser: true
```    

</details>

<details>
<summary><strong>Extra reading - What is a Slack App?</strong></summary>
A Slack app is a programmatic identity that can interact with your Slack workspace - send messages, read channels, react to messages. Think of it as a service account, but for Slack.

### What is a Bot User
When you create a Slack app you can give it a bot user - this is the "face" of the app inside Slack. It has a name (e.g. "Jenkins") and an avatar. When Jenkins sends a message to Slack, it appears as if that bot user typed it, not you.
Without a bot user → no identity inside Slack, can't post messages.

### What is "Install to Workspace"
A Slack app is just a definition until you install it. Installing means:
> "I authorize this app to act inside my workspace"

At that point Slack generates an OAuth token (xoxb-...) - this is the app's password. Whoever holds this token can send messages to your workspace as the Jenkins bot.

### What is "Add to Channel"
Slack channels are private by default - even a bot can't post to a channel it hasn't been invited to. Adding the bot to a channel is exactly like typing:
```bash
/invite @Jenkins
```
in that channel. After that, the bot has permission to post there.

</details>

## License

See `LICENSE` in this repository.
