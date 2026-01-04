# Production Deployment Guide

Comprehensive guide for deploying Mixamo Blend Pipeline to production data center environments.

**Author:** Ted Iro  
**Organization:** Rydlr Cloud Services Ltd (github.com/rydlrcs)  
**Date:** January 4, 2026

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Architecture](#architecture)
4. [Deployment Steps](#deployment-steps)
5. [Configuration](#configuration)
6. [Monitoring & Observability](#monitoring--observability)
7. [Security](#security)
8. [Operations](#operations)
9. [Troubleshooting](#troubleshooting)
10. [Disaster Recovery](#disaster-recovery)

---

## Overview

This guide covers production deployment of the Mixamo Blend Pipeline with:

- **Containerization**: Docker multi-stage builds with security hardening
- **Orchestration**: Kubernetes deployment with autoscaling
- **Observability**: Prometheus metrics, structured JSON logging, health checks
- **Resilience**: Retry logic, circuit breakers, graceful degradation
- **Security**: Non-root containers, secrets management, network policies

### Production-Readiness Checklist

✅ Containerization (Docker, docker-compose)  
✅ Kubernetes manifests (Deployment, Service, ConfigMap, HPA)  
✅ Health checks (liveness, readiness, startup probes)  
✅ Secrets management (Google Secret Manager, K8s Secrets)  
✅ Prometheus metrics & monitoring  
✅ Retry logic with exponential backoff  
✅ Circuit breaker pattern  
✅ Structured JSON logging with correlation IDs  
✅ Resource limits & quotas  
✅ Security hardening (non-root, read-only filesystem)

---

## Prerequisites

### Infrastructure Requirements

- **Kubernetes Cluster**: GKE, EKS, AKS, or self-managed (v1.24+)
- **Google Cloud Project**: With GCS and BigQuery enabled
- **Container Registry**: GCR, Docker Hub, or private registry
- **Metrics Server**: For horizontal pod autoscaling
- **Prometheus**: For metrics collection (optional but recommended)

### Tools Required

```bash
# Verify tool installations
kubectl version --client
docker --version
gcloud version  # For GCP deployments
helm version    # Optional, for Helm deployments
```

### Access Requirements

- Kubernetes cluster admin access (for initial setup)
- GCP project permissions:
  - `storage.admin` (for GCS bucket access)
  - `bigquery.dataEditor` (for BigQuery writes)
  - `secretmanager.secretAccessor` (if using Secret Manager)

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Load Balancer                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────────┐
│                  Kubernetes Service                          │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
┌───────▼──────┐ ┌──────▼─────┐ ┌──────▼─────┐
│  Pipeline    │ │  Pipeline  │ │  Pipeline  │
│  Worker 1    │ │  Worker 2  │ │  Worker 3  │
│  (Pod)       │ │  (Pod)     │ │  (Pod)     │
└──────┬───────┘ └──────┬─────┘ └──────┬─────┘
       │                │              │
       └────────┬───────┴──────┬───────┘
                │              │
      ┌─────────▼──┐    ┌──────▼──────┐
      │    GCS     │    │  BigQuery   │
      │  (Storage) │    │  (Metadata) │
      └────────────┘    └─────────────┘
```

### Data Flow

1. **Ingestion**: Animations downloaded from Mixamo (browser-based)
2. **Validation**: Files validated and organized in GCS seed/ folder
3. **Processing**: Blending operations performed by workers
4. **Storage**: Blended animations uploaded to GCS blend/ folder
5. **Metadata**: Animation metadata synced to BigQuery
6. **Consumption**: NPC engine retrieves blends from GCS

---

## Deployment Steps

### Step 1: Build Container Image

```bash
# Navigate to project root
cd /path/to/mixamo-blend-pipeline

# Build Docker image
docker build -t mixamo-blend-pipeline:v0.1.0 .

# Tag for registry
docker tag mixamo-blend-pipeline:v0.1.0 \
  gcr.io/YOUR_PROJECT_ID/mixamo-blend-pipeline:v0.1.0

# Push to registry
docker push gcr.io/YOUR_PROJECT_ID/mixamo-blend-pipeline:v0.1.0
```

### Step 2: Create Kubernetes Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

### Step 3: Configure Secrets

**Option A: Google Secret Manager (Recommended for production)**

```bash
# Create secrets in Google Secret Manager
echo -n "your-gcs-bucket-name" | gcloud secrets create GCS_BUCKET \
  --data-file=- \
  --replication-policy="automatic"

echo -n "your-project-id" | gcloud secrets create BQ_PROJECT \
  --data-file=- \
  --replication-policy="automatic"

# Grant access to Kubernetes service account (see Workload Identity setup)
```

**Option B: Kubernetes Secrets (Simpler, less secure)**

```bash
kubectl create secret generic pipeline-secrets \
  --from-literal=GCS_BUCKET=your-bucket-name \
  --from-literal=BQ_PROJECT=your-project-id \
  --from-literal=ELASTICSEARCH_URL=https://your-es-cluster \
  --from-literal=ES_API_KEY=your-api-key \
  -n mixamo-pipeline
```

### Step 4: Deploy Configuration

```bash
# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Verify
kubectl get configmap -n mixamo-pipeline pipeline-config -o yaml
```

### Step 5: Deploy Application

```bash
# Update deployment.yaml with your image
# Edit: spec.template.spec.containers[0].image

# Apply deployment
kubectl apply -f k8s/deployment.yaml

# Verify pods are running
kubectl get pods -n mixamo-pipeline
kubectl describe pod -n mixamo-pipeline <pod-name>
```

### Step 6: Create Service

```bash
kubectl apply -f k8s/service.yaml

# Verify service
kubectl get svc -n mixamo-pipeline
```

### Step 7: Enable Autoscaling

```bash
# Ensure metrics-server is installed
kubectl get deployment metrics-server -n kube-system

# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Verify autoscaler
kubectl get hpa -n mixamo-pipeline
```

### Step 8: Verify Deployment

```bash
# Check all resources
kubectl get all -n mixamo-pipeline

# Check pod logs
kubectl logs -n mixamo-pipeline -l app=mixamo-pipeline -f

# Test health endpoint
kubectl port-forward -n mixamo-pipeline svc/mixamo-pipeline 8080:8080
curl http://localhost:8080/health
```

---

## Configuration

### Environment Variables

Configuration is split between **ConfigMap** (non-sensitive) and **Secrets** (sensitive).

#### ConfigMap Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOG_FORMAT` | Log format (`text` or `json`) | `json` |
| `BQ_DATASET` | BigQuery dataset name | `RAW_DEV` |
| `UPLOAD_TIMEOUT_SECONDS` | GCS upload timeout | `300` |
| `MAX_RETRIES` | Retry attempts for failed operations | `3` |
| `RETRY_BACKOFF_MULTIPLIER` | Exponential backoff multiplier | `2.0` |
| `MAX_FILE_SIZE_MB` | Maximum file size for uploads | `500` |
| `WORKER_POOL_SIZE` | Number of concurrent workers | `4` |

#### Secret Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GCS_BUCKET` | Google Cloud Storage bucket name | Yes |
| `BQ_PROJECT` | Google Cloud project ID | Yes |
| `ELASTICSEARCH_URL` | Elasticsearch cluster URL | No |
| `ES_API_KEY` | Elasticsearch API key | No |

### Workload Identity Setup (GKE)

For production GKE deployments, use Workload Identity instead of service account keys:

```bash
# 1. Create GCP service account
gcloud iam service-accounts create mixamo-pipeline \
  --display-name="Mixamo Pipeline Service Account"

# 2. Grant GCS permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:mixamo-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.objectAdmin"

# 3. Grant BigQuery permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:mixamo-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/bigquery.dataEditor"

# 4. Create Kubernetes service account
kubectl create serviceaccount mixamo-pipeline-sa -n mixamo-pipeline

# 5. Bind K8s SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  mixamo-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:YOUR_PROJECT_ID.svc.id.goog[mixamo-pipeline/mixamo-pipeline-sa]"

# 6. Annotate K8s service account
kubectl annotate serviceaccount mixamo-pipeline-sa \
  -n mixamo-pipeline \
  iam.gke.io/gcp-service-account=mixamo-pipeline@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 7. Update deployment to use service account
# Edit k8s/deployment.yaml:
# spec.template.spec.serviceAccountName: mixamo-pipeline-sa
```

---

## Monitoring & Observability

### Prometheus Metrics

The pipeline exposes Prometheus metrics at `/metrics`:

```bash
# Port-forward to access metrics
kubectl port-forward -n mixamo-pipeline svc/mixamo-pipeline 9090:9090
curl http://localhost:9090/metrics
```

**Available Metrics:**

| Metric | Type | Description |
|--------|------|-------------|
| `blend_requests_total` | Counter | Total blend requests |
| `blend_duration_seconds` | Histogram | Blend operation latency |
| `upload_bytes_total` | Counter | Total bytes uploaded to GCS |
| `gcs_api_errors_total` | Counter | GCS API errors by type |
| `gcs_api_duration_seconds` | Histogram | GCS API call latency |
| `worker_pool_utilization` | Gauge | Worker pool utilization (0-1) |
| `queue_depth` | Gauge | Pending jobs in queue |

### Structured Logging

Logs are output in JSON format for aggregation:

```json
{
  "timestamp": "2026-01-04T10:30:15.123456Z",
  "level": "INFO",
  "logger": "src.uploader",
  "message": "Uploading file",
  "correlation_id": "req-abc-123",
  "source": {
    "file": "/app/src/uploader/uploader.py",
    "line": 250,
    "function": "upload_file"
  },
  "environment": {
    "hostname": "mixamo-pipeline-5f8b7c9d4-xz2kp",
    "pod_name": "mixamo-pipeline-5f8b7c9d4-xz2kp",
    "node_name": "gke-cluster-pool-1-node-3"
  },
  "extra": {
    "file_size": 102400,
    "destination": "blend/"
  }
}
```

**Log Collection:**

- **Cloud Logging**: Automatic for GKE clusters
- **ELK Stack**: Configure Fluentd/Filebeat to forward logs
- **Splunk**: Use Splunk Connect for Kubernetes

### Health Checks

Three health endpoints are available:

```bash
# Full health check (all components)
curl http://pipeline-service:8080/health

# Readiness check (critical components only)
curl http://pipeline-service:8080/ready

# Liveness check (basic functionality)
curl http://pipeline-service:8080/live
```

### Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
- name: mixamo_pipeline
  rules:
  - alert: HighErrorRate
    expr: |
      rate(gcs_api_errors_total[5m]) > 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High GCS API error rate"
      description: "GCS error rate is {{ $value }} per second"

  - alert: HighLatency
    expr: |
      histogram_quantile(0.95, rate(blend_duration_seconds_bucket[5m])) > 30
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High blend operation latency"
      description: "95th percentile latency is {{ $value }}s"

  - alert: PodCrashLooping
    expr: |
      rate(kube_pod_container_status_restarts_total{namespace="mixamo-pipeline"}[15m]) > 0
    labels:
      severity: critical
    annotations:
      summary: "Pod is crash looping"
      description: "Pod {{ $labels.pod }} is restarting frequently"
```

---

## Security

### Container Security

- ✅ **Non-root user**: Containers run as UID 1000
- ✅ **Read-only root filesystem**: Except mounted volumes
- ✅ **No privilege escalation**: `allowPrivilegeEscalation: false`
- ✅ **Capabilities dropped**: All capabilities removed, only essential added
- ✅ **Seccomp profile**: Runtime default seccomp profile

### Network Security

```yaml
# Example NetworkPolicy (create as k8s/network-policy.yaml)
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
  # Allow HTTPS (GCS, BigQuery, Elasticsearch)
  - ports:
    - protocol: TCP
      port: 443
```

### Secrets Management Best Practices

1. **Never commit secrets to git**
2. **Use Google Secret Manager** for production
3. **Enable encryption at rest** for Kubernetes secrets
4. **Rotate secrets regularly** (every 90 days)
5. **Use least-privilege access** principles
6. **Audit secret access** via Cloud Audit Logs

---

## Operations

### Scaling

**Manual Scaling:**
```bash
kubectl scale deployment mixamo-pipeline \
  --replicas=10 \
  -n mixamo-pipeline
```

**Autoscaling:**
HPA automatically scales based on CPU/memory (configured in `k8s/hpa.yaml`).

### Rolling Updates

```bash
# Update image
kubectl set image deployment/mixamo-pipeline \
  pipeline-worker=gcr.io/PROJECT_ID/mixamo-blend-pipeline:v0.2.0 \
  -n mixamo-pipeline

# Monitor rollout
kubectl rollout status deployment/mixamo-pipeline -n mixamo-pipeline

# Rollback if needed
kubectl rollout undo deployment/mixamo-pipeline -n mixamo-pipeline
```

### Maintenance Mode

```bash
# Scale down to zero
kubectl scale deployment mixamo-pipeline --replicas=0 -n mixamo-pipeline

# Perform maintenance...

# Scale back up
kubectl scale deployment mixamo-pipeline --replicas=3 -n mixamo-pipeline
```

---

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl get pods -n mixamo-pipeline

# Describe pod for events
kubectl describe pod -n mixamo-pipeline <pod-name>

# Check logs
kubectl logs -n mixamo-pipeline <pod-name>

# Common causes:
# - Image pull errors (check image name and registry access)
# - Missing secrets (check secret existence)
# - Resource constraints (check node capacity)
```

#### GCS Upload Failures

```bash
# Check service account permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:mixamo-pipeline*"

# Verify bucket access from pod
kubectl exec -n mixamo-pipeline <pod-name> -- \
  gsutil ls gs://your-bucket-name/

# Check circuit breaker status in metrics
curl http://localhost:9090/metrics | grep circuit
```

#### High Memory Usage

```bash
# Check resource usage
kubectl top pods -n mixamo-pipeline

# Check for memory leaks in logs
kubectl logs -n mixamo-pipeline <pod-name> | grep -i memory

# Increase memory limits in deployment.yaml if needed
```

---

## Disaster Recovery

### Backup Procedures

1. **GCS Versioning**: Enable on bucket for file recovery
   ```bash
   gsutil versioning set on gs://your-bucket-name
   ```

2. **BigQuery Snapshots**: Daily table snapshots
   ```bash
   bq cp YOUR_DATASET.animations \
     YOUR_DATASET.animations_backup_$(date +%Y%m%d)
   ```

3. **Configuration Backup**: Store in separate GCS bucket
   ```bash
   gsutil cp -r k8s/ gs://your-config-backup-bucket/
   ```

### Recovery Procedures

**Pod Failure:**
- Automatic restart via Kubernetes
- Check logs for root cause

**Node Failure:**
- Pods automatically rescheduled
- Verify with `kubectl get pods -n mixamo-pipeline -o wide`

**Data Loss:**
- Restore from GCS versioning
- Restore BigQuery snapshot

**Complete Cluster Failure:**
1. Provision new cluster
2. Restore configuration from backup
3. Redeploy using this guide
4. Verify data integrity

---

## Support

For issues or questions:

- **Email**: ted@rydlrcloudservices.com
- **GitHub**: https://github.com/rydlrcs/mixamo-blend-pipeline
- **Documentation**: https://github.com/rydlrcs/mixamo-blend-pipeline/tree/main/docs

---

**Document Version**: 1.0  
**Last Updated**: January 4, 2026  
**Author**: Ted Iro, Rydlr Cloud Services Ltd
