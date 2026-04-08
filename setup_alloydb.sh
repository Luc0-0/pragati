#!/bin/bash
# PRAGATI - AlloyDB Setup Script
# Creates cluster, instance, database, and applies schema
# Usage: bash setup_alloydb.sh YOUR_PROJECT_ID

set -e

PROJECT_ID=${1:-$(gcloud config get-value project)}
REGION="us-central1"
CLUSTER_ID="pragati-cluster"
INSTANCE_ID="pragati-primary"
DB_NAME="pragati"
DB_PASS="PragatiDB@2024"  # Change this!

echo "Setting up AlloyDB for PRAGATI..."

# Set project
gcloud config set project $PROJECT_ID

# Enable AlloyDB API
gcloud services enable alloydb.googleapis.com

# Create AlloyDB cluster
echo "Creating AlloyDB cluster..."
gcloud alloydb clusters create $CLUSTER_ID \
  --region=$REGION \
  --password=$DB_PASS \
  --project=$PROJECT_ID

# Create primary instance
echo "Creating AlloyDB instance (takes ~5 min)..."
gcloud alloydb instances create $INSTANCE_ID \
  --cluster=$CLUSTER_ID \
  --region=$REGION \
  --instance-type=PRIMARY \
  --cpu-count=2 \
  --project=$PROJECT_ID

# Get private IP
ALLOYDB_IP=$(gcloud alloydb instances describe $INSTANCE_ID \
  --cluster=$CLUSTER_ID \
  --region=$REGION \
  --format='value(ipAddress)' \
  --project=$PROJECT_ID)

echo "AlloyDB IP: $ALLOYDB_IP"

# Save to .env
cat > .env << EOF
GCP_PROJECT=$PROJECT_ID
GCP_LOCATION=$REGION
ALLOYDB_HOST=$ALLOYDB_IP
ALLOYDB_PORT=5432
ALLOYDB_DB=$DB_NAME
ALLOYDB_USER=postgres
ALLOYDB_PASS=$DB_PASS
ALLOYDB_INSTANCE=projects/$PROJECT_ID/locations/$REGION/clusters/$CLUSTER_ID/instances/$INSTANCE_ID
EOF

echo ""
echo "AlloyDB setup complete!"
echo "Next: Connect to AlloyDB and run:"
echo "  psql -h $ALLOYDB_IP -U postgres -c 'CREATE DATABASE $DB_NAME;'"
echo "  psql -h $ALLOYDB_IP -U postgres -d $DB_NAME -f db/schema.sql"
echo "  python db/seed_data.py"
