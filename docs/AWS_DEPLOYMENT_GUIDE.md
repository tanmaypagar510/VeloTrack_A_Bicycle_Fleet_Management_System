# VeloTrack AWS Cloud Deployment Guide

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        AWS Cloud (us-east-1)                      │
├──────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                    VPC: 10.0.0.0/16                      │     │
│  │  ┌─────────────────┐  ┌─────────────────┐              │     │
│  │  │ Public Subnet    │  │ Public Subnet    │              │     │
│  │  │ 10.0.1.0/24     │  │ 10.0.2.0/24     │              │     │
│  │  │ (AZ-a)          │  │ (AZ-b)          │              │     │
│  │  │  ┌─── ALB ───┐  │  │                  │              │     │
│  │  │  │ Ingress   │  │  │                  │              │     │
│  │  └──┴───────────┴──┘  └──────────────────┘              │     │
│  │  ┌─────────────────┐  ┌─────────────────┐              │     │
│  │  │ Private Subnet   │  │ Private Subnet   │              │     │
│  │  │ 10.0.3.0/24     │  │ 10.0.4.0/24     │              │     │
│  │  │ (AZ-a)          │  │ (AZ-b)          │              │     │
│  │  │  ┌── EKS ──────────────────────────┐ │              │     │
│  │  │  │ ┌─────────┐ ┌─────────────────┐ │ │              │     │
│  │  │  │ │user-svc │ │bicycle-svc      │ │ │              │     │
│  │  │  │ │(1-3pods)│ │(1-3pods)        │ │ │              │     │
│  │  │  │ ├─────────┤ ├─────────────────┤ │ │              │     │
│  │  │  │ │maint-svc│ │assistant-svc    │ │ │              │     │
│  │  │  │ │(1-3pods)│ │(1-3pods)        │ │ │              │     │
│  │  │  │ ├─────────┤ ├─────────────────┤ │ │              │     │
│  │  │  │ │RabbitMQ │ │PostgreSQL       │ │ │              │     │
│  │  │  │ └─────────┘ └─────────────────┘ │ │              │     │
│  │  │  └─────────────────────────────────┘ │              │     │
│  │  └──────────────────┘  └──────────────────┘              │     │
│  │  ┌─────────────────┐  ┌─────────────────┐              │     │
│  │  │ DB Subnet        │  │ DB Subnet        │              │     │
│  │  │ 10.0.5.0/24     │  │ 10.0.6.0/24     │              │     │
│  │  │ (AZ-a)          │  │ (AZ-b)          │              │     │
│  │  │  [RDS optional]  │  │                  │              │     │
│  │  └──────────────────┘  └──────────────────┘              │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                    │
│  ┌──── S3 ────┐  ┌── CloudWatch ──┐  ┌──── ECR ────┐           │
│  │ Frontend   │  │ Logs & Alerts  │  │ Private     │           │
│  │ ML Models  │  │ Dashboards     │  │ Registry    │           │
│  └────────────┘  └────────────────┘  └─────────────┘           │
└──────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

- AWS CLI installed and configured (`aws configure`)
- `kubectl` installed
- `eksctl` installed
- Docker installed
- Your Docker Hub images already pushed (`tanmaypagar510/velotrack-*`)

---

## Step-by-Step Deployment

### Step 1: Create ECR Private Repositories (Private Container Registry)

```bash
aws ecr create-repository --repository-name velotrack-user-service --region us-east-1
aws ecr create-repository --repository-name velotrack-bicycle-service --region us-east-1
aws ecr create-repository --repository-name velotrack-maintenance-rental-service --region us-east-1
aws ecr create-repository --repository-name velotrack-maintenance-assistant-service --region us-east-1
aws ecr create-repository --repository-name velotrack-frontend --region us-east-1
```

### Step 2: Push Images to ECR (Private Registry)

```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Tag and push each image
for svc in user-service bicycle-service maintenance-rental-service maintenance-assistant-service frontend; do
  docker tag tanmaypagar510/velotrack-${svc}:latest <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-${svc}:latest
  docker push <YOUR_AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-${svc}:latest
done
```

### Step 3: Create EKS Cluster

```bash
eksctl create cluster \
  --name velotrack-cluster \
  --region us-east-1 \
  --version 1.29 \
  --nodegroup-name velotrack-nodes \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed \
  --with-oidc
```

This creates:
- VPC with proper subnets (public + private)
- EKS cluster with managed node group
- IAM roles with least privilege
- Security groups

### Step 4: Configure kubectl

```bash
aws eks update-kubeconfig --name velotrack-cluster --region us-east-1
kubectl get nodes   # Verify connection
```

### Step 5: Install NGINX Ingress Controller

```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/aws/deploy.yaml
```

### Step 6: Install Metrics Server (for HPA)

```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Step 7: Deploy VeloTrack to EKS

```bash
cd infra/k8s

# Replace placeholder with your AWS Account ID
export AWS_ACCOUNT_ID=<YOUR_AWS_ACCOUNT_ID>
export REGION=us-east-1

# Sed replace in all YAML files
find . -name '*.yaml' -exec sed -i "s|<DOCKERHUB_USERNAME>|${AWS_ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com|g" {} \;

# Deploy in order
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f network-policies.yaml
kubectl apply -f postgres.yaml
kubectl apply -f rabbitmq.yaml

# Wait for DB to be ready
kubectl -n velotrack rollout status deployment/postgres --timeout=120s
kubectl -n velotrack rollout status deployment/rabbitmq --timeout=120s

# Deploy backend services
kubectl apply -f user-service.yaml
kubectl apply -f bicycle-service.yaml
kubectl apply -f maintenance-rental-service.yaml
kubectl apply -f maintenance-assistant-service.yaml

# Deploy frontend and ingress
kubectl apply -f frontend.yaml
kubectl apply -f ingress.yaml
```

### Step 8: Verify Deployment

```bash
# Check all pods are running
kubectl -n velotrack get pods

# Check services
kubectl -n velotrack get services

# Check HPA
kubectl -n velotrack get hpa

# Check ingress (get external URL)
kubectl -n velotrack get ingress

# Check logs
kubectl -n velotrack logs -l app=user-service --tail=20
kubectl -n velotrack logs -l app=bicycle-service --tail=20
```

### Step 9: Get Application URL

```bash
# Get the Load Balancer URL
kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### Step 10: Create S3 Bucket for Frontend & Models

```bash
# Create S3 bucket for ML model artifacts
aws s3 mb s3://velotrack-models-$(aws sts get-caller-identity --query Account --output text)

# Upload model artifacts (if any)
aws s3 cp data/models/ s3://velotrack-models-$(aws sts get-caller-identity --query Account --output text)/models/ --recursive
```

### Step 11: Setup CloudWatch Logging

```bash
# Install CloudWatch agent on EKS
kubectl apply -f infra/aws/cloudwatch-namespace.yaml
kubectl apply -f infra/aws/cloudwatch-agent.yaml
```

### Step 12: Create CloudWatch Alarms

```bash
# Create alarm for high CPU (triggers when >80% for 5 min)
aws cloudwatch put-metric-alarm \
  --alarm-name "VeloTrack-HighCPU" \
  --alarm-description "EKS Node CPU above 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# Create alarm for pod restart count
aws cloudwatch put-metric-alarm \
  --alarm-name "VeloTrack-PodRestarts" \
  --alarm-description "Pod restarts detected" \
  --metric-name pod_cpu_utilization \
  --namespace ContainerInsights \
  --statistic Average \
  --period 300 \
  --threshold 90 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

---

## Important kubectl Commands (for Demo Recording)

```bash
# Show running pods
kubectl -n velotrack get pods -o wide

# Show deployments
kubectl -n velotrack get deployments

# Show services
kubectl -n velotrack get svc

# Show configmaps
kubectl -n velotrack get configmap velotrack-config -o yaml

# Show secrets (keys only)
kubectl -n velotrack get secret velotrack-secrets -o yaml

# Show HPA status
kubectl -n velotrack get hpa

# View backend service logs
kubectl -n velotrack logs -l app=user-service --tail=50
kubectl -n velotrack logs -l app=maintenance-rental-service --tail=50

# Manually scale a deployment
kubectl -n velotrack scale deployment/bicycle-service --replicas=3

# See the scaling happen
kubectl -n velotrack get pods -w

# Scale back
kubectl -n velotrack scale deployment/bicycle-service --replicas=1

# Get public IP of exposed services
kubectl get svc -n ingress-nginx
kubectl -n velotrack get ingress

# Describe a pod (show node, IP, events)
kubectl -n velotrack describe pod -l app=user-service

# Network policies
kubectl -n velotrack get networkpolicies
```

---

## Cost Optimization (Free Tier / Low Cost)

| Service | Free Tier / Cost |
|---------|-----------------|
| EKS Cluster | $0.10/hr (~$72/mo) |
| EC2 t3.medium x2 | ~$60/mo (or use spot instances for ~$20/mo) |
| S3 | 5GB free |
| ECR | 500MB free private storage |
| CloudWatch | 5GB logs free |
| **Total** | **~$80-130/mo** (can reduce with spot instances) |

**Tip:** For demo purposes, you can create the cluster, record the demo, then delete:
```bash
eksctl delete cluster --name velotrack-cluster --region us-east-1
```

