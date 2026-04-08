#!/bin/bash
# PRAGATI - One-command Cloud Run deployment
# Usage: bash deploy.sh YOUR_PROJECT_ID

set -e

PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION="us-central1"
SERVICE_NAME="pragati"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "Deploying PRAGATI to Cloud Run..."
echo "Project: $PROJECT_ID | Region: $REGION"

# Enable required APIs
echo "Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  alloydb.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  --project=$PROJECT_ID

# Build and push Docker image
echo "Building Docker image..."
gcloud builds submit --tag $IMAGE --project=$PROJECT_ID

# Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --region $REGION \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "GCP_PROJECT=${PROJECT_ID},GCP_LOCATION=${REGION}" \
  --project=$PROJECT_ID

echo ""
echo "PRAGATI deployed successfully!"
echo "URL: $(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)' --project=$PROJECT_ID)"
