# VeloTrack – Complete Repository Explanation (Line-by-Line)

> This document explains **every folder, file, and line** of the VeloTrack project.
> It covers: what each file does, why it exists, and how all parts connect together.

---

## Table of Contents

1. [Root Level Files](#1-root-level-files)
2. [.github/workflows/ — CI/CD Pipeline](#2-githubworkflows--cicd-pipeline)
3. [backend/ — 4 Microservices](#3-backend--4-microservices)
4. [frontend/ — SvelteKit UI](#4-frontend--sveltekit-ui)
5. [infra/k8s/ — Kubernetes Manifests](#5-infrak8s--kubernetes-manifests)
6. [infra/aws/ — AWS Infrastructure](#6-infraaws--aws-infrastructure)
7. [infra/nginx/ — API Gateway](#7-infranginx--api-gateway)
8. [docs/ — Documentation](#8-docs--documentation)
9. [Service Communication Flow](#9-service-communication-flow)
10. [Why Each Technology Was Chosen](#10-why-each-technology-was-chosen)

---

## 1. Root Level Files

### `docker-compose.yml`
**What:** Defines all containers for local development. One command starts the entire app.
**Why:** Developers can run `docker-compose up --build -d` and get the full system running locally without installing anything.

```yaml
# Line-by-line explanation:

version: '3.8'                    # Docker Compose file format version

services:
  # ─── DATABASE ───
  postgres:                       # PostgreSQL database container
    image: postgres:15-alpine     # Official PostgreSQL 15 image (Alpine = lightweight)
    container_name: velotrack-postgres
    environment:                  # Database credentials (from .env file)
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: velotrack      # Creates a database named "velotrack" on first start
    ports:
      - "5432:5432"               # Expose port 5432 so services can connect
    volumes:
      - postgres_data:/var/lib/postgresql/data  # Persist data between restarts
    networks:
      - velotrack-net             # Internal network (all containers can talk to each other)

  # ─── MESSAGE BROKER ───
  rabbitmq:                       # RabbitMQ message broker
    image: rabbitmq:3-management-alpine  # Includes management UI dashboard
    container_name: velotrack-rabbitmq
    ports:
      - "5672:5672"               # AMQP protocol port (services publish/consume events)
      - "15672:15672"             # Management UI (http://localhost:15672, guest/guest)
    networks:
      - velotrack-net

  # ─── AI MODEL SERVER ───
  ollama:                         # Ollama - runs LLM models locally
    image: ollama/ollama:latest
    container_name: velotrack-ollama
    ports:
      - "11434:11434"             # Ollama API port
    volumes:
      - ollama_data:/root/.ollama # Persist downloaded models
    networks:
      - velotrack-net

  # ─── BACKEND MICROSERVICES ───
  user-service:                   # Handles login, registration, JWT tokens
    build: ./backend/user-service # Build from Dockerfile in this folder
    container_name: velotrack-user-service
    ports:
      - "5001:5001"
    environment:                  # Each service gets its own config
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      - postgres                  # Wait for postgres to start first
    networks:
      - velotrack-net

  bicycle-service:                # Manages bicycle fleet (CRUD operations)
    build: ./backend/bicycle-service
    container_name: velotrack-bicycle-service
    ports:
      - "5002:5002"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
    depends_on:
      - postgres
    networks:
      - velotrack-net

  maintenance-rental-service:     # Handles rentals + maintenance logs
    build: ./backend/maintenance-rental-service
    container_name: velotrack-maintenance-rental-service
    ports:
      - "5003:5003"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
      RABBITMQ_URL: ${RABBITMQ_URL}       # Publishes events to RabbitMQ
      BICYCLE_SERVICE_URL: http://bicycle-service:5002  # Calls bicycle service
    depends_on:
      - postgres
      - rabbitmq
    networks:
      - velotrack-net

  maintenance-assistant-service:  # AI assistant + risk scoring
    build: ./backend/maintenance-assistant-service
    container_name: velotrack-maintenance-assistant-service
    ports:
      - "5004:5004"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      JWT_SECRET: ${JWT_SECRET}
      RABBITMQ_URL: ${RABBITMQ_URL}       # Consumes events from RabbitMQ
      OLLAMA_URL: http://ollama:11434     # Connects to Ollama for AI responses
      OLLAMA_MODEL: tinyllama             # Which LLM model to use
      BICYCLE_SERVICE_URL: http://bicycle-service:5002
      MAINTENANCE_RENTAL_SERVICE_URL: http://maintenance-rental-service:5003
    depends_on:
      - postgres
      - rabbitmq
      - ollama
    networks:
      - velotrack-net

  # ─── FRONTEND ───
  frontend:                       # SvelteKit web application
    build: ./frontend
    container_name: velotrack-frontend
    ports:
      - "3000:3000"
    networks:
      - velotrack-net

  # ─── API GATEWAY ───
  nginx:                          # NGINX reverse proxy — single entry point
    image: nginx:alpine
    container_name: velotrack-nginx
    ports:
      - "8080:80"                 # User accesses http://localhost:8080
    volumes:
      - ./infra/nginx/nginx.conf:/etc/nginx/nginx.conf  # Our custom config
    depends_on:                   # Start after all services are up
      - user-service
      - bicycle-service
      - maintenance-rental-service
      - maintenance-assistant-service
      - frontend
    networks:
      - velotrack-net

volumes:                          # Named volumes for data persistence
  postgres_data:                  # Database files survive container restarts
  ollama_data:                    # Downloaded AI models survive restarts

networks:
  velotrack-net:                  # Custom bridge network — all containers can find each other by name
    driver: bridge
```

### `.env` / `.env.example`
**What:** Environment variables (database URL, passwords, secrets).
**Why:** Separates sensitive config from code. Never committed to git (`.env` is in `.gitignore`).

```bash
POSTGRES_USER=velotrack              # Database username
POSTGRES_PASSWORD=velotrack_secret   # Database password
DATABASE_URL=postgresql://velotrack:velotrack_secret@postgres:5432/velotrack  # Full connection string
JWT_SECRET=supersecretjwtkey123changeinproduction  # Secret key for signing JWT tokens
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672/     # RabbitMQ connection
OLLAMA_URL=http://ollama:11434                      # AI model server
OLLAMA_MODEL=tinyllama                              # Which model to use
```

### `.gitignore`
**What:** Tells git which files to NOT push to GitHub.
**Why:** Prevents sensitive data (`.env`), large files (models), and generated files (`node_modules`) from being committed.

### `VeloTrack_A_Bicycle_Fleet_Management_System.iml`
**What:** JetBrains IDE project file.
**Why:** Auto-generated by IntelliJ/WebStorm. Stores IDE settings.

---

## 2. .github/workflows/ — CI/CD Pipeline

### `ci-cd.yml` — Full Line-by-Line Explanation

```yaml
# ──────────────────────────────────────────────────────────────
# VeloTrack CI/CD Pipeline — Build, Push to ECR, Deploy to EKS
# ──────────────────────────────────────────────────────────────
name: VeloTrack CI/CD Pipeline     # Name shown in GitHub Actions tab

on:                                 # WHEN does this pipeline run?
  push:
    branches: [main]                # Run on every push to main branch
  pull_request:
    branches: [main]                # Also run on pull requests to main

env:                                # GLOBAL VARIABLES available to all jobs
  AWS_REGION: us-east-1             # AWS region where everything is deployed
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com
  #            ↑ Builds the ECR URL from your AWS Account ID secret
  #            Example: 123456789012.dkr.ecr.us-east-1.amazonaws.com
  EKS_CLUSTER_NAME: velotrack-cluster   # Name of your Kubernetes cluster
  K8S_NAMESPACE: velotrack              # Kubernetes namespace for all resources

jobs:
  # ═══════════════════════════════════════════════════════════════
  # JOB 1: Build Docker images and push to AWS ECR (private registry)
  # ═══════════════════════════════════════════════════════════════
  build-and-push:
    name: Build & Push Docker Images
    runs-on: ubuntu-latest          # Run on GitHub's Ubuntu server (free)
    strategy:
      matrix:                       # MATRIX = run this job 5 TIMES in parallel
        service:                    # Once for each service:
          - name: user-service
            context: ./backend/user-service     # Folder with Dockerfile
            port: 5001
          - name: bicycle-service
            context: ./backend/bicycle-service
            port: 5002
          - name: maintenance-rental-service
            context: ./backend/maintenance-rental-service
            port: 5003
          - name: maintenance-assistant-service
            context: ./backend/maintenance-assistant-service
            port: 5004
          - name: frontend
            context: ./frontend
            port: 3000

    steps:
      - name: Checkout code          # Download your repo code
        uses: actions/checkout@v4

      - name: Configure AWS credentials  # Login to AWS using your secrets
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
          # ↑ These secrets are stored in GitHub repo → Settings → Secrets

      - name: Login to Amazon ECR     # Get permission to push Docker images
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build, tag, and push image to ECR
        env:
          IMAGE_TAG: ${{ github.sha }}          # Use git commit hash as image tag
          SERVICE_NAME: ${{ matrix.service.name }}  # Current service from matrix
          BUILD_CONTEXT: ${{ matrix.service.context }}
        run: |
          # Build the Docker image from the service's Dockerfile
          docker build -t $ECR_REGISTRY/velotrack-$SERVICE_NAME:$IMAGE_TAG $BUILD_CONTEXT
          # ↑ Tag format: 123456789012.dkr.ecr.us-east-1.amazonaws.com/velotrack-user-service:abc123

          # Also tag as "latest" for convenience
          docker tag $ECR_REGISTRY/velotrack-$SERVICE_NAME:$IMAGE_TAG $ECR_REGISTRY/velotrack-$SERVICE_NAME:latest

          # Push both tags to ECR (private Docker registry in AWS)
          docker push $ECR_REGISTRY/velotrack-$SERVICE_NAME:$IMAGE_TAG
          docker push $ECR_REGISTRY/velotrack-$SERVICE_NAME:latest

  # ═══════════════════════════════════════════════════════════════
  # JOB 2: Deploy to Kubernetes (EKS)
  # Runs AFTER Job 1 completes successfully
  # ═══════════════════════════════════════════════════════════════
  deploy:
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    needs: build-and-push           # Wait for images to be built first
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    #   ↑ Only deploy on PUSH to main (not on pull requests)

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig for EKS
        run: |
          # Download kubectl config to connect to your EKS cluster
          aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $AWS_REGION

      - name: Replace placeholders in K8s manifests
        env:
          AWS_ACCOUNT_ID: ${{ secrets.AWS_ACCOUNT_ID }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          # The K8s YAML files have placeholders like <AWS_ACCOUNT_ID>
          # This replaces them with actual values before deploying
          find infra/k8s -name '*.yaml' -exec sed -i \
            -e "s|<AWS_ACCOUNT_ID>|$AWS_ACCOUNT_ID|g" \
            -e "s|<REGION>|$AWS_REGION|g" \
            -e "s|:latest|:$IMAGE_TAG|g" \
            {} \;
          # Now image references become:
          # 123456789012.dkr.ecr.us-east-1.amazonaws.com/velotrack-user-service:abc123

      - name: Deploy namespace and infrastructure
        run: |
          # Create the "velotrack" namespace
          kubectl apply -f infra/k8s/namespace.yaml

          # Apply ConfigMap (non-sensitive settings: URLs, model name, ports)
          kubectl apply -f infra/k8s/configmap.yaml

          # Create secrets (passwords, JWT secret) — NOT from file because
          # secrets.yaml is empty in git (security best practice)
          kubectl -n $K8S_NAMESPACE create secret generic velotrack-secrets \
            --from-literal=DATABASE_URL="postgresql://velotrack:velotrack_secret@postgres:5432/velotrack" \
            --from-literal=JWT_SECRET="supersecretjwtkey123changeinproduction" \
            --from-literal=POSTGRES_PASSWORD="velotrack_secret" \
            --from-literal=RABBITMQ_URL="amqp://guest:guest@rabbitmq:5672/" \
            --dry-run=client -o yaml | kubectl apply -f -
          # ↑ --dry-run=client -o yaml | kubectl apply -f -
          #   This trick: generates the YAML without creating it, then applies it.
          #   Works for both CREATE (first time) and UPDATE (subsequent times).

          # Apply network policies (firewall rules between pods)
          kubectl apply -f infra/k8s/network-policies.yaml

          # Deploy PostgreSQL (database)
          kubectl apply -f infra/k8s/postgres.yaml
          # Deploy RabbitMQ (message broker)
          kubectl apply -f infra/k8s/rabbitmq.yaml

          # Wait for database to be ready before deploying services
          kubectl -n $K8S_NAMESPACE rollout status deployment/postgres --timeout=120s
          kubectl -n $K8S_NAMESPACE rollout status deployment/rabbitmq --timeout=120s

      - name: Deploy backend microservices
        run: |
          kubectl apply -f infra/k8s/user-service.yaml
          kubectl apply -f infra/k8s/bicycle-service.yaml
          kubectl apply -f infra/k8s/maintenance-rental-service.yaml
          kubectl apply -f infra/k8s/maintenance-assistant-service.yaml

          # Wait for each service to be ready
          kubectl -n $K8S_NAMESPACE rollout status deployment/user-service --timeout=180s
          kubectl -n $K8S_NAMESPACE rollout status deployment/bicycle-service --timeout=180s
          kubectl -n $K8S_NAMESPACE rollout status deployment/maintenance-rental-service --timeout=180s
          kubectl -n $K8S_NAMESPACE rollout status deployment/maintenance-assistant-service --timeout=300s
          # ↑ 300s timeout for assistant because it's larger (AI dependencies)

      - name: Deploy frontend
        run: |
          kubectl apply -f infra/k8s/frontend.yaml
          kubectl -n $K8S_NAMESPACE rollout status deployment/frontend --timeout=120s

      - name: Verify deployment
        run: |
          # Print status of everything to verify it's working
          kubectl -n $K8S_NAMESPACE get pods         # Show all running containers
          kubectl -n $K8S_NAMESPACE get services     # Show internal service IPs
          kubectl -n $K8S_NAMESPACE get deployments  # Show deployment status
          kubectl -n $K8S_NAMESPACE get hpa          # Show auto-scaling config
          kubectl -n $K8S_NAMESPACE get configmaps   # Show config
          kubectl -n $K8S_NAMESPACE get secrets      # Show secrets exist (not values)

  # ═══════════════════════════════════════════════════════════════
  # JOB 3: Weekly Model Retraining (runs on schedule, not on push)
  # ═══════════════════════════════════════════════════════════════
  retrain-model:
    name: Weekly Risk Model Retraining
    runs-on: ubuntu-latest
    if: github.event_name == 'schedule'  # Only runs on cron schedule
    # ↑ This job NEVER runs on push/PR — only on weekly schedule

    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: aws eks update-kubeconfig --name $EKS_CLUSTER_NAME --region $AWS_REGION

      - name: Trigger model retraining
        run: |
          # Find the assistant service pod
          POD=$(kubectl -n $K8S_NAMESPACE get pods -l app=maintenance-assistant-service -o jsonpath='{.items[0].metadata.name}')

          # Call the retrain API inside the pod
          kubectl -n $K8S_NAMESPACE exec $POD -- curl -s -X POST http://localhost:5004/api/risk-scores/retrain \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer admin-cron-token"
          # ↑ This tells the XGBoost model to retrain on latest data

      - name: Trigger batch score update
        run: |
          POD=$(kubectl -n $K8S_NAMESPACE get pods -l app=maintenance-assistant-service -o jsonpath='{.items[0].metadata.name}')

          # Recalculate risk scores for ALL bikes
          kubectl -n $K8S_NAMESPACE exec $POD -- curl -s -X POST http://localhost:5004/api/risk-scores/batch-update \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer admin-cron-token"
```

---

## 3. backend/ — 4 Microservices

### Why 4 Separate Services?
Each service handles ONE responsibility (Single Responsibility Principle):
- **user-service** → Who are you? (Authentication)
- **bicycle-service** → What bikes exist? (Fleet data)
- **maintenance-rental-service** → What happened? (Events/history)
- **maintenance-assistant-service** → What should we do? (AI/Analytics)

### Common Files in Every Service

| File | Purpose |
|------|---------|
| `app.py` | Main application entry point — creates Flask app, registers routes, connects to DB |
| `routes.py` | API endpoint definitions (URLs + logic) |
| `models.py` | Database table definitions (SQLAlchemy ORM) |
| `auth.py` | JWT token validation decorator (`@jwt_required`) |
| `config.py` | Configuration from environment variables |
| `Dockerfile` | Instructions to build Docker image |
| `requirements.txt` | Python dependencies to install |

---

### 3.1 User Service (`backend/user-service/`)

**Purpose:** Handles user registration, login, JWT token issuance, and profile management.

#### `app.py`
```python
from flask import Flask          # Web framework
from flask_cors import CORS      # Allow cross-origin requests (frontend → backend)
from flasgger import Swagger     # Auto-generate Swagger/OpenAPI docs at /apidocs
from models import db            # SQLAlchemy database instance
from routes import auth_bp, users_bp  # Route blueprints
from config import Config        # Configuration class

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)      # Load DB URL, JWT secret from env vars
    CORS(app)                           # Allow frontend to call this API
    db.init_app(app)                    # Connect SQLAlchemy to Flask
    Swagger(app)                        # Enable /apidocs endpoint
    app.register_blueprint(auth_bp)     # Register /api/auth/* routes
    app.register_blueprint(users_bp)    # Register /api/users/* routes

    with app.app_context():
        db.create_all()                 # Create tables if they don't exist
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5001)  # Listen on all interfaces, port 5001
```

#### `models.py`
```python
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)    # Login identifier
    password_hash = db.Column(db.String(255))          # BCrypt hashed password
    full_name = db.Column(db.String(255))
    role = db.Column(db.String(50), default='staff')   # 'admin' or 'staff'
    phone = db.Column(db.String(100))
    created_at = db.Column(db.DateTime)
```
**Why BCrypt?** Passwords are never stored in plain text. BCrypt is slow by design (prevents brute-force attacks).

#### `auth.py`
```python
import jwt  # PyJWT library

def jwt_required(f):
    """Decorator — checks if request has valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            return {'error': 'Token required'}, 401
        try:
            payload = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
            request.user = payload  # Attach user info to request
        except jwt.ExpiredSignatureError:
            return {'error': 'Token expired'}, 401
        except jwt.InvalidTokenError:
            return {'error': 'Invalid token'}, 401
        return f(*args, **kwargs)
    return decorated
```
**Why JWT?** Stateless authentication — no session storage needed. Each request carries its own proof of identity.

#### `routes.py` — Key Endpoints
```python
POST /api/auth/register    → Create new user (hash password, save to DB)
POST /api/auth/login       → Verify password, return JWT token
GET  /api/auth/me          → Return current user's profile
POST /api/auth/change-password → Verify old password, update with new
GET  /api/users/           → List all users (admin only)
```

#### `Dockerfile`
```dockerfile
FROM python:3.11-slim          # Base image with Python 3.11
WORKDIR /app                   # Set working directory
COPY requirements.txt .        # Copy dependency list
RUN pip install -r requirements.txt  # Install dependencies
COPY . .                       # Copy all source code
EXPOSE 5001                    # Document which port the app uses
CMD ["python", "app.py"]       # Command to run when container starts
```

---

### 3.2 Bicycle Service (`backend/bicycle-service/`)

**Purpose:** CRUD operations for the bicycle fleet.

#### Key Endpoints
```python
POST   /api/bicycles/          → Register new bicycle (bike_code, make, model, color)
GET    /api/bicycles/          → List all bikes (optional ?status=Available filter)
GET    /api/bicycles/{id}      → Get single bike details
PUT    /api/bicycles/{id}      → Update bike details (color, location, condition)
PATCH  /api/bicycles/{id}/status → Change status (Available/Rented/In Maintenance/Out of Service)
DELETE /api/bicycles/{id}      → Delete a bicycle
```

#### `models.py`
```python
class Bicycle(db.Model):
    bike_code = db.Column(db.String(50), unique=True)  # e.g., "VT-MUM-001"
    make = db.Column(db.String(100))                    # e.g., "Hero"
    model = db.Column(db.String(100))                   # e.g., "Sprint Rover"
    status = db.Column(db.String(50), default='Available')  # Current state
    total_rentals = db.Column(db.Integer, default=0)    # Rental counter
    last_serviced = db.Column(db.DateTime)              # Last maintenance date
```

---

### 3.3 Maintenance & Rental Service (`backend/maintenance-rental-service/`)

**Purpose:** Records rental check-in/check-out events and maintenance logs. Publishes events to RabbitMQ.

#### Key Endpoints
```python
POST /api/rentals/checkout       → Start a rental (sets bike status to "Rented")
POST /api/rentals/return/{id}    → End a rental (calculates cost, duration, anomaly)
GET  /api/rentals/               → List all rentals (filter by ?status=Active)
POST /api/maintenance/           → Create maintenance log (sets bike to "In Maintenance")
GET  /api/maintenance/           → List all maintenance logs
GET  /api/maintenance/history/{bike_id} → Full history (rentals + maintenance combined)
```

#### `events.py` — RabbitMQ Publishing
```python
def publish_rental_return_event(bike_id, rental_id, duration, is_anomalous):
    """Publish event to RabbitMQ when a bike is returned"""
    message = {
        'event_type': 'rental.returned',
        'bicycle_id': bike_id,
        'rental_id': rental_id,
        'duration_hours': duration,
        'is_anomalous': is_anomalous
    }
    # Sends to RabbitMQ → maintenance-assistant-service picks it up
    # → triggers risk score recalculation for this bike
    channel.basic_publish(exchange='velotrack.events', routing_key='rental.returned', body=json.dumps(message))
```
**Why RabbitMQ?** Decouples services. Rental service doesn't need to know about risk scoring. It just publishes "something happened" and whoever cares will process it.

#### Anomaly Detection
```python
ANOMALY_THRESHOLD_MINUTES = 5  # Rentals shorter than 5 min are suspicious

if duration * 60 < ANOMALY_THRESHOLD_MINUTES:
    rental.is_anomalous = True
    rental.anomaly_reason = f"Unusually short rental: {round(duration*60,1)} minutes"
```
**Why?** Very short rentals often indicate a problem (bike broken, wrong bike checked out). These anomalies feed into the risk scoring model.

---

### 3.4 Maintenance Assistant Service (`backend/maintenance-assistant-service/`)

**Purpose:** AI-powered recommendations + ML risk scoring. The most complex service.

#### Special Files

| File | Purpose |
|------|---------|
| `llm_client.py` | Connects to Ollama LLM + provides intelligent data-driven fallback |
| `vector_store.py` | FAISS vector database — stores bike history as embeddings |
| `rag_pipeline.py` | RAG (Retrieval Augmented Generation) — finds relevant context + asks LLM |
| `risk_scorer.py` | XGBoost ML model for risk scoring (0-100) |
| `event_consumer.py` | Background thread consuming RabbitMQ events |

#### `risk_scorer.py` — How Risk Scoring Works
```python
FEATURE_NAMES = [
    'days_since_last_service',      # How long since last maintenance
    'total_rentals',                 # Total lifetime rentals
    'rentals_since_last_service',    # Rentals since last fix
    'total_maintenance_count',       # How many times serviced
    'avg_rental_duration',           # Average rental length
    'anomalous_rental_count',        # Number of suspicious rentals
    'total_issues_logged',           # Total problems found
    'days_since_purchase'            # How old is the bike
]

def compute_score(self, bike_data, maintenance_logs, rentals):
    features = self.extract_features(...)  # Build feature array
    if self.model:                         # If XGBoost model exists
        score = model.predict_proba(features)  # ML prediction
    else:                                  # Fallback: rule-based scoring
        score = (days_since_service * 0.3) + (rentals_since_service * 0.25) + ...
    return round(score * 100, 1)  # Return 0-100
```
**Why XGBoost?** Interpretable ML model — SHAP values explain *why* a bike is high risk.

#### `rag_pipeline.py` — How AI Assistant Works
```
User asks: "Does bike #1 need servicing?"
    ↓
Step 1: Search vector store for bike #1's history
    ↓
Step 2: Retrieve top 5 relevant records (maintenance logs, rentals)
    ↓
Step 3: Build prompt: "Given these records... answer the question"
    ↓
Step 4: Send to Ollama LLM → Get natural language response
    ↓
Step 5: If LLM gives generic/bad answer → Use data-driven smart response
    ↓
Return answer + source records to user
```

#### `event_consumer.py` — Real-time Risk Updates
```python
def on_message(channel, method, properties, body):
    """Called whenever a rental/maintenance event arrives from RabbitMQ"""
    event = json.loads(body)
    bike_id = event['bicycle_id']
    # Recalculate risk score for this specific bike
    new_score = risk_scorer.compute_score(bike_data, logs, rentals)
    # Save to database
    save_risk_score(bike_id, new_score)
```
**Why?** Every time a bike is rented or serviced, its risk score updates **immediately** — not just nightly.

---

## 4. frontend/ — SvelteKit UI

### File Structure
```
frontend/
├── Dockerfile              # Build SvelteKit app into a Node.js container
├── package.json            # Dependencies (svelte, tailwindcss, chart.js)
├── svelte.config.js        # SvelteKit configuration (adapter-node for SSR)
├── vite.config.js          # Build tool configuration
├── tailwind.config.js      # Tailwind CSS theme/colors
├── src/
│   ├── app.html            # Root HTML template
│   ├── app.css             # Global styles (Tailwind imports)
│   ├── lib/
│   │   ├── api.js          # API client (fetch wrapper with auth headers)
│   │   ├── stores.js       # Svelte stores (auth state, notifications)
│   │   └── components/
│   │       ├── Navbar.svelte        # Navigation bar
│   │       ├── Notifications.svelte # Toast notifications
│   │       ├── RiskBadge.svelte     # Color-coded risk badge (Low/Medium/High)
│   │       └── RiskSparkline.svelte # Mini chart showing risk trend
│   └── routes/
│       ├── +layout.svelte    # App shell (navbar + content area)
│       ├── +page.svelte      # Home/landing page
│       ├── login/+page.svelte     # Login form
│       ├── register/+page.svelte  # Registration form
│       ├── dashboard/+page.svelte # Fleet overview dashboard
│       ├── bicycles/+page.svelte  # Bicycle list with risk badges
│       ├── bicycles/[id]/+page.svelte  # Single bike detail + history
│       ├── rentals/+page.svelte   # Rental management
│       ├── maintenance/+page.svelte # Maintenance logs
│       └── assistant/+page.svelte # AI chat interface
```

### Why SvelteKit?
- **File-based routing** — folder structure = URL structure (`/bicycles` → `routes/bicycles/+page.svelte`)
- **Reactive** — UI auto-updates when data changes (no manual DOM manipulation)
- **Fast** — Compiles to minimal JavaScript (smaller bundle than React)
- **SSR support** — Server-side rendering via adapter-node

### `lib/api.js` — API Client
```javascript
// Base URL comes from environment or defaults to same origin
const API_BASE = '';  // Empty = same domain (via NGINX proxy)

async function fetchWithAuth(url, options = {}) {
    const token = localStorage.getItem('token');
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` })
    };
    const response = await fetch(url, { ...options, headers });
    // Check if response is JSON (not HTML error page)
    if (!response.headers.get('content-type')?.includes('application/json')) {
        throw new Error('Server error. Please try again.');
    }
    return response.json();
}
```

### `lib/stores.js` — State Management
```javascript
import { writable } from 'svelte/store';

export const authStore = writable({ token: null, user: null });
export const notificationStore = writable([]);
export const riskScoreStore = writable({});  // {bike_id: {score, risk_level}}
```
**Why stores?** Share state between components without prop drilling.

---

## 5. infra/k8s/ — Kubernetes Manifests

### Why Kubernetes?
- **Auto-scaling** — HPA scales pods up/down based on CPU
- **Self-healing** — If a pod crashes, K8s auto-restarts it
- **Declarative** — YAML files describe desired state, K8s makes it happen
- **Network isolation** — NetworkPolicies act as firewalls between services

### File Explanations

| File | What it creates |
|------|----------------|
| `namespace.yaml` | Isolated environment `velotrack` — all resources go here |
| `configmap.yaml` | Non-sensitive config (service URLs, model name, DB name) |
| `secrets.yaml` | Sensitive data (passwords, JWT secret) — created via kubectl |
| `postgres.yaml` | PostgreSQL deployment + PVC (5Gi EBS disk) + Service |
| `rabbitmq.yaml` | RabbitMQ deployment + Service |
| `ollama.yaml` | Ollama LLM server deployment + Service |
| `user-service.yaml` | User service Deployment + Service + HPA |
| `bicycle-service.yaml` | Bicycle service Deployment + Service + HPA |
| `maintenance-rental-service.yaml` | Maintenance/Rental Deployment + Service + HPA |
| `maintenance-assistant-service.yaml` | Assistant Deployment + Service + HPA |
| `frontend.yaml` | Frontend Deployment + Service + HPA |
| `ingress.yaml` | NGINX Ingress — routes external traffic to services |
| `network-policies.yaml` | Firewall rules (who can talk to whom) |

### Representative K8s Manifest: `user-service.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment                   # "I want this many copies of this container running"
metadata:
  name: user-service
  namespace: velotrack
spec:
  replicas: 1                      # Start with 1 pod (HPA can scale to 3)
  selector:
    matchLabels:
      app: user-service            # How K8s finds pods belonging to this deployment
  template:
    metadata:
      labels:
        app: user-service
    spec:
      containers:
        - name: user-service
          image: <AWS_ACCOUNT_ID>.dkr.ecr.<REGION>.amazonaws.com/velotrack-user-service:latest
          # ↑ Pulled from ECR private registry (replaced by CI/CD pipeline)
          ports:
            - containerPort: 5001
          envFrom:
            - configMapRef:
                name: velotrack-config   # Load ALL keys from ConfigMap as env vars
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: velotrack-secrets
                  key: DATABASE_URL      # Sensitive — from Secret, not ConfigMap
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: velotrack-secrets
                  key: JWT_SECRET
          readinessProbe:              # K8s checks: "Is the service ready?"
            httpGet:
              path: /health
              port: 5001
            initialDelaySeconds: 10    # Wait 10s before first check
            periodSeconds: 10          # Check every 10s
          livenessProbe:               # K8s checks: "Is the service alive?"
            httpGet:
              path: /health
              port: 5001
            initialDelaySeconds: 15
            periodSeconds: 20
          resources:
            requests:                  # Minimum guaranteed resources
              cpu: 100m               # 0.1 CPU core
              memory: 128Mi           # 128 MB RAM
            limits:                    # Maximum allowed resources
              cpu: 500m               # 0.5 CPU core
              memory: 512Mi           # 512 MB RAM
---
apiVersion: v1
kind: Service                      # "How other pods find this service"
metadata:
  name: user-service
  namespace: velotrack
spec:
  selector:
    app: user-service              # Route traffic to pods with this label
  ports:
    - port: 5001                   # Service port
      targetPort: 5001             # Container port
  type: ClusterIP                  # Internal only (not exposed to internet)
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler     # "Auto-scale based on CPU usage"
metadata:
  name: user-service-hpa
  namespace: velotrack
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: user-service
  minReplicas: 1                   # Never go below 1 pod
  maxReplicas: 3                   # Never exceed 3 pods
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70   # Scale up when CPU > 70%
```

### `network-policies.yaml` — Firewall Rules
```yaml
# Rule: Only backend services can access PostgreSQL
# (Frontend can NOT directly access the database)
spec:
  podSelector:
    matchLabels:
      app: postgres
  ingress:
    - from:
        - podSelector: { matchLabels: { app: user-service } }
        - podSelector: { matchLabels: { app: bicycle-service } }
        - podSelector: { matchLabels: { app: maintenance-rental-service } }
        - podSelector: { matchLabels: { app: maintenance-assistant-service } }
      ports:
        - port: 5432
```
**Why Network Policies?** Principle of least privilege — each service can only access what it needs.

### `ingress.yaml` — Traffic Routing
```yaml
# Routes incoming HTTP requests to the correct service based on URL path:
# /api/auth/*      → user-service:5001
# /api/bicycles/*  → bicycle-service:5002
# /api/rentals/*   → maintenance-rental-service:5003
# /api/maintenance-assistant/* → maintenance-assistant-service:5004
# /api/risk-scores/* → maintenance-assistant-service:5004
# /* (everything else) → frontend:3000
```

---

## 6. infra/aws/ — AWS Infrastructure

| File | Purpose |
|------|---------|
| `eks-cluster.yaml` | EKS cluster definition (for `eksctl create cluster -f`) |
| `iam-policy.json` | IAM permissions (CloudWatch, ECR, S3 access) |
| `cloudwatch-namespace.yaml` | K8s namespace for logging components |
| `cloudwatch-agent.yaml` | Fluent Bit DaemonSet — collects logs from all pods → CloudWatch |
| `network-architecture.txt` | Documents VPC layout, subnets, NACLs, security groups |
| `deploy.sh` | One-click deployment script (all steps automated) |
| `cleanup.sh` | Deletes ALL AWS resources to stop billing |

---

## 7. infra/nginx/ — API Gateway

### `nginx.conf`
```nginx
# NGINX acts as the single entry point for all traffic.
# Users access http://localhost:8080 → NGINX routes to correct service.

upstream user_service { server user-service:5001; }
upstream bicycle_service { server bicycle-service:5002; }
upstream maintenance_rental_service { server maintenance-rental-service:5003; }
upstream maintenance_assistant_service { server maintenance-assistant-service:5004; }
upstream frontend { server frontend:3000; }

server {
    listen 80;

    # API routes → backend services
    location /api/auth/    { proxy_pass http://user_service/api/auth/; }
    location /api/users/   { proxy_pass http://user_service/api/users/; }
    location /api/bicycles/ { proxy_pass http://bicycle_service/api/bicycles/; }
    location /api/rentals/  { proxy_pass http://maintenance_rental_service/api/rentals/; }
    location /api/maintenance/ { proxy_pass http://maintenance_rental_service/api/maintenance/; }
    location /api/maintenance-assistant/ {
        proxy_pass http://maintenance_assistant_service/api/maintenance-assistant/;
        proxy_read_timeout 300s;  # AI responses can take time
    }
    location /api/risk-scores/ { proxy_pass http://maintenance_assistant_service/api/risk-scores/; }

    # Everything else → frontend
    location / { proxy_pass http://frontend/; }
}
```
**Why NGINX?** Single entry point. Frontend doesn't need to know which port each service runs on.

---

## 8. docs/ — Documentation

| File | Purpose |
|------|---------|
| `SETUP_GUIDE.md` | Complete step-by-step setup (local + AWS) |
| `DEPLOYMENT_LOG.md` | Record of all commands executed + errors resolved |
| `AWS_DEPLOYMENT_GUIDE.md` | AWS-specific architecture and deployment |
| `VeloTrack_API_Collection.postman.json` | Postman collection for localhost testing |
| `VeloTrack_AWS_API_Collection.postman.json` | Postman collection for AWS testing |

---

## 9. Service Communication Flow

```
┌─────────┐     HTTP      ┌─────────┐     HTTP      ┌──────────────┐
│ Browser │ ──────────────▸│  NGINX  │ ──────────────▸│ user-service │
│         │                │ Gateway │               │              │
└─────────┘                │ (:8080) │               └──────────────┘
                           │         │     HTTP      ┌──────────────┐
                           │         │ ──────────────▸│bicycle-service│
                           │         │               └──────────────┘
                           │         │     HTTP      ┌──────────────────┐
                           │         │ ──────────────▸│maint-rental-svc │
                           │         │               └────────┬─────────┘
                           │         │                        │
                           │         │     HTTP      ┌────────▼─────────┐
                           │         │ ──────────────▸│maint-assistant   │
                           └─────────┘               └────────┬─────────┘
                                                              │
                    ┌──────────────────────────────────────────┤
                    │                                          │
              ┌─────▼─────┐                            ┌──────▼──────┐
              │ RabbitMQ  │◀── publishes events ───────│   Ollama    │
              │           │                            │  (TinyLlama)│
              └─────┬─────┘                            └─────────────┘
                    │
                    │ consumes events
                    ▼
        ┌───────────────────────┐
        │ Risk Score Recalculation │
        └───────────────────────┘
```

### Communication Types:
1. **Synchronous (HTTP):** Frontend → NGINX → Backend services
2. **Synchronous (HTTP):** Service-to-service (e.g., rental-service calls bicycle-service to update status)
3. **Asynchronous (RabbitMQ):** rental-service publishes event → assistant-service consumes → recalculates risk

---

## 9.1 RabbitMQ — Detailed Explanation

### What is RabbitMQ?
RabbitMQ is a **message broker** — think of it as a **post office** between services. One service drops a message (letter) into a queue, and another service picks it up later. The sender and receiver don't need to be online at the same time.

### Why Do We Need RabbitMQ in VeloTrack?

**Problem without RabbitMQ:**
```
When a bike is returned (rental-service):
  1. Calculate rental cost ✅
  2. Update bike status to "Available" ✅
  3. Recalculate risk score for this bike ❌ (rental-service doesn't know how!)
  4. Update vector store with new history ❌ (rental-service doesn't know about FAISS!)
  5. Check for anomalies ❌ (not rental-service's job!)
```

If rental-service had to do all this directly, it would need to:
- Know about the risk scorer (tight coupling)
- Wait for risk calculation to finish (slow response to user)
- Break if assistant-service is down (fragile)

**Solution with RabbitMQ:**
```
When a bike is returned (rental-service):
  1. Calculate rental cost ✅
  2. Update bike status to "Available" ✅
  3. Publish event: "Hey, bike #1 was just returned!" → RabbitMQ ✅ (instant, fire-and-forget)
  4. Return response to user immediately ✅ (fast!)

Meanwhile, in the background (maintenance-assistant-service):
  1. Picks up the event from RabbitMQ
  2. Recalculates risk score for bike #1
  3. Updates vector store with new rental history
  4. Saves new score to database
  → User sees updated risk badge next time they load the page
```

### Where Exactly is RabbitMQ Used in Code?

#### 1. **Publisher** — `backend/maintenance-rental-service/events.py`
```python
import pika  # Python RabbitMQ client library
import json

def publish_event(event_type, data):
    """Send a message to RabbitMQ"""
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    
    # Declare the exchange (like a post office sorting center)
    channel.exchange_declare(exchange='velotrack.events', exchange_type='topic')
    
    message = {
        'event_type': event_type,
        'data': data,
        'timestamp': datetime.now().isoformat()
    }
    
    # Publish the message with a routing key
    channel.basic_publish(
        exchange='velotrack.events',        # Which exchange to send to
        routing_key=event_type,             # e.g., "rental.returned" or "maintenance.created"
        body=json.dumps(message)            # The actual message content
    )
    connection.close()

# Called when a bike is RETURNED:
def publish_rental_return_event(bike_id, rental_id, duration, is_anomalous):
    publish_event('rental.returned', {
        'bicycle_id': bike_id,
        'rental_id': rental_id,
        'duration_hours': duration,
        'is_anomalous': is_anomalous
    })

# Called when a MAINTENANCE LOG is created:
def publish_maintenance_event(bike_id, log_id):
    publish_event('maintenance.created', {
        'bicycle_id': bike_id,
        'log_id': log_id
    })
```

#### 2. **Consumer** — `backend/maintenance-assistant-service/event_consumer.py`
```python
import pika
import threading

def start_consumer():
    """Background thread that listens for events from RabbitMQ"""
    connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
    channel = connection.channel()
    
    # Declare same exchange (must match publisher)
    channel.exchange_declare(exchange='velotrack.events', exchange_type='topic')
    
    # Create a queue for this service
    result = channel.queue_declare(queue='risk-score-updates', durable=True)
    
    # Bind queue to exchange — listen for these event types:
    channel.queue_bind(exchange='velotrack.events', queue='risk-score-updates', routing_key='rental.returned')
    channel.queue_bind(exchange='velotrack.events', queue='risk-score-updates', routing_key='maintenance.created')
    
    # When a message arrives, call on_message()
    channel.basic_consume(queue='risk-score-updates', on_message_callback=on_message)
    channel.start_consuming()  # Block and wait for messages forever

def on_message(channel, method, properties, body):
    """Process a received event"""
    event = json.loads(body)
    bike_id = event['data']['bicycle_id']
    
    # Recalculate risk score for this specific bike
    bike_data = fetch_bike_data(bike_id)
    logs = fetch_maintenance_logs(bike_id)
    rentals = fetch_rentals(bike_id)
    new_score = risk_scorer.compute_score(bike_data, logs, rentals)
    
    # Save updated score
    save_risk_score(bike_id, new_score)
    
    # Re-index bike history in vector store (for AI assistant)
    rag_pipeline.index_bike_history(bike_id, logs, rentals)
    
    # Acknowledge the message (tell RabbitMQ: "I processed it, delete it")
    channel.basic_ack(delivery_tag=method.delivery_tag)

# Start consumer in a background thread when the service starts
consumer_thread = threading.Thread(target=start_consumer, daemon=True)
consumer_thread.start()
```

### RabbitMQ Concepts Used

| Concept | What it means | In our project |
|---------|--------------|----------------|
| **Exchange** | Post office sorting center — receives messages and routes them | `velotrack.events` (topic exchange) |
| **Queue** | Mailbox — stores messages until consumed | `risk-score-updates` |
| **Routing Key** | Address label — determines which queue gets the message | `rental.returned`, `maintenance.created` |
| **Publisher** | Service that sends messages | `maintenance-rental-service` |
| **Consumer** | Service that receives messages | `maintenance-assistant-service` |
| **Topic Exchange** | Routes messages based on pattern matching | `rental.*` matches `rental.returned`, `rental.checkout` |

### Flow Diagram
```
┌─────────────────────────┐
│ maintenance-rental-svc  │
│                         │
│ User returns bike #1    │
│    ↓                    │
│ publish_event(          │
│   'rental.returned',   │
│   {bike_id: 1, ...}    │──────┐
│ )                       │      │
└─────────────────────────┘      │
                                 ▼
                    ┌─────────────────────┐
                    │      RabbitMQ       │
                    │                     │
                    │ Exchange:           │
                    │ "velotrack.events"  │
                    │      │              │
                    │      ▼              │
                    │ Queue:             │
                    │ "risk-score-updates"│
                    └──────────┬──────────┘
                               │
                               ▼
               ┌───────────────────────────────┐
               │ maintenance-assistant-service  │
               │                               │
               │ on_message() triggered:       │
               │   1. Fetch bike #1 data       │
               │   2. Recalculate risk score   │
               │   3. Save score: 67 (High)    │
               │   4. Update vector store      │
               │   5. Acknowledge message      │
               └───────────────────────────────┘
```

### How to Login to RabbitMQ Dashboard

#### Local (Docker Compose):
- **URL:** http://localhost:15672
- **Username:** `guest`
- **Password:** `guest`

#### What You'll See in the Dashboard:

**1. Overview Tab:**
- Total messages queued/delivered/published
- Message rates (messages/second)
- Node status (running, memory usage)

**2. Connections Tab:**
- Shows which services are connected
- You'll see 2 connections:
  - `maintenance-rental-service` (publisher)
  - `maintenance-assistant-service` (consumer)

**3. Exchanges Tab:**
- `velotrack.events` — our custom topic exchange
- Click on it to see:
  - Bindings (which queues are connected)
  - Message rates in/out

**4. Queues Tab:**
- `risk-score-updates` — our queue
- Shows:
  - **Ready:** Messages waiting to be processed
  - **Unacked:** Messages being processed right now
  - **Total:** Total messages in queue
  - **Message rate:** How fast messages are being consumed

**5. What to Show in Demo:**
- Click on `velotrack.events` exchange → Show bindings
- Click on `risk-score-updates` queue → Show message count
- Return a bike in the app → Watch the message count briefly spike then go back to 0 (processed!)

### When Does RabbitMQ Receive Messages?

| User Action | Event Published | What Happens |
|-------------|----------------|--------------|
| Return a bike (rental) | `rental.returned` | Risk score recalculated for that bike |
| Create maintenance log | `maintenance.created` | Risk score recalculated + vector store updated |
| Checkout a bike | `rental.checkout` | Risk score recalculated (rental count increased) |

### Why Not Just Call the API Directly?

| Approach | Problem |
|----------|---------|
| **Rental service directly calls assistant service API** | If assistant is down, rental fails. User gets error for something unrelated to their rental. |
| **With RabbitMQ (our approach)** | Rental completes instantly. If assistant is down, messages queue up. When assistant comes back, it processes all queued messages. No data lost. |

### Key Benefits for This Project:
1. **Decoupling** — Rental service doesn't know/care about risk scoring
2. **Resilience** — If assistant crashes, messages wait in queue (not lost)
3. **Speed** — User gets rental response instantly (risk calc happens async)
4. **Scalability** — Can add more consumers if message volume grows

---

## 10. Why Each Technology Was Chosen

| Technology | Why? | Alternative Considered |
|-----------|------|----------------------|
| **Flask** | Lightweight Python framework, perfect for microservices (not a monolithic app) | Django (too heavy), FastAPI (less mature ecosystem) |
| **SvelteKit** | Fast, reactive, file-based routing, small bundle size | React (heavier), Next.js (more complex) |
| **PostgreSQL** | Mature SQL database, relational data (bikes, users, rentals have relationships) | MongoDB (NoSQL — harder for relational queries) |
| **RabbitMQ** | Reliable message delivery, topic-based routing, management UI | Kafka (overkill for this scale), Redis pub/sub (no durability) |
| **Ollama** | Run AI models locally, no API costs, privacy (data stays in-house) | OpenAI API (expensive, data leaves network) |
| **TinyLlama** | 1.1B params — fast on CPU, loads in seconds | Mistral 7B (too slow on 8GB RAM systems) |
| **FAISS** | Fast vector similarity search, runs in-memory, no external service needed | Chroma (heavier), Pinecone (paid SaaS) |
| **XGBoost** | Fast training, interpretable via SHAP, works with small datasets | Neural networks (need more data), Random Forest (less accurate) |
| **Docker** | Consistent environments, "works on my machine" problem solved | VMs (slower, heavier) |
| **Kubernetes (EKS)** | Auto-scaling, self-healing, declarative deployments | ECS (less portable), plain EC2 (manual scaling) |
| **NGINX** | Battle-tested reverse proxy, load balancing, simple config | Traefik (more complex), HAProxy (less features) |
| **JWT** | Stateless auth — no session storage, each request self-contained | Session cookies (requires sticky sessions), OAuth2 (overkill) |
| **GitHub Actions** | Free CI/CD, native GitHub integration, YAML-based | Jenkins (self-hosted), GitLab CI (different platform) |
| **AWS ECR** | Private Docker registry in same AWS account as EKS | Docker Hub (public by default) |
| **Tailwind CSS** | Utility-first, rapid prototyping, no custom CSS files needed | Bootstrap (opinionated), plain CSS (slower development) |

