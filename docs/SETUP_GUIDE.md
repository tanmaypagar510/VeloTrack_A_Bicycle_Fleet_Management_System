# VeloTrack – Complete Setup & Deployment Guide

> **Last Updated:** June 14, 2026
> **Author:** Tanmay Pagar
> **Repository:** https://github.com/tanmaypagar510/VeloTrack_A_Bicycle_Fleet_Management_System

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Local Development Setup (Docker Compose)](#2-local-development-setup-docker-compose)
3. [Push Code to GitHub](#3-push-code-to-github)
4. [Push Docker Images to Docker Hub](#4-push-docker-images-to-docker-hub)
5. [AWS Account Setup & IAM Configuration](#5-aws-account-setup--iam-configuration)
6. [Install AWS CLI, eksctl & kubectl](#6-install-aws-cli-eksctl--kubectl)
7. [Create ECR Private Repositories](#7-create-ecr-private-repositories)
8. [Push Images to ECR (Private Registry)](#8-push-images-to-ecr-private-registry)
9. [Create EKS Cluster](#9-create-eks-cluster)
10. [Install Metrics Server & NGINX Ingress Controller](#10-install-metrics-server--nginx-ingress-controller)
11. [Fix EBS CSI Driver (for PersistentVolumeClaim)](#11-fix-ebs-csi-driver-for-persistentvolumeclaim)
12. [Deploy VeloTrack to Kubernetes (EKS)](#12-deploy-velotrack-to-kubernetes-eks)
13. [Verify Deployment & Get Application URL](#13-verify-deployment--get-application-url)
14. [CI/CD Pipeline (GitHub Actions)](#14-cicd-pipeline-github-actions)
15. [API Testing with Postman](#15-api-testing-with-postman)
16. [Demo Recording Checklist](#16-demo-recording-checklist)
17. [Cleanup — Stop AWS Billing](#17-cleanup--stop-aws-billing)
18. [Cost Breakdown](#18-cost-breakdown)

---

## 1. Prerequisites

Install these tools on your machine:

| Tool | Purpose | Install Link |
|------|---------|-------------|
| Docker Desktop | Run containers locally | https://www.docker.com/products/docker-desktop |
| Git | Version control | https://git-scm.com/downloads |
| WSL (Windows) | Linux environment for Docker/AWS | Pre-installed on Windows 10/11 |
| Node.js 20 | Frontend build | https://nodejs.org |
| Postman | API testing | https://www.postman.com/downloads |

---

## 2. Local Development Setup (Docker Compose)

### Step 2.1: Clone the Repository
```bash
git clone https://github.com/tanmaypagar510/VeloTrack_A_Bicycle_Fleet_Management_System.git
cd VeloTrack_A_Bicycle_Fleet_Management_System
```

### Step 2.2: Verify .env File
The `.env` file is already configured with defaults:
```
POSTGRES_USER=velotrack
POSTGRES_PASSWORD=velotrack_secret
DATABASE_URL=postgresql://velotrack:velotrack_secret@postgres:5432/velotrack
JWT_SECRET=supersecretjwtkey123changeinproduction
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=tinyllama
```

### Step 2.3: Build & Start All Services
```bash
docker-compose up --build -d
```

This starts **9 containers**:

| Container | Port | Description |
|-----------|------|-------------|
| velotrack-postgres | 5432 | PostgreSQL database |
| velotrack-rabbitmq | 5672, 15672 | Message broker (RabbitMQ) |
| velotrack-ollama | 11434 | AI/LLM model server |
| velotrack-user-service | 5001 | User auth microservice |
| velotrack-bicycle-service | 5002 | Bicycle CRUD microservice |
| velotrack-maintenance-rental-service | 5003 | Maintenance & rentals microservice |
| velotrack-maintenance-assistant-service | 5004 | AI assistant + risk scoring microservice |
| velotrack-frontend | 3000 | SvelteKit frontend |
| velotrack-nginx | 8080 | NGINX API gateway |

### Step 2.4: Pull AI Model for Assistant
```bash
docker exec velotrack-ollama ollama pull tinyllama
```
> This downloads the TinyLlama model (~637MB). The AI assistant will not work without this step.

### Step 2.5: Verify All Services Are Running
```bash
docker-compose ps
```
All 9 containers should show `Up` status.

### Step 2.6: Access the Application
- **Application:** http://localhost:8080
- **RabbitMQ Dashboard:** http://localhost:15672 (guest/guest)

### Step 2.7: Restart Without Losing Data
```bash
# Stop (data preserved)
docker-compose down

# Restart (data preserved)
docker-compose up --build -d
```

> ⚠️ **Never** use `docker-compose down -v` unless you want to **delete all data**.

---

## 3. Push Code to GitHub

### Step 3.1: Create GitHub Repository
1. Go to https://github.com → Click **"+"** → **"New repository"**
2. Name: `VeloTrack_A_Bicycle_Fleet_Management_System`
3. Visibility: **Public**
4. Do NOT add README/.gitignore (already exist)
5. Click **"Create repository"**

### Step 3.2: Push Code
```bash
git init
git add .
git commit -m "feat: Complete VeloTrack Bicycle Fleet Management System"
git branch -M main
git remote add origin https://github.com/tanmaypagar510/VeloTrack_A_Bicycle_Fleet_Management_System.git
git push -u origin main
```

---

## 4. Push Docker Images to Docker Hub

### Step 4.1: Login to Docker Hub
```bash
docker login -u tanmaypagar510
```

### Step 4.2: Tag and Push All Images
```bash
docker tag velotrack_a_bicycle_fleet_management_system_user-service:latest tanmaypagar510/velotrack-user-service:latest
docker push tanmaypagar510/velotrack-user-service:latest

docker tag velotrack_a_bicycle_fleet_management_system_bicycle-service:latest tanmaypagar510/velotrack-bicycle-service:latest
docker push tanmaypagar510/velotrack-bicycle-service:latest

docker tag velotrack_a_bicycle_fleet_management_system_maintenance-rental-service:latest tanmaypagar510/velotrack-maintenance-rental-service:latest
docker push tanmaypagar510/velotrack-maintenance-rental-service:latest

docker tag velotrack_a_bicycle_fleet_management_system_maintenance-assistant-service:latest tanmaypagar510/velotrack-maintenance-assistant-service:latest
docker push tanmaypagar510/velotrack-maintenance-assistant-service:latest

docker tag velotrack_a_bicycle_fleet_management_system_frontend:latest tanmaypagar510/velotrack-frontend:latest
docker push tanmaypagar510/velotrack-frontend:latest
```

### Step 4.3: Verify on Docker Hub
Visit: https://hub.docker.com/u/tanmaypagar510
> You should see 5 repositories: `velotrack-user-service`, `velotrack-bicycle-service`, `velotrack-maintenance-rental-service`, `velotrack-maintenance-assistant-service`, `velotrack-frontend`

---

## 5. AWS Account Setup & IAM Configuration

### Step 5.1: Find Your AWS Account ID
1. Login to **AWS Console** → Click your **username** (top-right corner)
2. Copy the **12-digit Account ID** (e.g., `123456789012`)

### Step 5.2: Create IAM User (Principle of Least Privilege)
1. AWS Console → Search **"IAM"** → Click **IAM**
2. Left sidebar → **"Users"** → **"Create user"**
3. User name: `velotrack-cicd`
4. Click **Next**
5. Select **"Attach policies directly"**
6. Search and tick: ✅ `AdministratorAccess`
7. Click **Next** → **"Create user"**

### Step 5.3: Create Access Keys
1. Click on user **"velotrack-cicd"**
2. Go to **"Security credentials"** tab
3. Scroll to **"Access keys"** → **"Create access key"**
4. Select **"Command Line Interface (CLI)"**
5. Tick confirmation → **Next** → **"Create access key"**
6. **Copy both values** (won't see them again):
   - **Access Key ID** (e.g., `AKIAIOSFODNN7EXAMPLE`)
   - **Secret Access Key** (e.g., `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)

---

## 6. Install AWS CLI, eksctl & kubectl

Run these in your **WSL terminal**:

### Step 6.1: Install AWS CLI
```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
aws --version
```

### Step 6.2: Configure AWS CLI
```bash
aws configure
```
Enter:
- **AWS Access Key ID:** (paste your key)
- **AWS Secret Access Key:** (paste your secret)
- **Default region:** `us-east-1`
- **Default output format:** `json`

### Step 6.3: Verify AWS Access
```bash
aws sts get-caller-identity
```
> Should show your Account ID. If error → check credentials.

### Step 6.4: Install eksctl
```bash
curl --silent --location "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$(uname -s)_amd64.tar.gz" | tar xz -C /tmp
sudo mv /tmp/eksctl /usr/local/bin
eksctl version
```

### Step 6.5: Install kubectl
```bash
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/
kubectl version --client
```

---

## 7. Create ECR Private Repositories

```bash
aws ecr create-repository --repository-name velotrack-user-service --region us-east-1
aws ecr create-repository --repository-name velotrack-bicycle-service --region us-east-1
aws ecr create-repository --repository-name velotrack-maintenance-rental-service --region us-east-1
aws ecr create-repository --repository-name velotrack-maintenance-assistant-service --region us-east-1
aws ecr create-repository --repository-name velotrack-frontend --region us-east-1
```

---

## 8. Push Images to ECR (Private Registry)

### Step 8.1: Login to ECR
```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com
```

### Step 8.2: Tag and Push Each Image
```bash
docker tag tanmaypagar510/velotrack-user-service:latest ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-user-service:latest
docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-user-service:latest

docker tag tanmaypagar510/velotrack-bicycle-service:latest ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-bicycle-service:latest
docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-bicycle-service:latest

docker tag tanmaypagar510/velotrack-maintenance-rental-service:latest ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-rental-service:latest
docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-rental-service:latest

docker tag tanmaypagar510/velotrack-maintenance-assistant-service:latest ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-assistant-service:latest
docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-maintenance-assistant-service:latest

docker tag tanmaypagar510/velotrack-frontend:latest ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-frontend:latest
docker push ${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com/velotrack-frontend:latest
```

---

## 9. Create EKS Cluster

> ⏱️ This step takes **~15 minutes**

```bash
eksctl create cluster \
  --name velotrack-cluster \
  --region us-east-1 \
  --version 1.30 \
  --nodegroup-name velotrack-nodes \
  --node-type t3.medium \
  --nodes 2 \
  --nodes-min 1 \
  --nodes-max 3 \
  --managed
```

This creates:
- **VPC** with public and private subnets (CIDR: 10.0.0.0/16)
- **EKS Control Plane** (managed Kubernetes master)
- **2 Worker Nodes** (t3.medium — 2 vCPU, 4GB RAM each)
- **IAM Roles** with least privilege
- **Security Groups** for cluster and nodes
- **NAT Gateway** for private subnet outbound access

### Configure kubectl
```bash
aws eks update-kubeconfig --name velotrack-cluster --region us-east-1
kubectl get nodes
```
> You should see 2 nodes in `Ready` status.

---

## 10. Install Metrics Server & NGINX Ingress Controller

### Step 10.1: Install Metrics Server (required for HPA)
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```
> If you get an error about duplicate/immutable fields, delete and retry:
> ```bash
> kubectl delete deployment metrics-server -n kube-system
> kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
> ```

### Step 10.2: Install NGINX Ingress Controller
```bash
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/aws/deploy.yaml
```
> This creates an AWS Load Balancer that provides the external URL for the application.

---

## 11. Fix EBS CSI Driver (for PersistentVolumeClaim)

EKS requires the EBS CSI driver for PersistentVolumeClaims to work:

### Step 11.1: Enable OIDC Provider
```bash
eksctl utils associate-iam-oidc-provider --cluster velotrack-cluster --region us-east-1 --approve
```

### Step 11.2: Create IAM Service Account for EBS CSI
```bash
eksctl create iamserviceaccount \
  --name ebs-csi-controller-sa \
  --namespace kube-system \
  --cluster velotrack-cluster \
  --region us-east-1 \
  --attach-policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy \
  --approve \
  --override-existing-serviceaccounts
```

### Step 11.3: Attach EBS Policy to Node Role
```bash
NODE_ROLE=$(aws eks describe-nodegroup --cluster-name velotrack-cluster --nodegroup-name velotrack-nodes --region us-east-1 --query "nodegroup.nodeRole" --output text | awk -F'/' '{print $NF}')
aws iam attach-role-policy --role-name $NODE_ROLE --policy-arn arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy
```

### Step 11.4: Install EBS CSI Driver
```bash
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=release-1.28"
```

### Step 11.5: Verify CSI Driver
```bash
sleep 30
kubectl -n kube-system get pods -l app.kubernetes.io/name=aws-ebs-csi-driver
```
> You should see ebs-csi-controller and ebs-csi-node pods in `Running` status.

---

## 12. Deploy VeloTrack to Kubernetes (EKS)

### Step 12.1: Update K8s Manifests with Your Account ID
```bash
cd /mnt/c/Users/tanmaypagar/code/VeloTrack_A_Bicycle_Fleet_Management_System
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

sed -i "s|<AWS_ACCOUNT_ID>|${ACCOUNT_ID}|g" infra/k8s/user-service.yaml
sed -i "s|<AWS_ACCOUNT_ID>|${ACCOUNT_ID}|g" infra/k8s/bicycle-service.yaml
sed -i "s|<AWS_ACCOUNT_ID>|${ACCOUNT_ID}|g" infra/k8s/maintenance-rental-service.yaml
sed -i "s|<AWS_ACCOUNT_ID>|${ACCOUNT_ID}|g" infra/k8s/maintenance-assistant-service.yaml
sed -i "s|<AWS_ACCOUNT_ID>|${ACCOUNT_ID}|g" infra/k8s/frontend.yaml

sed -i "s|<REGION>|us-east-1|g" infra/k8s/user-service.yaml
sed -i "s|<REGION>|us-east-1|g" infra/k8s/bicycle-service.yaml
sed -i "s|<REGION>|us-east-1|g" infra/k8s/maintenance-rental-service.yaml
sed -i "s|<REGION>|us-east-1|g" infra/k8s/maintenance-assistant-service.yaml
sed -i "s|<REGION>|us-east-1|g" infra/k8s/frontend.yaml
```

### Step 12.2: Deploy Namespace & ConfigMap
```bash
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/configmap.yaml
```

### Step 12.3: Create Secrets (not stored in git for security)
```bash
kubectl -n velotrack create secret generic velotrack-secrets \
  --from-literal=DATABASE_URL="postgresql://velotrack:velotrack_secret@postgres:5432/velotrack" \
  --from-literal=JWT_SECRET="supersecretjwtkey123changeinproduction" \
  --from-literal=POSTGRES_PASSWORD="velotrack_secret" \
  --from-literal=RABBITMQ_URL="amqp://guest:guest@rabbitmq:5672/"
```

### Step 12.4: Deploy Network Policies
```bash
kubectl apply -f infra/k8s/network-policies.yaml
```

### Step 12.5: Deploy PostgreSQL (with PVC)
```bash
kubectl apply -f infra/k8s/postgres.yaml
kubectl -n velotrack rollout status deployment/postgres --timeout=120s
```
> PostgreSQL uses a `gp2` EBS PersistentVolumeClaim (5Gi) with `PGDATA` set to a subdirectory to avoid the `lost+found` issue on EBS volumes.

### Step 12.6: Deploy RabbitMQ
```bash
kubectl apply -f infra/k8s/rabbitmq.yaml
kubectl -n velotrack rollout status deployment/rabbitmq --timeout=120s
```

### Step 12.7: Deploy Backend Microservices
```bash
kubectl apply -f infra/k8s/user-service.yaml
kubectl apply -f infra/k8s/bicycle-service.yaml
kubectl apply -f infra/k8s/maintenance-rental-service.yaml
kubectl apply -f infra/k8s/maintenance-assistant-service.yaml
```

### Step 12.8: Deploy Frontend & Ingress
```bash
kubectl apply -f infra/k8s/frontend.yaml
kubectl apply -f infra/k8s/ingress.yaml
```

---

## 13. Verify Deployment & Get Application URL

### Step 13.1: Check All Pods
```bash
kubectl -n velotrack get pods
```
Expected output — all pods should show `Running` and `1/1` Ready:
```
NAME                                             READY   STATUS    RESTARTS   AGE
bicycle-service-xxx                              1/1     Running   0          2m
frontend-xxx                                     1/1     Running   0          2m
maintenance-assistant-service-xxx                1/1     Running   0          2m
maintenance-rental-service-xxx                   1/1     Running   0          2m
postgres-xxx                                     1/1     Running   0          3m
rabbitmq-xxx                                     1/1     Running   0          3m
user-service-xxx                                 1/1     Running   0          2m
```

### Step 13.2: Check Services
```bash
kubectl -n velotrack get svc
```

### Step 13.3: Check HPA (Horizontal Pod Autoscaler)
```bash
kubectl -n velotrack get hpa
```
> All services should show `MINPODS: 1`, `MAXPODS: 3`.

### Step 13.4: Check ConfigMap & Secrets
```bash
kubectl -n velotrack get configmap velotrack-config -o yaml
kubectl -n velotrack get secret velotrack-secrets
```

### Step 13.5: Check Network Policies
```bash
kubectl -n velotrack get networkpolicies
```

### Step 13.6: Get Application URL
```bash
kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```
> Open this URL in your browser — VeloTrack is live on AWS! 🎉

### Step 13.7: View Service Logs
```bash
kubectl -n velotrack logs -l app=user-service --tail=20
kubectl -n velotrack logs -l app=bicycle-service --tail=20
kubectl -n velotrack logs -l app=maintenance-rental-service --tail=20
kubectl -n velotrack logs -l app=maintenance-assistant-service --tail=20
```

### Step 13.8: Manually Scale Deployments
```bash
# Scale bicycle-service to 3 replicas
kubectl -n velotrack scale deployment/bicycle-service --replicas=3
kubectl -n velotrack get pods -w

# Scale back to 1
kubectl -n velotrack scale deployment/bicycle-service --replicas=1
```

---

## 14. CI/CD Pipeline (GitHub Actions)

### Step 14.1: Add GitHub Secrets
Go to GitHub repo → **Settings** → **Secrets and variables** → **Actions** → Add:

| Secret Name | Value |
|-------------|-------|
| `AWS_ACCESS_KEY_ID` | Your IAM Access Key ID |
| `AWS_SECRET_ACCESS_KEY` | Your IAM Secret Access Key |
| `AWS_ACCOUNT_ID` | Your 12-digit AWS Account ID |
| `DOCKERHUB_USERNAME` | `tanmaypagar510` |
| `DOCKERHUB_TOKEN` | Your Docker Hub access token |

### Step 14.2: Pipeline Trigger
The CI/CD pipeline (`.github/workflows/ci-cd.yml`) runs automatically on every `git push` to `main`:

1. ✅ Builds Docker images for all 5 services
2. ✅ Pushes images to ECR (private registry)
3. ✅ Connects to EKS cluster
4. ✅ Replaces `<AWS_ACCOUNT_ID>` and `<REGION>` placeholders
5. ✅ Creates/updates Kubernetes secrets
6. ✅ Deploys all manifests to EKS
7. ✅ Verifies deployment (pods, services, HPA)

### Step 14.3: Monitor Pipeline
Go to GitHub → **Actions** tab → Watch the pipeline run.

---

## 15. API Testing with Postman

### Step 15.1: Import Collection
Two Postman collections are provided:
- `docs/VeloTrack_API_Collection.postman.json` — **localhost** (Docker Compose)
- `docs/VeloTrack_AWS_API_Collection.postman.json` — **AWS EKS** deployment

Import in Postman → Click **Import** → Select the JSON file.

### Step 15.2: Run in Order
Execute requests numbered in order (1.1 → 1.2 → 1.3 → ...). Tokens and IDs auto-save.

### Step 15.3: Sample Data (Indian Names)

| Category | Sample Data |
|----------|-------------|
| **Users** | Rajesh Kumar (Admin), Priya Sharma (Staff), Amit Patel (Staff) |
| **Bicycles** | Hero Sprint Rover (Mumbai), Firefox Raptor (Mumbai), Atlas Peak (Delhi), Hercules Roadeo (Bangalore), Montra Madrock (Pune) |
| **Renters** | Neha Verma, Vikram Singh, Ananya Iyer, Rohan Deshmukh |
| **Technicians** | Suresh Yadav, Manoj Tiwari, Deepak Joshi |
| **Costs** | All in ₹ (INR) — ₹350, ₹800, ₹1200, ₹1500 |
| **Rental Rates** | ₹40-60 per hour |

---

## 16. Demo Recording Checklist (~5-10 min)

### Part 1: Running Application Demo
- [ ] Open browser → Show VeloTrack landing page
- [ ] **Login** → Dashboard with fleet overview
- [ ] Show **High Risk Alert Banner** (if >20% bikes in High tier)
- [ ] Navigate to **Bicycles** → Show list with **Risk Badges** (Low/Medium/High)
- [ ] Click **"Add Bicycle"** → Register a new bike
- [ ] Click **"Why this score?"** tooltip on a Risk Badge
- [ ] Go to **Rentals** → **Checkout** a bicycle (with ₹ rate)
- [ ] **Return** the bicycle → Cost calculated in ₹
- [ ] Go to **Maintenance** → Create a maintenance log
- [ ] Show **Bicycle Detail page** → Risk Trend Sparkline + History
- [ ] Go to **Assistant** → Ask: *"Does bike #1 need servicing?"*
- [ ] Show the **AI response with source records**

### Part 2: AWS Console Walkthrough
- [ ] Show AWS Console with **account name visible** (top-right corner)
- [ ] Navigate to **ECR** → Show 5 pushed container images
- [ ] Navigate to **EKS** → Show cluster details, node group
- [ ] Navigate to **VPC** → Show VPC, subnets, security groups
- [ ] Navigate to **EC2** → Show running instances (EKS nodes)
- [ ] Navigate to **Load Balancer** → Show the ALB serving the app
- [ ] Navigate to **CloudWatch** → Show log groups

### Part 3: kubectl Commands (show in terminal)
```bash
# Show running pods
kubectl -n velotrack get pods -o wide

# Show deployments
kubectl -n velotrack get deployments

# Show services
kubectl -n velotrack get svc

# Show configmaps (at least 2 key-value pairs)
kubectl -n velotrack get configmap velotrack-config -o yaml

# Show secrets
kubectl -n velotrack get secret velotrack-secrets -o yaml

# Show HPA (max 3 replicas)
kubectl -n velotrack get hpa

# Show network policies
kubectl -n velotrack get networkpolicies

# View backend service logs
kubectl -n velotrack logs -l app=user-service --tail=10
kubectl -n velotrack logs -l app=maintenance-rental-service --tail=10

# Manually scale deployment
kubectl -n velotrack scale deployment/bicycle-service --replicas=3
kubectl -n velotrack get pods

# Scale back
kubectl -n velotrack scale deployment/bicycle-service --replicas=1

# Show public IP of exposed services
kubectl get svc -n ingress-nginx
kubectl -n velotrack get ingress
```

---

## 17. Cleanup — Stop AWS Billing

> ⚠️ **Run this IMMEDIATELY after demo recording to stop charges!**

```bash
eksctl delete cluster --name velotrack-cluster --region us-east-1
```

This deletes:
- EKS cluster and control plane
- EC2 worker nodes
- NAT Gateway
- Load Balancer
- VPC, subnets, security groups
- EBS volumes

**Optional — delete ECR repos:**
```bash
for svc in user-service bicycle-service maintenance-rental-service maintenance-assistant-service frontend; do
  aws ecr delete-repository --repository-name velotrack-${svc} --region us-east-1 --force
done
```

---

## 18. Cost Breakdown

| Service | 24hr Cost | Monthly Cost |
|---------|-----------|-------------|
| EKS Control Plane | $2.40 | $72 |
| EC2 Nodes (2× t3.medium) | $2.00 | $60 |
| NAT Gateway | $1.08 | $32 |
| Load Balancer | $0.60 | $18 |
| EBS + ECR + Data Transfer | $0.05 | $1 |
| **Total** | **~$6.13 (~₹515)** | **~$183 (~₹15,400)** |

> 💡 **Tip:** Create cluster → Record demo → Delete cluster. Total cost: **₹500-1500**.

---

## Architecture Summary

```
┌─── AWS Cloud (us-east-1) ──────────────────────────────────────┐
│                                                                  │
│  ┌── VPC: 10.0.0.0/16 ───────────────────────────────────────┐ │
│  │                                                             │ │
│  │  Public Subnets (10.0.1.0/24, 10.0.2.0/24)                │ │
│  │  └── ALB (NGINX Ingress Controller)                        │ │
│  │  └── NAT Gateway                                           │ │
│  │                                                             │ │
│  │  Private Subnets (10.0.3.0/24, 10.0.4.0/24)               │ │
│  │  └── EKS Worker Nodes (2× t3.medium)                      │ │
│  │      ├── user-service (1-3 pods, HPA)                      │ │
│  │      ├── bicycle-service (1-3 pods, HPA)                   │ │
│  │      ├── maintenance-rental-service (1-3 pods, HPA)        │ │
│  │      ├── maintenance-assistant-service (1-3 pods, HPA)     │ │
│  │      ├── frontend (1-3 pods, HPA)                          │ │
│  │      ├── PostgreSQL (1 pod, 5Gi PVC)                       │ │
│  │      └── RabbitMQ (1 pod)                                  │ │
│  │                                                             │ │
│  │  Security: NACLs + Security Groups + Network Policies      │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ECR (Private Registry) │ S3 (ML Models) │ CloudWatch (Logs)   │
└──────────────────────────────────────────────────────────────────┘
```

