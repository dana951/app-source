// WHAT THIS PIPELINE DOES:
//   Promotes a Docker image through environments: DEV → QA → STAGING → PROD
//   Each environment follows the same pattern:
//     1. Update gitops-manifests (ArgoCD picks this up and deploys)
//     2. Wait for the deployment to become healthy
//     3. Run E2E tests against the live deployment
//     4. If tests pass → promote to next environment
//   PROD requires a human approval gate before deployment.
//
// TRIGGERED BY:
//   GitHub Actions self-hosted runner via Jenkins Remote Access API:
//   POST /job/podinfo-deploy/buildWithParameters
//   Parameters: IMAGE_TAG, IMAGE_URI, GIT_SHA, GIT_BRANCH, TRIGGERED_BY
//
// POD AGENT STRATEGY:
//   Runs on ephemeral Kubernetes pod agents (Jenkins Kubernetes plugin).
//   Each build gets a fresh pod — no state leaks between builds.
//   The pod has two containers:
//     - tools: kubectl, helm, awscli, git (for gitops updates + ArgoCD CLI)
//     - python: for running E2E tests

@Library('jenkins-shared-lib') _

pipeline {

    agent {
        kubernetes {
            label "podinfo-deploy-${env.BUILD_NUMBER}"
            yaml """
apiVersion: v1
kind: Pod
spec:
  serviceAccountName: jenkins-agent
  containers:

    # tools container: AWS CLI + ArgoCD CLI + git
    # Used for: ECR verification, gitops-manifests update, ArgoCD sync
    - name: tools
      image: alpine/k8s:1.33.11
      command: [cat]
      tty: true
      resources:
        requests:
          cpu: 200m
          memory: 256Mi

    # python container: runs the E2E test suite
    # Kept separate from tools — each container has minimal dependencies
    - name: python
      image: python:3.11-slim
      command: [cat]
      tty: true
      resources:
        requests:
          cpu: 200m
          memory: 256Mi
  nodeSelector:
    workload/node-group: jenkins-agents
"""
        }
    }

    // ── Parameters ────────────────────────────────────────────────────────────
    // Passed by GitHub Actions when triggering this job.
    // Also fillable manually from Jenkins UI.
    parameters {
        string(
            name: 'IMAGE_TAG',
            description: 'Short git SHA used as the Docker image tag (e.g. abc1234). ' +
                         'This tag must already exist in ECR before this job runs.'
        )
        string(
            name: 'IMAGE_URI',
            description: 'Full ECR image URI (e.g. 123456789.dkr.ecr.us-east-1.amazonaws.com/podinfo:abc1234)'
        )
        string(
            name: 'GIT_SHA',
            description: 'Full git commit SHA from the app-source repo (for audit trail)'
        )
        string(
            name: 'GIT_BRANCH',
            defaultValue: 'main',
            description: 'Source branch (should always be main for automated deploys)'
        )
        string(
            name: 'TRIGGERED_BY',
            defaultValue: 'manual',
            description: 'GitHub username who triggered the pipeline (for audit trail)'
        )
        choice(
            name: 'TARGET_ENV',
            choices: ['dev', 'qa', 'staging', 'prod'],
            description: 'Environment to START deployment from. ' +
                         'dev = full promotion pipeline (DEV→QA→STAGING→PROD). ' +
                         'staging = start from staging (useful for hotfixes). ' +
                         'prod = deploy directly to prod (break-glass only).'
        )
        booleanParam(
            name: 'SKIP_E2E',
            defaultValue: false,
            description: 'Skip E2E tests on all environments. ' +
                         'BREAK-GLASS USE ONLY — document the reason in the build description.'
        )
        booleanParam(
            name: 'SKIP_PROD_APPROVAL',
            defaultValue: false,
            description: 'Skip the human approval gate before PROD. ' +
                         'BREAK-GLASS USE ONLY — requires devops-lead Jenkins permission.'
        )
    }

    // ── Environment Variables ─────────────────────────────────────────────────
    environment {
        AWS_REGION        = 'us-east-1'
        ECR_REGISTRY      = '123456789.dkr.ecr.us-east-1.amazonaws.com'   // ECR registry
        ECR_REPOSITORY    = 'podinfo'

        // GitOps repo — ArgoCD watches this for changes
        GITOPS_REPO       = 'git@github.com:dana951/gitops-manifests.git' // gitops repo
        GITOPS_BRANCH     = 'main'

        APP_NAME          = 'podinfo'

        // In-cluster DNS URLs per environment namespace.
        // Only reachable from inside the EKS cluster —
        DEV_APP_URL       = 'http://podinfo.dev.svc.cluster.local:8080'
        QA_APP_URL        = 'http://podinfo.qa.svc.cluster.local:8080'
        STAGING_APP_URL   = 'http://podinfo.staging.svc.cluster.local:8080'
        PROD_APP_URL      = 'http://podinfo.prod.svc.cluster.local:8080'

        // Jenkins credential IDs (configured in Jenkins → Manage Credentials)
        GIT_CREDS_ID      = 'github-gitops-ssh-key'
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '30'))
        // Full promotion pipeline (4 envs + E2E on each) can take 30-40 minutes
        timeout(time: 60, unit: 'MINUTES')
        timestamps()
        // Prevent concurrent deploys — two simultaneous promotions would race
        // on the gitops-manifests repo and cause git push conflicts
        disableConcurrentBuilds()
        ansiColor('xterm')
    }

    stages {

        // ── Stage 1: Validate ─────────────────────────────────────────────────
        // Fail immediately with a clear message if required parameters are missing.
        stage('Validate Parameters') {
            steps {
                script {
                    if (!params.IMAGE_TAG) {
                        error('IMAGE_TAG is required. Was this job triggered correctly by GitHub Actions?')
                    }
                    if (!params.IMAGE_URI) {
                        error('IMAGE_URI is required.')
                    }
                    if (!params.GIT_SHA) {
                        error('GIT_SHA is required.')
                    }

                    // Set the Jenkins build display name
                    currentBuild.displayName  = "#${env.BUILD_NUMBER} | ${params.IMAGE_TAG}"
                    currentBuild.description  = "By: ${params.TRIGGERED_BY} | Branch: ${params.GIT_BRANCH}"

                    echo """
                    PODINFO DEPLOYMENT PIPELINE
                    Image Tag:      ${params.IMAGE_TAG}
                    Git SHA:        ${params.GIT_SHA}
                    Git Branch:     ${params.GIT_BRANCH}
                    Triggered by:   ${params.TRIGGERED_BY}
                    Start env:      ${params.TARGET_ENV}
                    Skip E2E:       ${params.SKIP_E2E}
                    Skip Approval:  ${params.SKIP_PROD_APPROVAL}
                    """
                }
            }
        }

        // ── Stage 2: Verify Image in ECR ─────────────────────────────────────
        // Confirm the image tag exists in ECR before touching any environment.
        // Uses dockerUtils from the shared library.
        stage('Verify Image in ECR') {
            steps {
                container('tools') {
                    script {
                        dockerUtils.verifyImageInECR(
                            env.ECR_REGISTRY,
                            env.ECR_REPOSITORY,
                            params.IMAGE_TAG,
                            env.AWS_REGION
                        )
                    }
                }
            }
        }

        // ── Stage 3: Deploy to DEV ────────────────────────────────────────────
        // First environment in the promotion pipeline.
        // Skipped if TARGET_ENV is qa, staging, or prod — this allows
        // a hotfix to be deployed starting from a later environment.
        stage('Deploy → DEV') {
            when {
                expression { params.TARGET_ENV == 'dev' }
            }
            steps {
                container('tools') {
                    script {
                        deployToEnvironment(
                            environment:    'dev',
                            valuesFilePath: 'apps/podinfo/dev/values.yaml',
                            imageTag:       params.IMAGE_TAG,
                            gitopsRepo:     env.GITOPS_REPO,
                            gitCredentialsId: env.GIT_CREDS_ID,
                            appName:        env.APP_NAME
                        )
                    }
                }
            }
        }

        // ── Stage 4: E2E Tests on DEV ─────────────────────────────────────────
        // Full E2E suite (smoke + api journey tests).
        // If any test fails, pipeline stops — broken image is not promoted to QA.
        stage('E2E Tests → DEV') {
            when {
                allOf {
                    expression { params.TARGET_ENV == 'dev' }
                    expression { !params.SKIP_E2E }
                }
            }
            steps {
                container('python') {
                    script {
                        runE2ETests(
                            environment:     'dev',
                            appUrl:          env.DEV_APP_URL,
                            expectedVersion: params.IMAGE_TAG,
                            markers:         'smoke or e2e'
                        )
                    }
                }
            }
        }

        // ── Stage 5: Deploy to QA ─────────────────────────────────────────────
        stage('Deploy → QA') {
            when {
                expression { params.TARGET_ENV in ['dev', 'qa'] }
            }
            steps {
                container('tools') {
                    script {
                        deployToEnvironment(
                            environment:    'qa',
                            valuesFilePath: 'apps/podinfo/qa/values.yaml',
                            imageTag:       params.IMAGE_TAG,
                            gitopsRepo:     env.GITOPS_REPO,
                            gitCredentialsId: env.GIT_CREDS_ID,
                            appName:        env.APP_NAME
                        )
                    }
                }
            }
        }

        // ── Stage 6: E2E Tests on QA ─────────────────────────────────────────
        stage('E2E Tests → QA') {
            when {
                allOf {
                    expression { params.TARGET_ENV in ['dev', 'qa'] }
                    expression { !params.SKIP_E2E }
                }
            }
            steps {
                container('python') {
                    script {
                        runE2ETests(
                            environment:     'qa',
                            appUrl:          env.QA_APP_URL,
                            expectedVersion: params.IMAGE_TAG,
                            markers:         'smoke or e2e'
                        )
                    }
                }
            }
        }

        // ── Stage 7: Deploy to STAGING ────────────────────────────────────────
        // Staging is production-like — same resource limits, same config shape.
        // Passing E2E here is the final automated gate before prod.
        stage('Deploy → STAGING') {
            when {
                expression { params.TARGET_ENV in ['dev', 'qa', 'staging'] }
            }
            steps {
                container('tools') {
                    script {
                        deployToEnvironment(
                            environment:    'staging',
                            valuesFilePath: 'apps/podinfo/staging/values.yaml',
                            imageTag:       params.IMAGE_TAG,
                            gitopsRepo:     env.GITOPS_REPO,
                            gitCredentialsId: env.GIT_CREDS_ID,
                            appName:        env.APP_NAME
                        )
                    }
                }
            }
        }

        // ── Stage 8: E2E Tests on STAGING ────────────────────────────────────
        stage('E2E Tests → STAGING') {
            when {
                allOf {
                    expression { params.TARGET_ENV in ['dev', 'qa', 'staging'] }
                    expression { !params.SKIP_E2E }
                }
            }
            steps {
                container('python') {
                    script {
                        runE2ETests(
                            environment:     'staging',
                            appUrl:          env.STAGING_APP_URL,
                            expectedVersion: params.IMAGE_TAG,
                            markers:         'smoke or e2e'
                        )
                    }
                }
            }
        }

        // ── Stage 9: Human Approval Gate ─────────────────────────────────────
        // Pauses the pipeline and waits for a human to approve the PROD deploy.
        //   submitter: 'devops-leads' — only specific users can approve,
        //   timeout 24h: auto-aborts if nobody approves within 24 hours.
        //     Prevents the pipeline from blocking an executor indefinitely.
        //   SKIP_PROD_APPROVAL: break-glass param for genuine emergencies.
        stage('Approval: Deploy to PROD') {
            when {
                expression { !params.SKIP_PROD_APPROVAL }
            }
            steps {
                script {
                    echo "Waiting for human approval before deploying to PROD..."

                    timeout(time: 24, unit: 'HOURS') {
                        input(
                            message: """Deploy to PRODUCTION?

Image Tag:    ${params.IMAGE_TAG}
Git SHA:      ${params.GIT_SHA}
Triggered by: ${params.TRIGGERED_BY}

Promotion status:
  DEV     ✅ deployed + E2E passed
  QA      ✅ deployed + E2E passed
  STAGING ✅ deployed + E2E passed

Approve to deploy to PROD.""",
                            ok: 'Approve — Deploy to PROD',
                            submitter: 'devops-leads'
                        )
                    }
                }
            }
        }

        // ── Stage 10: Deploy to PROD ──────────────────────────────────────────
        stage('Deploy → PROD') {
            steps {
                container('tools') {
                    script {
                        deployToEnvironment(
                            environment:    'prod',
                            valuesFilePath: 'apps/podinfo/prod/values.yaml',
                            imageTag:       params.IMAGE_TAG,
                            gitopsRepo:     env.GITOPS_REPO,
                            gitCredentialsId: env.GIT_CREDS_ID,
                            appName:        env.APP_NAME
                        )
                    }
                }
            }
        }

        // ── Stage 11: Smoke Tests on PROD ────────────────────────────────────
        // On PROD: smoke marker only — no full E2E suite.
        // Smoke tests are read-only and have no side effects.
        stage('Smoke Tests → PROD') {
            when {
                expression { !params.SKIP_E2E }
            }
            steps {
                container('python') {
                    script {
                        runE2ETests(
                            environment:     'prod',
                            appUrl:          env.PROD_APP_URL,
                            expectedVersion: params.IMAGE_TAG,
                            markers:         'smoke'
                        )
                    }
                }
            }
        }

    }

    // ── Post-build ────────────────────────────────────────────────────────────
    post {
        success {
            script {
                notifyUtils.deploymentSuccess(
                    appName:     env.APP_NAME,
                    imageTag:    params.IMAGE_TAG,
                    version:     params.IMAGE_TAG,
                    environment: 'prod',
                    buildUrl:    env.BUILD_URL
                )
            }
        }
        failure {
            script {
                notifyUtils.deploymentFailure(
                    appName:  env.APP_NAME,
                    stage:    env.STAGE_NAME ?: 'unknown',
                    buildUrl: env.BUILD_URL
                )
            }
        }
        always {
            cleanWs()
        }
    }

}