#!/bin/bash
# ─────────────────────────────────────────────────────────────
# VeloTrack AWS Setup Script — Run ONCE to configure all AWS resources
# ─────────────────────────────────────────────────────────────
set -e

REGION="us-east-1"
CLUSTER_NAME="velotrack-cluster"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "═══════════════════════════════════════════════"
echo "  VeloTrack AWS Deployment — Account: $ACCOUNT_ID"
echo "═══════════════════════════════════════════════"

# ─── Step 1: Create ECR Repositories (Private Container Registry) ───
echo ""
echo "▶ Step 1: Creating ECR Repositories..."
for svc in user-service bicycle-service maintenance-rental-service maintenance-assistant-service frontend; do
  aws ecr create-repository --repository-name velotrack-${svc} --region $REGION 2>/dev/null || echo "  ✓ velotrack-${svc} already exists"
done
echo "✅ ECR repositories ready"

# ─── Step 2: Push images from Docker Hub to ECR ───
echo ""
echo "▶ Step 2: Pushing images to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

for svc in user-service bicycle-service maintenance-rental-service maintenance-assistant-service frontend; do
  echo "  Pushing velotrack-${svc}..."
  docker tag tanmaypagar510/velotrack-${svc}:latest ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/velotrack-${svc}:latest
  docker push ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/velotrack-${svc}:latest
done
echo "✅ All images pushed to ECR"

# ─── Step 3: Create IAM Policy ───
echo ""
echo "▶ Step 3: Creating IAM Policy..."
aws iam create-policy \
  --policy-name VeloTrackEKSPolicy \
  --policy-document file://infra/aws/iam-policy.json \
  --description "VeloTrack EKS cluster policy — least privilege" 2>/dev/null || echo "  ✓ Policy already exists"
echo "✅ IAM Policy created"

# ─── Step 4: Create EKS Cluster ───
echo ""
echo "▶ Step 4: Creating EKS Cluster (this takes ~15 minutes)..."
eksctl create cluster -f infra/aws/eks-cluster.yaml
echo "✅ EKS Cluster created"

# ─── Step 5: Update kubeconfig ───
echo ""
echo "▶ Step 5: Configuring kubectl..."
aws eks update-kubeconfig --name $CLUSTER_NAME --region $REGION
echo "✅ kubectl configured"

# ─── Step 6: Install NGINX Ingress Controller ───
echo ""
echo "▶ Step 6: Installing NGINX Ingress Controller..."
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/aws/deploy.yaml
echo "  Waiting for ingress controller..."
sleep 30
echo "✅ NGINX Ingress installed"

# ─── Step 7: Install Metrics Server (for HPA) ───
echo ""
echo "▶ Step 7: Installing Metrics Server..."
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
echo "✅ Metrics Server installed"

# ─── Step 8: Update K8s manifests with ECR registry ───
echo ""
echo "▶ Step 8: Updating K8s manifests with ECR registry..."
cd infra/k8s
find . -name '*.yaml' -exec sed -i "s|<DOCKERHUB_USERNAME>|${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com|g" {} \;
cd ../..
echo "✅ Manifests updated"

# ─── Step 9: Deploy VeloTrack ───
echo ""
echo "▶ Step 9: Deploying VeloTrack to EKS..."
kubectl apply -f infra/k8s/namespace.yaml
kubectl apply -f infra/k8s/configmap.yaml
kubectl apply -f infra/k8s/secrets.yaml
kubectl apply -f infra/k8s/network-policies.yaml
kubectl apply -f infra/k8s/postgres.yaml
kubectl apply -f infra/k8s/rabbitmq.yaml

echo "  Waiting for PostgreSQL..."
kubectl -n velotrack rollout status deployment/postgres --timeout=120s
echo "  Waiting for RabbitMQ..."
kubectl -n velotrack rollout status deployment/rabbitmq --timeout=120s

kubectl apply -f infra/k8s/user-service.yaml
kubectl apply -f infra/k8s/bicycle-service.yaml
kubectl apply -f infra/k8s/maintenance-rental-service.yaml
kubectl apply -f infra/k8s/maintenance-assistant-service.yaml
kubectl apply -f infra/k8s/frontend.yaml
kubectl apply -f infra/k8s/ingress.yaml

echo "  Waiting for services to start..."
kubectl -n velotrack rollout status deployment/user-service --timeout=180s
kubectl -n velotrack rollout status deployment/bicycle-service --timeout=180s
kubectl -n velotrack rollout status deployment/maintenance-rental-service --timeout=180s
kubectl -n velotrack rollout status deployment/frontend --timeout=120s

# ─── Step 10: Setup CloudWatch Logging ───
echo ""
echo "▶ Step 10: Setting up CloudWatch Logging..."
cd infra/aws
sed -i "s|<AWS_ACCOUNT_ID>|${ACCOUNT_ID}|g" cloudwatch-agent.yaml
cd ../..
kubectl apply -f infra/aws/cloudwatch-namespace.yaml
kubectl apply -f infra/aws/cloudwatch-agent.yaml
echo "✅ CloudWatch logging enabled"

# ─── Step 11: Create S3 Bucket for ML Models ───
echo ""
echo "▶ Step 11: Creating S3 bucket for ML models..."
aws s3 mb s3://velotrack-models-${ACCOUNT_ID} --region $REGION 2>/dev/null || echo "  ✓ Bucket already exists"
echo "✅ S3 bucket ready"

# ─── Step 12: Create CloudWatch Alarms ───
echo ""
echo "▶ Step 12: Creating CloudWatch Alarms..."
aws cloudwatch put-metric-alarm \
  --alarm-name "VeloTrack-HighCPU" \
  --alarm-description "EKS Node CPU above 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/EC2 \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region $REGION

aws cloudwatch put-metric-alarm \
  --alarm-name "VeloTrack-HighMemory" \
  --alarm-description "EKS Node Memory above 85%" \
  --metric-name mem_used_percent \
  --namespace CWAgent \
  --statistic Average \
  --period 300 \
  --threshold 85 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  --region $REGION
echo "✅ CloudWatch alarms created"

# ─── Done ───
echo ""
echo "═══════════════════════════════════════════════"
echo "  ✅ VeloTrack deployed successfully!"
echo "═══════════════════════════════════════════════"
echo ""
echo "── Status ──"
kubectl -n velotrack get pods
echo ""
kubectl -n velotrack get svc
echo ""
kubectl -n velotrack get hpa
echo ""

# Get Load Balancer URL
echo "── Application URL ──"
LB_URL=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)
if [ -n "$LB_URL" ]; then
  echo "🌐 Open: http://$LB_URL"
else
  echo "⏳ Load Balancer URL not ready yet. Run:"
  echo "   kubectl get svc -n ingress-nginx"
fi
echo ""
echo "── Useful Commands ──"
echo "  kubectl -n velotrack get pods -o wide"
echo "  kubectl -n velotrack logs -l app=user-service"
echo "  kubectl -n velotrack get hpa"
echo "  kubectl -n velotrack scale deployment/bicycle-service --replicas=3"

