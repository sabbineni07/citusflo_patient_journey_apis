#!/bin/bash

# AWS Deployment Script for CitusFlo Patient Journey APIs
# This script deploys the CitusFlo Patient Journey APIs to AWS using ECS Fargate

set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="citusflo-patient-journey-api"
ECS_CLUSTER="production-citusflo-patient-cluster"
ECS_SERVICE="production-citusflo-patient-service"
ENVIRONMENT="production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting AWS deployment for CitusFlo Patient Journey APIs...${NC}"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}Error: AWS CLI is not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Create ECR repository if it doesn't exist
echo -e "${YELLOW}Creating ECR repository...${NC}"
aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION > /dev/null 2>&1 || \
aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION

# Get ECR login token
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -t $ECR_REPOSITORY:latest .

# Tag image for ECR
docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Push image to ECR
echo -e "${YELLOW}Pushing image to ECR...${NC}"
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest

# Deploy CloudFormation stack
echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"
aws cloudformation deploy \
    --template-file aws/cloudformation-template.yaml \
    --stack-name citusflo-patient-journey-api-infrastructure \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        DatabasePassword="$(openssl rand -base64 32)" \
        SecretKey="$(openssl rand -base64 32)" \
        JWTSecretKey="$(openssl rand -base64 32)" \
    --capabilities CAPABILITY_IAM \
    --region $AWS_REGION

# Update ECS service to use new image
echo -e "${YELLOW}Updating ECS service...${NC}"
aws ecs update-service \
    --cluster $ECS_CLUSTER \
    --service $ECS_SERVICE \
    --force-new-deployment \
    --region $AWS_REGION

# Wait for deployment to complete
echo -e "${YELLOW}Waiting for deployment to complete...${NC}"
aws ecs wait services-stable \
    --cluster $ECS_CLUSTER \
    --services $ECS_SERVICE \
    --region $AWS_REGION

# Get load balancer DNS name
LB_DNS=$(aws cloudformation describe-stacks \
    --stack-name citusflo-patient-journey-api-infrastructure \
    --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' \
    --output text \
    --region $AWS_REGION)

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo -e "${GREEN}Application URL: http://$LB_DNS${NC}"
echo -e "${GREEN}Health Check: http://$LB_DNS/health${NC}"

# Run health check
echo -e "${YELLOW}Running health check...${NC}"
sleep 30  # Wait for service to be fully ready

if curl -f http://$LB_DNS/health > /dev/null 2>&1; then
    echo -e "${GREEN}Health check passed!${NC}"
else
    echo -e "${RED}Health check failed. Please check the logs.${NC}"
    echo -e "${YELLOW}To check logs, run:${NC}"
    echo "aws logs tail /ecs/$ENVIRONMENT-citusflo-patient-api --follow --region $AWS_REGION"
fi

echo -e "${GREEN}Deployment script completed!${NC}"
