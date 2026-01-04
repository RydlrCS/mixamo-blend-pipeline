# Mixamo Blend Pipeline - Kubernetes README
# Guide for deploying pipeline to Kubernetes
#
# Author: Ted Iro
# Organization: Rydlr Cloud Services Ltd (github.com/rydlrcs)
# Date: January 4, 2026

# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the Mixamo Blend Pipeline to production.

## Prerequisites

- Kubernetes cluster (GKE, EKS, AKS, or self-managed)
- `kubectl` CLI configured with cluster access
- Container image built and pushed to registry
- Google Cloud credentials (service account or Workload Identity)

## Quick Start

```bash
# 1. Create namespace
kubectl apply -f k8s/namespace.yaml

# 2. Create ConfigMap
kubectl apply -f k8s/configmap.yaml

# 3. Create Secrets (see secret.yaml.template)
kubectl create secret generic pipeline-secrets \
  --from-literal=GCS_BUCKET=your-bucket \
  --from-literal=BQ_PROJECT=your-project \
  -n mixamo-pipeline

# 4. Deploy application
kubectl apply -f k8s/deployment.yaml

# 5. Create Service
kubectl apply -f k8s/service.yaml

# 6. Enable autoscaling (optional)
kubectl apply -f k8s/hpa.yaml

# 7. Verify deployment
kubectl get all -n mixamo-pipeline
```

## Files Overview

| File | Purpose |
|------|---------|
| `namespace.yaml` | Creates dedicated namespace for pipeline resources |
| `configmap.yaml` | Non-sensitive configuration (log level, timeouts, etc.) |
| `secret.yaml.template` | Template for sensitive configuration (credentials) |
| `deployment.yaml` | Main application deployment with worker pods |
| `service.yaml` | Service for load balancing and service discovery |
| `hpa.yaml` | Horizontal Pod Autoscaler for automatic scaling |
| `README.md` | This file - deployment documentation |

## Configuration

### Environment Variables

Configuration is split between ConfigMap (non-sensitive) and Secrets (sensitive):

**ConfigMap** (`configmap.yaml`):
- `LOG_LEVEL` - Logging verbosity (INFO, DEBUG, WARNING, ERROR)
- `BQ_DATASET` - BigQuery dataset name
- `UPLOAD_TIMEOUT_SECONDS` - GCS upload timeout
- `MAX_RETRIES` - Retry attempts for failed operations

**Secrets** (`pipeline-secrets`):
- `GCS_BUCKET` - Google Cloud Storage bucket name
- `BQ_PROJECT` - Google Cloud project ID
- `ELASTICSEARCH_URL` - Elasticsearch endpoint (optional)
- `ES_API_KEY` - Elasticsearch API key (optional)

### Creating Secrets

**Option 1: From literal values** (development/testing):
```bash
kubectl create secret generic pipeline-secrets \
  --from-literal=GCS_BUCKET=my-animations-bucket \
  --from-literal=BQ_PROJECT=my-gcp-project \
  --from-literal=ELASTICSEARCH_URL=https://my-cluster.es.cloud \
  --from-literal=ES_API_KEY=my-api-key \
  -n mixamo-pipeline
```

**Option 2: From env file** (recommended):
```bash
# Create .env.production with your values
cat > .env.production <<EOF
GCS_BUCKET=my-animations-bucket
BQ_PROJECT=my-gcp-project
ELASTICSEARCH_URL=https://my-cluster.es.cloud
ES_API_KEY=my-api-key
EOF

# Create secret from file
kubectl create secret generic pipeline-secrets \
  --from-env-file=.env.production \
  -n mixamo-pipeline

# Clean up env file
rm .env.production
```

**Option 3: External Secret Manager** (production):
```bash
# Use external-secrets-operator with Google Secret Manager
# See: https://external-secrets.io/latest/provider/google-secrets-manager/

# Install external-secrets operator
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace

# Create SecretStore and ExternalSecret (see advanced configuration)
```

## Deployment

### Standard Deployment

```bash
# Apply all manifests in order
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml

# Verify deployment
kubectl get pods -n mixamo-pipeline
kubectl get svc -n mixamo-pipeline
kubectl get hpa -n mixamo-pipeline
```

### Update Deployment

```bash
# Update configuration
kubectl apply -f k8s/configmap.yaml

# Trigger rolling update
kubectl rollout restart deployment/mixamo-pipeline -n mixamo-pipeline

# Monitor rollout
kubectl rollout status deployment/mixamo-pipeline -n mixamo-pipeline

# View rollout history
kubectl rollout history deployment/mixamo-pipeline -n mixamo-pipeline
```

### Rollback Deployment

```bash
# Rollback to previous version
kubectl rollout undo deployment/mixamo-pipeline -n mixamo-pipeline

# Rollback to specific revision
kubectl rollout undo deployment/mixamo-pipeline \
  -n mixamo-pipeline \
  --to-revision=2
```

## Scaling

### Manual Scaling

```bash
# Scale to 5 replicas
kubectl scale deployment mixamo-pipeline \
  --replicas=5 \
  -n mixamo-pipeline

# Verify scaling
kubectl get pods -n mixamo-pipeline
```

### Autoscaling

The HPA automatically scales based on CPU and memory:

```bash
# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Watch autoscaling in action
kubectl get hpa -n mixamo-pipeline -w

# Describe HPA for detailed metrics
kubectl describe hpa mixamo-pipeline-hpa -n mixamo-pipeline
```

## Monitoring

### Logs

```bash
# View logs from all pods
kubectl logs -n mixamo-pipeline -l app=mixamo-pipeline -f

# View logs from specific pod
kubectl logs -n mixamo-pipeline <pod-name> -f

# View previous container logs (if pod restarted)
kubectl logs -n mixamo-pipeline <pod-name> -p
```

### Pod Status

```bash
# Get pod status
kubectl get pods -n mixamo-pipeline

# Describe pod for detailed info
kubectl describe pod -n mixamo-pipeline <pod-name>

# Get pod events
kubectl get events -n mixamo-pipeline --sort-by='.lastTimestamp'
```

### Resource Usage

```bash
# View resource usage
kubectl top pods -n mixamo-pipeline
kubectl top nodes

# View resource requests/limits
kubectl describe pod -n mixamo-pipeline <pod-name> | grep -A 5 "Limits:"
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status and events
kubectl describe pod -n mixamo-pipeline <pod-name>

# Check logs
kubectl logs -n mixamo-pipeline <pod-name>

# Check if image pull failed
kubectl get pod -n mixamo-pipeline <pod-name> -o yaml | grep -A 5 "containerStatuses"
```

### Connection Issues

```bash
# Test service connectivity
kubectl run -n mixamo-pipeline test-pod \
  --image=curlimages/curl:latest \
  --rm -it -- sh

# Inside pod:
curl http://mixamo-pipeline:8080/health
```

### Secret Issues

```bash
# Verify secret exists
kubectl get secret -n mixamo-pipeline pipeline-secrets

# Describe secret (values are hidden)
kubectl describe secret -n mixamo-pipeline pipeline-secrets

# Decode secret values (for debugging)
kubectl get secret -n mixamo-pipeline pipeline-secrets -o jsonpath='{.data.GCS_BUCKET}' | base64 -d
```

## Security

### Workload Identity (GKE)

For GKE, use Workload Identity instead of service account keys:

```bash
# Create GCP service account
gcloud iam service-accounts create mixamo-pipeline \
  --display-name="Mixamo Pipeline"

# Grant permissions
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:mixamo-pipeline@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:mixamo-pipeline@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

# Create Kubernetes service account
kubectl create serviceaccount mixamo-pipeline-sa -n mixamo-pipeline

# Bind Kubernetes SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  mixamo-pipeline@PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:PROJECT_ID.svc.id.goog[mixamo-pipeline/mixamo-pipeline-sa]"

# Annotate Kubernetes service account
kubectl annotate serviceaccount mixamo-pipeline-sa \
  -n mixamo-pipeline \
  iam.gke.io/gcp-service-account=mixamo-pipeline@PROJECT_ID.iam.gserviceaccount.com

# Update deployment.yaml to use service account:
# spec.template.spec.serviceAccountName: mixamo-pipeline-sa
```

## Clean Up

```bash
# Delete all resources
kubectl delete -f k8s/hpa.yaml
kubectl delete -f k8s/service.yaml
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/configmap.yaml
kubectl delete secret -n mixamo-pipeline pipeline-secrets
kubectl delete -f k8s/namespace.yaml

# Or delete entire namespace
kubectl delete namespace mixamo-pipeline
```

## Advanced Configuration

### Network Policies

Add network policies to restrict pod communication:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mixamo-pipeline-netpol
  namespace: mixamo-pipeline
spec:
  podSelector:
    matchLabels:
      app: mixamo-pipeline
  policyTypes:
  - Egress
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53
  # Allow HTTPS to GCS/BigQuery
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
```

### Pod Disruption Budget

Ensure minimum availability during cluster maintenance:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: mixamo-pipeline-pdb
  namespace: mixamo-pipeline
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: mixamo-pipeline
```

## Support

For issues or questions:
- Email: ted@rydlrcloudservices.com
- GitHub: https://github.com/rydlrcs/mixamo-blend-pipeline
- Documentation: https://github.com/rydlrcs/mixamo-blend-pipeline/tree/main/docs
