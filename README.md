# 🚲 VeloTrack – Bicycle Fleet Management System

A **cloud-native, microservices-based** fleet management system for bicycle rental businesses. Built with **SvelteKit** frontend, **Flask** microservices, **ML-powered risk scoring**, **RAG-powered AI assistant**, containerized with **Docker**, orchestrated with **Kubernetes**, and deployed via **CI/CD** pipeline to **AWS**.

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Microservice Descriptions](#microservice-descriptions)
3. [Cloud-Native Patterns](#cloud-native-patterns)
4. [Tech Stack](#tech-stack)
5. [Project Structure](#project-structure)
6. [Setup Guide – Local Development](#setup-guide--local-development)
7. [API Documentation](#api-documentation)
8. [Kubernetes Deployment](#kubernetes-deployment)
9. [CI/CD Pipeline](#cicd-pipeline)
10. [Security](#security)
11. [Scalability & Observability](#scalability--observability)
12. [User Walkthrough](#user-walkthrough)
13. [Network Architecture](#network-architecture)

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         NGINX API Gateway (:8080)                   │
│            (Reverse proxy, load balancing, route dispatch)           │
├──────┬──────────┬─────────────────┬─────────────────┬───────────────┤
│      │          │                 │                 │               │
│  Frontend   User Service   Bicycle Service   Maint-Rental    Maint-Assistant
│  (SvelteKit) (Flask:5001)  (Flask:5002)      Service          Service
│  (:3000)                                     (Flask:5003)     (Flask:5004)
│      │          │                 │                 │               │
│      │          └────────┬────────┘                 │               │
│      │                   │                          │               │
│      │            ┌──────┴──────┐            ┌──────┴──────┐       │
│      │            │  PostgreSQL  │            │  RabbitMQ   │       │
│      │            │   (:5432)    │            │  (:5672)    │       │
│      │            └─────────────┘            └─────────────┘       │
│      │                                              │               │
│      │                                       ┌──────┴──────┐       │
│      │                                       │   Ollama     │       │
│      │                                       │  LLM (:11434)│       │
│      │                                       └─────────────┘       │
│      │                                              │               │
│      │                                       ┌──────┴──────┐       │
│      │                                       │ FAISS Vector │       │
│      │                                       │    Store     │       │
│      │                                       └─────────────┘       │
└──────┴──────────────────────────────────────────────────────────────┘
```

### Design Principles
- **Microservices Architecture**: Each service is independent, loosely coupled, and independently deployable
- **Event-Driven**: RabbitMQ for async inter-service communication (maintenance/rental events → risk recalculation)
- **API Gateway**: NGINX reverse proxy handles routing, load balancing
- **Stateless Services**: Horizontally scalable via Kubernetes HPA
- **12-Factor App**: Environment-based config, containerized, declarative infrastructure

---

## 🔧 Microservice Descriptions

### 1. User Service (Port 5001)
- **Purpose**: Authentication & user management
- **Endpoints**: Register, Login, JWT token generation, password change, profile management
- **Database**: PostgreSQL (`users` table)
- **Auth**: BCrypt password hashing, JWT tokens with configurable expiry

### 2. Bicycle Service (Port 5002)
- **Purpose**: Fleet CRUD – add, update, delete, status management
- **Endpoints**: CRUD for bicycles, status transitions (Available → Rented → Maintenance → Out of Service)
- **Database**: PostgreSQL (`bicycles` table)
- **Features**: Search/filter by status, unique bike codes, purchase tracking

### 3. Maintenance & Rental Service (Port 5003)
- **Purpose**: Maintenance logs, rental check-in/check-out, anomaly detection
- **Endpoints**: Maintenance CRUD, rental checkout/return, bicycle history
- **Database**: PostgreSQL (`maintenance_logs`, `rentals` tables)
- **Events**: Publishes to RabbitMQ on every maintenance/rental event
- **Anomaly Detection**: Flags rentals shorter than 5 minutes as anomalous

### 4. Maintenance Assistant Service (Port 5004)
- **Purpose**: AI-powered RAG assistant + ML risk scoring
- **Components**:
  - **RAG Pipeline**: Vector store (FAISS) + LLM (Ollama/Mistral) for conversational maintenance advice
  - **Risk Scorer**: XGBoost/rule-based scoring (0-100) with SHAP explainability
  - **Event Consumer**: Listens to RabbitMQ for real-time risk recalculation
- **Endpoints**: 
  - `POST /api/maintenance-assistant/ask` – Ask AI assistant
  - `GET /api/risk-scores/` – All fleet risk scores
  - `GET /api/risk-scores/{bike_id}` – Single bike score with trend
  - `POST /api/risk-scores/retrain` – Trigger model retraining (admin)
  - `POST /api/risk-scores/batch-update` – Nightly batch recalculation

---

## ☁️ Cloud-Native Patterns

| Component | Pattern | Implementation |
|---|---|---|
| **Authentication** | JWT + Principle of Least Privilege | Per-service JWT validation, admin_required decorator |
| **Network Segregation** | VNet/Subnet isolation | Kubernetes namespace `velotrack`, ClusterIP services |
| **Network Security** | Security Groups / NACLs | K8s NetworkPolicies, ClusterIP (internal only) |
| **Backend Services** | Containerization + Orchestration | Docker + Kubernetes Deployments |
| **Frontend** | Static hosting | SvelteKit with adapter-node on K8s |
| **Database** | Managed SQL | PostgreSQL 15 with PersistentVolumeClaim |
| **Vector Store** | Embedding storage | FAISS (in-process, within Assistant service) |
| **Local LLM** | Open-source LLM | Ollama (Mistral model) |
| **Risk Model Store** | Versioned model artifacts | Filesystem (S3 in production) |
| **Message Broker** | Async event-driven | RabbitMQ with topic exchange |
| **Scalability** | Horizontal Pod Autoscaling | HPA max 3 replicas, CPU threshold 70% |
| **Logging** | Centralized structured logging | Python `logging` → stdout → CloudWatch |
| **CI/CD** | Automated pipeline | GitHub Actions → ECR → EKS |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | SvelteKit 2, TailwindCSS 3, Chart.js |
| **Backend** | Python 3.11, Flask 3.0, Gunicorn |
| **Database** | PostgreSQL 15, SQLAlchemy ORM |
| **Message Broker** | RabbitMQ 3 (pika client) |
| **ML/AI** | XGBoost, SHAP, scikit-learn, sentence-transformers |
| **Vector Store** | FAISS (faiss-cpu) |
| **LLM** | Ollama (Mistral 7B) |
| **Containerization** | Docker, Docker Compose |
| **Orchestration** | Kubernetes (EKS) |
| **CI/CD** | GitHub Actions |
| **API Gateway** | NGINX |
| **Cloud** | AWS (ECR, EKS, RDS, S3, CloudWatch) |
| **API Docs** | Swagger/Flasgger (OpenAPI) |

---

## 📂 Project Structure

```
VeloTrack/
├── .github/
│   └── workflows/
│       └── ci-cd.yml                    # CI/CD pipeline (GitHub Actions)
├── backend/
│   ├── user-service/                    # Authentication & user management
│   │   ├── app.py, routes.py, models.py, auth.py, config.py
│   │   ├── Dockerfile, requirements.txt
│   ├── bicycle-service/                 # Bicycle fleet CRUD
│   │   ├── app.py, routes.py, models.py, auth.py, config.py
│   │   ├── Dockerfile, requirements.txt
│   ├── maintenance-rental-service/      # Maintenance logs & rentals
│   │   ├── app.py, routes.py, models.py, auth.py, config.py, events.py
│   │   ├── Dockerfile, requirements.txt
│   └── maintenance-assistant-service/   # RAG AI assistant & risk scoring
│       ├── app.py, routes.py, models.py, auth.py, config.py
│       ├── llm_client.py               # Ollama LLM integration
│       ├── vector_store.py             # FAISS vector store
│       ├── rag_pipeline.py             # RAG pipeline
│       ├── risk_scorer.py              # XGBoost risk scoring + SHAP
│       ├── event_consumer.py           # RabbitMQ event consumer
│       ├── Dockerfile, requirements.txt
├── frontend/                            # SvelteKit UI
│   ├── src/
│   │   ├── lib/api.js                  # API client
│   │   ├── lib/stores.js               # Svelte stores (auth, risk scores)
│   │   ├── lib/components/             # Navbar, RiskBadge, RiskSparkline
│   │   └── routes/                     # File-based routing
│   │       ├── +page.svelte            # Landing page
│   │       ├── +layout.svelte          # App layout
│   │       ├── login/+page.svelte
│   │       ├── register/+page.svelte
│   │       ├── dashboard/+page.svelte
│   │       ├── bicycles/+page.svelte
│   │       ├── bicycles/[id]/+page.svelte
│   │       ├── maintenance/+page.svelte
│   │       ├── rentals/+page.svelte
│   │       └── assistant/+page.svelte
│   ├── Dockerfile, package.json, svelte.config.js, vite.config.js
│   └── tailwind.config.js, postcss.config.js
├── infra/
│   ├── k8s/                             # Kubernetes manifests
│   │   ├── namespace.yaml
│   │   ├── configmap.yaml              # 9 key-value config pairs
│   │   ├── secrets.yaml                # 4 secret key-value pairs
│   │   ├── postgres.yaml               # DB + PVC
│   │   ├── rabbitmq.yaml               # Message broker
│   │   ├── user-service.yaml           # Deployment + Service + HPA
│   │   ├── bicycle-service.yaml
│   │   ├── maintenance-rental-service.yaml
│   │   ├── maintenance-assistant-service.yaml
│   │   └── frontend.yaml
│   └── nginx/
│       └── nginx.conf                   # API Gateway config
├── docker-compose.yml                   # Local development
├── .env                                 # Environment variables
└── README.md                            # This file
```

---

## 🚀 Setup Guide – Local Development

### Prerequisites
- **Docker Desktop** (v20+) with Docker Compose
- **Git**
- **Node.js 20+** (optional, for frontend dev without Docker)
- **Python 3.11+** (optional, for backend dev without Docker)

### Step 1: Clone the Repository
```bash
git clone https://github.com/<your-username>/VeloTrack_A_Bicycle_Fleet_Management_System.git
cd VeloTrack_A_Bicycle_Fleet_Management_System
```

### Step 2: Configure Environment Variables
The `.env` file is pre-configured with defaults for local development:
```bash
# Review/edit if needed
cat .env
```

### Step 3: Build and Start All Services
```bash
# Build and start all containers
docker-compose up --build -d

# Watch logs
docker-compose logs -f
```

### Step 4: Pull the Ollama LLM Model
```bash
# After Ollama container is running, pull the Mistral model
docker exec velotrack-ollama ollama pull mistral
```

### Step 5: Access the Application
| Service | URL |
|---|---|
| **Frontend (via NGINX)** | http://localhost:8080 |
| **Frontend (direct)** | http://localhost:3000 |
| **User Service API** | http://localhost:5001 |
| **Bicycle Service API** | http://localhost:5002 |
| **Maintenance Service API** | http://localhost:5003 |
| **Assistant Service API** | http://localhost:5004 |
| **RabbitMQ Dashboard** | http://localhost:15672 (guest/guest) |
| **Swagger Docs** | http://localhost:500X/apidocs |

### Step 6: Verify Health
```bash
curl http://localhost:5001/health
curl http://localhost:5002/health
curl http://localhost:5003/health
curl http://localhost:5004/health
```

### Stopping Services
```bash
docker-compose down          # Stop containers
docker-compose down -v       # Stop + remove volumes
```

---

## 📡 API Documentation

Swagger/OpenAPI documentation is auto-generated and available at `/apidocs` for each service:
- User Service: http://localhost:5001/apidocs
- Bicycle Service: http://localhost:5002/apidocs
- Maintenance Service: http://localhost:5003/apidocs
- Assistant Service: http://localhost:5004/apidocs

### Key API Endpoints

#### Authentication
```
POST /api/auth/register     - Register new user
POST /api/auth/login        - Login (returns JWT token)
GET  /api/auth/me           - Get current user profile
POST /api/auth/change-password - Change password
```

#### Bicycles
```
GET    /api/bicycles/           - List all bicycles (filter by ?status=)
GET    /api/bicycles/{id}       - Get bicycle details
POST   /api/bicycles/           - Register new bicycle
PUT    /api/bicycles/{id}       - Update bicycle details
PATCH  /api/bicycles/{id}/status - Update bicycle status
DELETE /api/bicycles/{id}       - Delete bicycle
```

#### Maintenance
```
GET  /api/maintenance/              - List all maintenance logs
GET  /api/maintenance/{id}          - Get maintenance log
POST /api/maintenance/              - Create maintenance log
GET  /api/maintenance/history/{id}  - Complete bicycle history
```

#### Rentals
```
GET  /api/rentals/                  - List all rentals
POST /api/rentals/checkout          - Checkout bicycle (start rental)
POST /api/rentals/return/{id}       - Return bicycle (end rental)
GET  /api/rentals/{id}              - Get rental details
```

#### Maintenance Assistant (RAG)
```
POST /api/maintenance-assistant/ask     - Ask AI assistant
GET  /api/maintenance-assistant/history - Chat history
```

#### Risk Scores
```
GET  /api/risk-scores/              - All fleet risk scores
GET  /api/risk-scores/{bike_id}     - Single bike risk + trend
POST /api/risk-scores/retrain       - Trigger retraining (admin)
POST /api/risk-scores/batch-update  - Nightly batch update
```

### Authentication
All API endpoints (except `/api/auth/login` and `/api/auth/register`) require a JWT Bearer token:
```
Authorization: Bearer <jwt_token>
```

---

## ☸️ Kubernetes Deployment

### Prerequisites
- AWS CLI configured with proper IAM credentials
- `kubectl` installed and configured
- EKS cluster created (`velotrack-cluster`)
- ECR repositories created for each service

### Create ECR Repositories
```bash
aws ecr create-repository --repository-name velotrack-user-service
aws ecr create-repository --repository-name velotrack-bicycle-service
aws ecr create-repository --repository-name velotrack-maintenance-rental-service
aws ecr create-repository --repository-name velotrack-maintenance-assistant-service
aws ecr create-repository --repository-name velotrack-frontend
```

### Manual Deployment Steps
```bash
# 1. Update kubeconfig
aws eks update-kubeconfig --name velotrack-cluster --region us-east-1

# 2. Create namespace
kubectl apply -f infra/k8s/namespace.yaml

# 3. Apply config and secrets
kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -f infra/k8s/secrets.yaml

# 4. Deploy infrastructure
kubectl apply -f infra/k8s/postgres.yaml
kubectl apply -f infra/k8s/rabbitmq.yaml

# 5. Deploy backend services
kubectl apply -f infra/k8s/user-service.yaml
kubectl apply -f infra/k8s/bicycle-service.yaml
kubectl apply -f infra/k8s/maintenance-rental-service.yaml
kubectl apply -f infra/k8s/maintenance-assistant-service.yaml

# 6. Deploy frontend
kubectl apply -f infra/k8s/frontend.yaml

# 7. Verify deployment
kubectl -n velotrack get pods
kubectl -n velotrack get services
kubectl -n velotrack get deployments
kubectl -n velotrack get hpa
kubectl -n velotrack get configmaps
kubectl -n velotrack get secrets
```

### K8s Features Implemented
| Feature | Details |
|---|---|
| **ConfigMap** | 9 key-value pairs (service URLs, Ollama config, DB name) |
| **Secrets** | 4 key-value pairs (DATABASE_URL, JWT_SECRET, RABBITMQ_URL, POSTGRES_PASSWORD) |
| **HPA** | Enabled for all 5 deployments, max 3 replicas, CPU 70% threshold |
| **Health Probes** | Readiness + Liveness probes on `/health` for all services |
| **Resource Limits** | CPU/memory requests and limits for every container |
| **PersistentVolume** | PVC for PostgreSQL data (5Gi) |
| **Namespace** | Isolated `velotrack` namespace |

### Useful kubectl Commands
```bash
# View logs
kubectl -n velotrack logs -f deployment/user-service
kubectl -n velotrack logs -f deployment/bicycle-service

# Scale manually
kubectl -n velotrack scale deployment/user-service --replicas=3

# Get service IPs
kubectl -n velotrack get svc

# Describe a pod
kubectl -n velotrack describe pod <pod-name>

# Port forward for local access
kubectl -n velotrack port-forward svc/frontend 3000:3000
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflow (`.github/workflows/ci-cd.yml`)

**Trigger**: Push to `main` branch

**Pipeline Stages:**

1. **Build & Push** (parallel for all 5 services)
   - Checkout code
   - Login to AWS ECR
   - Build Docker images
   - Tag with commit SHA + `latest`
   - Push to ECR (private registry)

2. **Deploy to Kubernetes** (sequential, after build)
   - Update kubeconfig for EKS
   - Replace image tag placeholders in K8s manifests
   - Apply namespace, configmap, secrets
   - Deploy infrastructure (PostgreSQL, RabbitMQ)
   - Deploy backend services
   - Deploy frontend
   - Verify all pods are running

3. **Weekly Model Retraining** (cron schedule)
   - Trigger XGBoost model retraining
   - Batch update all risk scores

### Required GitHub Secrets
```
AWS_ACCESS_KEY_ID     - AWS IAM access key
AWS_SECRET_ACCESS_KEY - AWS IAM secret key
AWS_ACCOUNT_ID        - AWS account number
```

---

## 🔒 Security

| Measure | Implementation |
|---|---|
| **JWT Authentication** | All APIs protected with JWT Bearer tokens |
| **Password Hashing** | BCrypt with salt |
| **Role-Based Access** | `admin` and `staff` roles, `admin_required` decorator |
| **Secrets Management** | K8s Secrets (base64 encoded) for sensitive config |
| **Network Security** | ClusterIP services (not exposed externally), NGINX gateway |
| **CORS** | Configured per-service |
| **HTTPS** | TLS termination at load balancer (production) |
| **Principle of Least Privilege** | Services only access what they need |

---

## 📊 Scalability & Observability

### Scalability
- **Stateless Services**: All microservices are stateless, enabling horizontal scaling
- **HPA**: Kubernetes Horizontal Pod Autoscaler for all deployments (max 3 replicas)
- **Load Balancing**: NGINX distributes traffic across service instances
- **Database**: PostgreSQL with connection pooling

### Observability
- **Structured Logging**: Python `logging` with timestamps, service names, log levels
- **Health Checks**: `/health` endpoint on every service
- **CloudWatch Integration**: Container logs stream to CloudWatch via EKS
- **Error Tracking**: Try-catch with logged warnings for all inter-service calls
- **RabbitMQ Monitoring**: Management dashboard on port 15672

---

## 🎬 User Walkthrough

### Scenario: Complete Fleet Management Workflow

1. **Admin logs in** → `POST /api/auth/login` with credentials → receives JWT token

2. **Registers a new bicycle** → Navigates to Bicycles page → Clicks "Add Bicycle" → Fills form (bike_code: BIKE-042, make: Trek, model: FX 3, condition: Good) → Submits

3. **Marks it as rented** → On Rentals page → Clicks "New Checkout" → Selects BIKE-042 → Enters renter name → Submits (status changes to "Rented", RabbitMQ event published)

4. **Returns the bike** → Clicks "Return" on the active rental → Bike status returns to "Available", duration calculated, anomaly detection runs

5. **Creates maintenance log after return** → Maintenance page → "New Log" → Selects BIKE-042 → Describes problem "Brake pads worn" → Work done "Replaced front brake pads" → Submits (RabbitMQ event triggers risk recalculation)

6. **Views bicycle history** → Clicks BIKE-042 in bicycle list → Sees full maintenance + rental history with anomaly tags → Views risk score badge + 30-day trend sparkline

7. **Asks the Maintenance Assistant** → Navigates to Assistant page → Types "Does bike #42 need servicing?" → Receives AI-generated recommendation grounded in actual maintenance and rental history with source records displayed

8. **Reviews risk scores** → Dashboard shows High Risk Alert if >20% of fleet is high risk → Each bike card shows color-coded risk badge (Low/Medium/High) → Clicks badge to see "Why this score?" tooltip with top contributing features

---

## 🌐 Network Architecture

```
                    ┌──────────────────┐
                    │   Internet /     │
                    │   Client Browser │
                    └────────┬─────────┘
                             │ HTTPS (Port 443)
                    ┌────────┴─────────┐
                    │   AWS ALB /      │
                    │   Load Balancer  │
                    └────────┬─────────┘
                             │
              ┌──────────────┴──────────────┐
              │   VPC: 10.0.0.0/16          │
              │                              │
              │  ┌─── Public Subnet ──────┐  │
              │  │  10.0.1.0/24           │  │
              │  │  NAT Gateway           │  │
              │  │  ALB Target Group      │  │
              │  └────────┬───────────────┘  │
              │           │                  │
              │  ┌─── Private Subnet 1 ───┐  │
              │  │  10.0.10.0/24          │  │
              │  │  EKS Worker Nodes      │  │
              │  │  ┌──────────────┐      │  │
              │  │  │ K8s Namespace│      │  │
              │  │  │  velotrack   │      │  │
              │  │  │              │      │  │
              │  │  │ ┌──────────┐ │      │  │
              │  │  │ │Frontend  │ │      │  │
              │  │  │ │:3000     │ │      │  │
              │  │  │ ├──────────┤ │      │  │
              │  │  │ │User Svc  │ │      │  │
              │  │  │ │:5001     │ │      │  │
              │  │  │ ├──────────┤ │      │  │
              │  │  │ │Bike Svc  │ │      │  │
              │  │  │ │:5002     │ │      │  │
              │  │  │ ├──────────┤ │      │  │
              │  │  │ │Maint Svc │ │      │  │
              │  │  │ │:5003     │ │      │  │
              │  │  │ ├──────────┤ │      │  │
              │  │  │ │Asst Svc  │ │      │  │
              │  │  │ │:5004     │ │      │  │
              │  │  │ ├──────────┤ │      │  │
              │  │  │ │RabbitMQ  │ │      │  │
              │  │  │ │:5672     │ │      │  │
              │  │  │ └──────────┘ │      │  │
              │  │  └──────────────┘      │  │
              │  └────────────────────────┘  │
              │                              │
              │  ┌─── Private Subnet 2 ───┐  │
              │  │  10.0.20.0/24          │  │
              │  │  RDS PostgreSQL        │  │
              │  │  (Multi-AZ optional)   │  │
              │  │  Security Group:       │  │
              │  │   Allow 5432 from      │  │
              │  │   10.0.10.0/24 only    │  │
              │  └────────────────────────┘  │
              │                              │
              └──────────────────────────────┘
```

### Security Groups
| Security Group | Inbound Rules |
|---|---|
| **ALB SG** | Port 80/443 from 0.0.0.0/0 |
| **EKS Node SG** | All traffic from ALB SG, All traffic from self |
| **RDS SG** | Port 5432 from EKS Node SG only |
| **RabbitMQ SG** | Port 5672 from EKS Node SG only |

---

## 📝 Documentation Deliverables Checklist

- [x] **Public GitHub Repo** – Full source code with commits
- [x] **DevOps** – Kubernetes manifests, Dockerfiles, CI/CD pipeline YAML
- [x] **Architecture Overview** – This README with microservice descriptions & cloud patterns
- [x] **Setup Guide** – Step-by-step Docker Compose setup
- [x] **API Documentation** – Swagger/OpenAPI via Flasgger (auto-generated)
- [x] **User Walkthrough** – Complete scenario documented above
- [ ] **Network Architecture Diagram** – Draw.io diagram (see ASCII above)
- [ ] **Cloud Deployment Screenshots** – AWS console screenshots
- [ ] **Demo Recording** – 5-10 min video walkthrough

---

## 📄 License

This project is developed as a case study for educational purposes.

