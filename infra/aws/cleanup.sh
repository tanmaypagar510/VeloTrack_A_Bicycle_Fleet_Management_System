#!/bin/bash
# ─────────────────────────────────────────────────────────────
# VeloTrack AWS Cleanup — Deletes ALL AWS resources to stop billing
# ⚠️  WARNING: This deletes everything! Only run when done.
# ─────────────────────────────────────────────────────────────
set -e

REGION="us-east-1"
CLUSTER_NAME="velotrack-cluster"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "⚠️  This will DELETE all VeloTrack AWS resources!"
echo "   Press Ctrl+C within 5 seconds to cancel..."
sleep 5

echo ""
echo "▶ Deleting K8s workloads..."
kubectl delete namespace velotrack --ignore-not-found
kubectl delete namespace amazon-cloudwatch --ignore-not-found

echo ""
echo "▶ Deleting NGINX Ingress..."
kubectl delete -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.10.0/deploy/static/provider/aws/deploy.yaml --ignore-not-found

echo ""
echo "▶ Deleting EKS Cluster (takes ~10 minutes)..."
eksctl delete cluster --name $CLUSTER_NAME --region $REGION

echo ""
echo "▶ Deleting ECR Repositories..."
for svc in user-service bicycle-service maintenance-rental-service maintenance-assistant-service frontend; do
  aws ecr delete-repository --repository-name velotrack-${svc} --region $REGION --force 2>/dev/null || true
done

echo ""
echo "▶ Deleting S3 bucket..."
aws s3 rb s3://velotrack-models-${ACCOUNT_ID} --force 2>/dev/null || true

echo ""
echo "▶ Deleting CloudWatch log groups..."
aws logs delete-log-group --log-group-name /velotrack/eks/application --region $REGION 2>/dev/null || true

echo ""
echo "▶ Deleting CloudWatch alarms..."
aws cloudwatch delete-alarms --alarm-names "VeloTrack-HighCPU" "VeloTrack-HighMemory" --region $REGION 2>/dev/null || true

echo ""
echo "✅ All VeloTrack AWS resources deleted. No further billing."

