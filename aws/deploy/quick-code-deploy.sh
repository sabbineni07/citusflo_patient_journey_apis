#!/bin/bash

# CitusFlo Patient Journey APIs - Quick Code-Only Deployment Script
# This script only updates the application code without touching CloudFormation

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration
AWS_REGION="us-east-1"
ECR_REPO_NAME="production-citusflo-patient-journey-api"
IMAGE_TAG="latest"
CONTAINER_NAME="patient-api"
ECS_CLUSTER_NAME="production-citusflo-patient-cluster"
ECS_SERVICE_NAME="production-citusflo-patient-service"

print_status "🚀 Starting Quick Code-Only Deployment"
print_status "This will only update the application code (build, push, deploy)"
print_status "CloudFormation stack will NOT be modified"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    print_error "AWS CLI not configured or no valid credentials"
    exit 1
fi

# Get AWS account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
print_status "Using AWS Account: $AWS_ACCOUNT_ID"

# Check if required tools are installed
command -v docker >/dev/null 2>&1 || { print_error "Docker is required but not installed. Aborting."; exit 1; }
command -v aws >/dev/null 2>&1 || { print_error "AWS CLI is required but not installed. Aborting."; exit 1; }

# Verify ECS service exists
print_status "🔍 Verifying ECS service exists..."
if ! aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER_NAME --services $ECS_SERVICE_NAME --query 'services[0].serviceName' --output text 2>/dev/null | grep -q "$ECS_SERVICE_NAME"; then
    print_error "ECS service '$ECS_SERVICE_NAME' not found in cluster '$ECS_CLUSTER_NAME'"
    print_error "Please verify the service name and cluster name"
    exit 1
fi
print_success "ECS service verified"

# Login to ECR
print_status "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build Docker image
print_status "🔨 Building Docker image..."
docker build --platform linux/amd64 -t $CONTAINER_NAME .

# Tag and push image
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG"
docker tag $CONTAINER_NAME:latest $ECR_URI

print_status "📤 Pushing image to ECR: $ECR_URI"
docker push $ECR_URI

print_success "Image pushed successfully: $ECR_URI"

# Force ECS service deployment with new image
print_status "🔄 Updating ECS service to use new image..."
aws ecs update-service \
    --region $AWS_REGION \
    --cluster $ECS_CLUSTER_NAME \
    --service $ECS_SERVICE_NAME \
    --force-new-deployment \
    > /dev/null

print_success "ECS service deployment triggered"

# Wait for service to stabilize
print_status "⏳ Waiting for ECS service to stabilize (this may take 2-3 minutes)..."
aws ecs wait services-stable \
    --region $AWS_REGION \
    --cluster $ECS_CLUSTER_NAME \
    --services $ECS_SERVICE_NAME

print_success "✅ Service is stable and running new code!"

# Test the deployment
print_status "🧪 Testing deployment..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://api.citusflo.com/health" 2>/dev/null || echo "000")

if [[ "$HEALTH_RESPONSE" == "200" ]]; then
    print_success "Health endpoint working: https://api.citusflo.com/health"
else
    print_warning "Health endpoint returned status: $HEALTH_RESPONSE"
fi

# Display deployment summary
echo ""
print_success "🎉 Quick code deployment completed successfully!"
echo ""
echo "📊 DEPLOYMENT SUMMARY:"
echo "======================"
echo "ECS Cluster: $ECS_CLUSTER_NAME"
echo "ECS Service: $ECS_SERVICE_NAME"
echo "ECR Image: $ECR_URI"
echo "Region: $AWS_REGION"
echo ""
echo "🌐 APPLICATION URL:"
echo "==================="
echo "Health Check: https://api.citusflo.com/health"
echo "API Base: https://api.citusflo.com/api"
echo ""
echo "📝 NEW ENDPOINTS DEPLOYED:"
echo "=========================="
echo "✅ GET /api/auth/user/<value>"
echo "   - Get user by username or email"
echo ""
echo "✅ GET /api/auth/user/<value>/webauthn"
echo "   - Check if user has WebAuthn setup"
echo ""
echo "💡 To view service logs:"
echo "aws logs tail /ecs/production-citusflo-patient-journey-api --follow --region $AWS_REGION"
echo ""




