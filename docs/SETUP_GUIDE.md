# VeloTrack – Complete Setup & Deployment Guide

## Table of Contents
1. [Local Development (Docker Compose)](#1-local-development-docker-compose)
2. [AWS Cloud Setup](#2-aws-cloud-setup)
3. [Kubernetes Deployment (EKS)](#3-kubernetes-deployment-eks)
4. [CI/CD Pipeline Setup](#4-cicd-pipeline-setup)
5. [Verification & Testing](#5-verification--testing)
6. [Demo Recording Checklist](#6-demo-recording-checklist)

---

## 1. Local Development (Docker Compose)

### Step 1.1: Install Prerequisites
1. Install **Docker Desktop**: https://www.docker.com/products/docker-desktop
2. Install **Git**: https://git-scm.com/downloads
3. Ensure Docker Desktop is running

### Step 1.2: Clone & Configure
```bash
git clone https://github.com/<your-username>/VeloTrack_A_Bicycle_Fleet_Management_System.git
cd VeloTrack_A_Bicycle_Fleet_Management_System
```

The `.env` file is already configured with defaults.

### Step 1.3: Build & Start All Services
```bash
docker-compose up --build -d
```

This starts:
- PostgreSQL (port 5432)
- RabbitMQ (ports 5672, 15672)
- Ollama LLM (port 11434)
- User Service (port 5001)
- Bicycle Service (port 5002)
- Maintenance Rental Service (port 5003)
- Maintenance Assistant Service (port 5004)
- Frontend (port 3000)
- NGINX API Gateway (port 8080)

### Step 1.4: Pull Ollama Model
```bash
docker exec velotrack-ollama ollama pull mistral
```

### Step 1.5: Verify All Services
```bash
docker-compose ps
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
curl http://localhost:5004/health
```

### Step 1.6: Access Application
- Open browser: http://localhost:8080
- Register a new account
- Start managing bicycles!

---

## 2. AWS Cloud Setup

### Step 2.1: AWS Prerequisites
- AWS Account (Free Tier eligible)
- AWS CLI installed: https://aws.amazon.com/cli/
- kubectl installed: https://kubernetes.io/docs/tasks/tools/

### Step 2.2: Configure AWS CLI
```bash
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### Step 2.3: Create VPC & Network (Network Segregation)
```bash
# Create VPC
aws ec2 create-vpc --cidr-block 10.0.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=velotrack-vpc}]'

# Note the VPC ID from output, then create subnets:

# Public Subnet (for ALB/NAT)
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=velotrack-public-1}]'

# Private Subnet 1 (for EKS nodes)
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.10.0/24 --availability-zone us-east-1a --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=velotrack-private-1}]'

# Private Subnet 2 (for RDS)
aws ec2 create-subnet --vpc-id <VPC_ID> --cidr-block 10.0.20.0/24 --availability-zone us-east-1b --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=velotrack-private-2}]'
```

### Step 2.4: Create Security Groups
```bash
# EKS Node Security Group
aws ec2 create-security-group --group-name velotrack-eks-sg --description "EKS Node SG" --vpc-id <VPC_ID>

# RDS Security Group (allow 5432 from EKS only)
aws ec2 create-security-group --group-name velotrack-rds-sg --description "RDS SG" --vpc-id <VPC_ID>
aws ec2 authorize-security-group-ingress --group-id <RDS_SG_ID> --protocol tcp --port 5432 --source-group <EKS_SG_ID>
```

### Step 2.5: Create ECR Repositories (Private Container Registry)
```bash
aws ecr create-repository --repository-name velotrack-user-service --region us-east-1
aws ecr create-repository --repository-name velotrack-bicycle-service --region us-east-1
aws ecr create-repository --repository-name velotrack-maintenance-rental-service --region us-east-1
aws ecr create-repository --repository-name velotrack-maintenance-assistant-service --region us-east-1
aws ecr create-repository --repository-name velotrack-frontend --region us-east-1
```

### Step 2.6: Build & Push Docker Images to ECR
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build and push each service
# User Service
docker build -t velotrack-user-service ./backend/user-service
docker tag velotrack-user-service:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-user-service:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-user-service:latest

# Bicycle Service
docker build -t velotrack-bicycle-service ./backend/bicycle-service
docker tag velotrack-bicycle-service:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-bicycle-service:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-bicycle-service:latest

# Maintenance Rental Service
docker build -t velotrack-maintenance-rental-service ./backend/maintenance-rental-service
docker tag velotrack-maintenance-rental-service:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-rental-service:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-rental-service:latest

# Maintenance Assistant Service
docker build -t velotrack-maintenance-assistant-service ./backend/maintenance-assistant-service
docker tag velotrack-maintenance-assistant-service:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-assistant-service:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-assistant-service:latest

# Frontend
docker build -t velotrack-frontend ./frontend
docker tag velotrack-frontend:latest <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-frontend:latest
docker push <AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/velotrack-frontend:latest
```

### Step 2.7: Create RDS PostgreSQL (Optional – can use K8s PostgreSQL)
```bash
aws rds create-db-instance \
  --db-instance-identifier velotrack-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15 \
  --master-username velotrack \
  --master-user-password velotrack_secret \
  --allocated-storage 20 \
  --vpc-security-group-ids <RDS_SG_ID> \
  --db-subnet-group-name velotrack-db-subnet-group \
  --no-publicly-accessible
```

---

## 3. Kubernetes Deployment (EKS)

### Step 3.1: Create EKS Cluster
```bash
# Install eksctl
# Windows: choco install eksctl
# Mac: brew install eksctl

eksctl create cluster \
  --name velotrack-cluster \
  --region us-east-1 \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed
```

### Step 3.2: Configure kubectl
```bash
aws eks update-kubeconfig --name velotrack-cluster --region us-east-1
kubectl get nodes  # Verify cluster access
```

### Step 3.3: Update Image References
Edit the K8s YAML files to replace placeholders with your actual AWS account ID:
```bash
# On Linux/Mac:
find infra/k8s -name '*.yaml' -exec sed -i 's/<AWS_ACCOUNT_ID>/YOUR_ACCOUNT_ID/g' {} \;
find infra/k8s -name '*.yaml' -exec sed -i 's/<REGION>/us-east-1/g' {} \;

# On Windows PowerShell:
Get-ChildItem -Path infra/k8s -Filter *.yaml | ForEach-Object {
    (Get-Content $_.FullName) -replace '<AWS_ACCOUNT_ID>', 'YOUR_ACCOUNT_ID' -replace '<REGION>', 'us-east-1' | Set-Content $_.FullName
}
```

### Step 3.4: Deploy to Kubernetes
```bash
# 1. Create namespace
kubectl apply -f infra/k8s/namespace.yaml

# 2. Apply ConfigMap and Secrets
kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -f infra/k8s/secrets.yaml

# 3. Deploy infrastructure
kubectl apply -f infra/k8s/postgres.yaml
kubectl apply -f infra/k8s/rabbitmq.yaml

# Wait for infrastructure
kubectl -n velotrack rollout status deployment/postgres
kubectl -n velotrack rollout status deployment/rabbitmq

# 4. Deploy backend services
kubectl apply -f infra/k8s/user-service.yaml
kubectl apply -f infra/k8s/bicycle-service.yaml
kubectl apply -f infra/k8s/maintenance-rental-service.yaml
kubectl apply -f infra/k8s/maintenance-assistant-service.yaml

# 5. Deploy frontend
kubectl apply -f infra/k8s/frontend.yaml
```

### Step 3.5: Expose Frontend (LoadBalancer)
```bash
# Change frontend service type to LoadBalancer for external access
kubectl -n velotrack patch svc frontend -p '{"spec":{"type":"LoadBalancer"}}'

# Get external IP
kubectl -n velotrack get svc frontend
```

### Step 3.6: Verify Deployment
```bash
# Check all resources
kubectl -n velotrack get pods
kubectl -n velotrack get services
kubectl -n velotrack get deployments
kubectl -n velotrack get hpa
kubectl -n velotrack get configmaps
kubectl -n velotrack get secrets

# Check logs
kubectl -n velotrack logs -f deployment/user-service
kubectl -n velotrack logs -f deployment/bicycle-service

# Scale manually
kubectl -n velotrack scale deployment/user-service --replicas=3
kubectl -n velotrack get pods  # Verify scaling

# Scale back
kubectl -n velotrack scale deployment/user-service --replicas=1
```

---

## 4. CI/CD Pipeline Setup

### Step 4.1: Push Code to GitHub
```bash
git init  (if not already)
git add .
git commit -m "VeloTrack - Complete bicycle fleet management system"
git remote add origin https://github.com/<your-username>/VeloTrack_A_Bicycle_Fleet_Management_System.git
git push -u origin main
```

### Step 4.2: Configure GitHub Secrets
Go to your GitHub repo → Settings → Secrets and variables → Actions → New repository secret:

| Secret Name | Value |
|---|---|
| `AWS_ACCESS_KEY_ID` | Your AWS IAM access key |
| `AWS_SECRET_ACCESS_KEY` | Your AWS IAM secret key |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS account number |

### Step 4.3: Trigger CI/CD
Push any change to `main` branch → GitHub Actions will automatically:
1. Build Docker images for all 5 services
2. Push to ECR (private registry)
3. Deploy to EKS cluster

### Step 4.4: Monitor Pipeline
Go to GitHub → Actions tab → Watch the pipeline run

---

## 5. Verification & Testing

### Test Complete User Flow
```bash
# 1. Register a user
curl -X POST http://localhost:8080/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@velotrack.com","password":"admin123","full_name":"Admin User","role":"admin"}'

# Save the token from response
export TOKEN="<token_from_response>"

# 2. Add a bicycle
curl -X POST http://localhost:8080/api/bicycles/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"bike_code":"BIKE-042","make":"Trek","model":"FX 3","year":2024,"color":"Blue","condition":"Good"}'

# 3. Checkout bicycle
curl -X POST http://localhost:8080/api/rentals/checkout \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"bicycle_id":1,"renter_name":"Jane Doe"}'

# 4. Return bicycle
curl -X POST http://localhost:8080/api/rentals/return/1 \
  -H "Authorization: Bearer $TOKEN"

# 5. Create maintenance log
curl -X POST http://localhost:8080/api/maintenance/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"bicycle_id":1,"problem_description":"Brake pads worn","work_done":"Replaced brake pads","technician":"John","cost":45.50}'

# 6. Ask the AI assistant
curl -X POST http://localhost:8080/api/maintenance-assistant/ask \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"bike_id":1,"question":"Does bike #42 need servicing?"}'

# 7. Get risk scores
curl http://localhost:8080/api/risk-scores/ \
  -H "Authorization: Bearer $TOKEN"
```

---

## 6. Demo Recording Checklist

Use this checklist when recording your 5-10 min demo video:

### Application Demo
- [ ] Open browser showing the application URL
- [ ] Login with credentials
- [ ] Show dashboard with fleet overview and risk alerts
- [ ] Navigate to Bicycles page, show list with risk badges
- [ ] Click "Add Bicycle" and register a new bike
- [ ] Create a rental checkout
- [ ] Return the bike
- [ ] Create a maintenance log
- [ ] Show bicycle history (maintenance + rental)
- [ ] Click "Why this score?" on a risk badge
- [ ] Navigate to Assistant, ask "Does bike #42 need servicing?"
- [ ] Show the AI response with source records

### AWS Console Walkthrough
- [ ] Show AWS console with account name visible (top right)
- [ ] Navigate to ECR → Show pushed container images
- [ ] Navigate to EKS → Show cluster details
- [ ] Navigate to RDS → Show database (if using RDS)
- [ ] Navigate to VPC → Show network configuration
- [ ] Navigate to CloudWatch → Show logs

### kubectl Commands
- [ ] `kubectl -n velotrack get pods`
- [ ] `kubectl -n velotrack get deployments`
- [ ] `kubectl -n velotrack get services`
- [ ] `kubectl -n velotrack get hpa`
- [ ] `kubectl -n velotrack get configmaps`
- [ ] `kubectl -n velotrack get secrets`
- [ ] `kubectl -n velotrack logs deployment/user-service` (show logs)
- [ ] `kubectl -n velotrack scale deployment/user-service --replicas=3` (manual scaling)
- [ ] `kubectl -n velotrack get pods` (verify scaled pods)
- [ ] `kubectl -n velotrack get svc` (show public IPs)

