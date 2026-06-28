#!/usr/bin/env bash
set -euo pipefail

# EchoLoop Deployment Orchestrator
# Builds container remotely via Cloud Build and deploys Cloud Run via Terraform.

PROJECT_ID="echoloop-500808"
REGION="europe-west4"
STATE_BUCKET="echoloop-tf-state"
source .env

echo "=== 1. Setting target GCP project ==="
gcloud config set project "${PROJECT_ID}"

echo "=== 2. Verifying Google OAuth credentials ==="
if [[ -z "${GOOGLE_CLIENT_ID:-}" || -z "${GOOGLE_CLIENT_SECRET:-}" ]]; then
    echo "Error: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in your environment."
    echo "Please set them first before deploying."
    exit 1
fi

# Fallback: whitelist the active gcloud user email if ALLOWED_EMAILS is not configured
ACTIVE_USER=$(gcloud config get-value account 2>/dev/null || echo "")
EMAILS_WHITELIST="${ALLOWED_EMAILS:-$ACTIVE_USER}"
echo "Configured Allowed Emails: ${EMAILS_WHITELIST}"

echo "=== 3. Bootstrapping GCS state bucket if not exists ==="
if ! gcloud storage buckets describe "gs://${STATE_BUCKET}" &>/dev/null; then
    echo "Creating state bucket gs://${STATE_BUCKET}..."
    gcloud storage buckets create "gs://${STATE_BUCKET}" --location="${REGION}"
else
    echo "State bucket gs://${STATE_BUCKET} already exists."
fi

# Run Terraform commands relative to the terraform directory
cd terraform

echo "=== 4. Initializing Terraform ==="
terraform init -reconfigure

echo "=== 5. Bootstrapping Artifact Registry via Terraform ==="
# Deploy Repository and Services first to resolve chicken-and-egg dependency
terraform apply \
    -target=google_artifact_registry_repository.echoloop_repo \
    -auto-approve

echo "=== 6. Building and pushing Docker container via Cloud Build ==="
cd ..
# Submit build to Cloud Build targeting the created repository
gcloud builds submit --tag "${REGION}-docker.pkg.dev/${PROJECT_ID}/echoloop-repo/echoloop:latest" .

echo "=== 7. Applying full Terraform configuration ==="
cd terraform
terraform apply \
    -var="project_id=${PROJECT_ID}" \
    -var="region=${REGION}" \
    -var="google_client_id=${GOOGLE_CLIENT_ID}" \
    -var="google_client_secret=${GOOGLE_CLIENT_SECRET}" \
    -var="allowed_emails=${EMAILS_WHITELIST}" \
    -var="image_tag=latest" \
    -auto-approve

echo "=== 8. Deployment Successful ==="
# Extract the deployed Service URL from Terraform output
SERVICE_URL=$(terraform output -raw service_url 2>/dev/null || gcloud run services describe echoloop-ui --region="${REGION}" --format="value(status.url)")
echo "Your EchoLoop UI is accessible at: ${SERVICE_URL}"
