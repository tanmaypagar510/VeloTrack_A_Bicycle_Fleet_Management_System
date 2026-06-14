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
