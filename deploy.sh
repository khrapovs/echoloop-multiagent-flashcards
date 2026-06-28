#!/usr/bin/env bash
set -euo pipefail

# EchoLoop Deployment Orchestrator
# Builds container remotely via Cloud Build and deploys Cloud Run via Terraform.

PROJECT_ID="echoloop-500808"
REGION="europe-west4"
STATE_BUCKET="echoloop-tf-state"

echo "=== 1. Setting target GCP project ==="
gcloud config set project "${PROJECT_ID}"

echo "=== 2. Resolving your public IP address for whitelisting ==="
# Retrieve public IP
CURRENT_IP=$(curl -s https://ifconfig.me)
echo "Resolved IP: ${CURRENT_IP}"

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
    -var="allowed_ips=${CURRENT_IP}" \
    -var="image_tag=latest" \
    -auto-approve

echo "=== 8. Deployment Successful ==="
# Extract the deployed Service URL from Terraform output
# Note: we should add an output resource in terraform
SERVICE_URL=$(terraform output -raw service_url 2>/dev/null || gcloud run services describe echoloop-ui --region="${REGION}" --format="value(status.url)")
echo "Your EchoLoop UI is accessible at: ${SERVICE_URL}"
