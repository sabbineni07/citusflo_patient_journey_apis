#!/bin/bash

# CitusFlo Patient Journey APIs - Comprehensive AWS Deployment Script
# This script deploys the application to AWS ECS Fargate with all necessary infrastructure

set -e

# Configuration
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REPOSITORY="citusflo-patient-journey-api"
ECS_CLUSTER="production-citusflo-patient-cluster"
ECS_SERVICE="production-citusflo-patient-service"
ENVIRONMENT="production"

# VPC Configuration (Update these values for your environment)
VPC_ID="vpc-0204102b87fc02753"  # Your VPC ID
PUBLIC_SUBNET_1="subnet-035661356dc83d054"  # Public subnet in us-east-1b
PUBLIC_SUBNET_2="subnet-0bdb6dd4f4f780305"  # Public subnet in us-east-1a
ALL_SUBNETS="subnet-084c887eef0bbb19f,subnet-035661356dc83d054,subnet-0bdb6dd4f4f780305,subnet-0a2613df7d19ca3e3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 CitusFlo Patient Journey APIs - AWS Deployment${NC}"
echo -e "${BLUE}================================================${NC}"

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}📋 Checking prerequisites...${NC}"
    
    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        echo -e "${RED}❌ AWS CLI is not installed. Please install AWS CLI first.${NC}"
        exit 1
    fi
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed. Please install Docker first.${NC}"
        exit 1
    fi
    
    # Check AWS credentials
    if ! aws sts get-caller-identity > /dev/null 2>&1; then
        echo -e "${RED}❌ AWS CLI is not configured. Please run 'aws configure' first.${NC}"
        exit 1
    fi
    
    # Check Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All prerequisites met${NC}"
}

# Function to create ECR repository
create_ecr_repository() {
    echo -e "${YELLOW}📦 Creating ECR repository...${NC}"
    
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories --repository-names $ECR_REPOSITORY --region $AWS_REGION > /dev/null 2>&1 || \
    aws ecr create-repository --repository-name $ECR_REPOSITORY --region $AWS_REGION
    
    echo -e "${GREEN}✅ ECR repository ready${NC}"
}

# Function to build and push Docker image
build_and_push_image() {
    echo -e "${YELLOW}🐳 Building and pushing Docker image...${NC}"
    
    # Get ECR login token
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    # Build Docker image with correct architecture
    echo -e "${YELLOW}Building Docker image for x86_64 architecture...${NC}"
    docker build --platform linux/amd64 -t $ECR_REPOSITORY:latest .
    
    # Tag image for ECR
    docker tag $ECR_REPOSITORY:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
    
    # Push image to ECR
    docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest
    
    echo -e "${GREEN}✅ Docker image built and pushed successfully${NC}"
}

# Function to create CloudFormation stack
deploy_infrastructure() {
    echo -e "${YELLOW}🏗️  Deploying AWS infrastructure...${NC}"
    
    # Generate secure passwords
    DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    SECRET_KEY=$(openssl rand -base64 32)
    JWT_SECRET_KEY=$(openssl rand -base64 32)
    
    echo -e "${YELLOW}Generated secure passwords for deployment${NC}"
    
    # Deploy CloudFormation stack
    aws cloudformation deploy \
        --template-file cloudformation.yaml \
        --stack-name citusflo-patient-journey-api-infrastructure \
        --parameter-overrides \
            Environment=$ENVIRONMENT \
            VpcId=$VPC_ID \
            SubnetIds=$ALL_SUBNETS \
            AlbSubnetIds="$PUBLIC_SUBNET_1,$PUBLIC_SUBNET_2" \
            DatabasePassword="$DB_PASSWORD" \
            SecretKey="$SECRET_KEY" \
            JWTSecretKey="$JWT_SECRET_KEY" \
        --capabilities CAPABILITY_IAM \
        --region $AWS_REGION
    
    echo -e "${GREEN}✅ Infrastructure deployed successfully${NC}"
}

# Function to update ECS service
update_ecs_service() {
    echo -e "${YELLOW}🔄 Updating ECS service...${NC}"
    
    # Update ECS service to use new image
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
    
    echo -e "${GREEN}✅ ECS service updated successfully${NC}"
}

# Function to verify deployment
verify_deployment() {
    echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
    
    # Get application URLs
    APP_URL=$(aws cloudformation describe-stacks \
        --stack-name citusflo-patient-journey-api-infrastructure \
        --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
        --output text \
        --region $AWS_REGION)
    
    HEALTH_URL=$(aws cloudformation describe-stacks \
        --stack-name citusflo-patient-journey-api-infrastructure \
        --query 'Stacks[0].Outputs[?OutputKey==`HealthCheckURL`].OutputValue' \
        --output text \
        --region $AWS_REGION)
    
    echo -e "${GREEN}Application URLs:${NC}"
    echo -e "${GREEN}  • Application: $APP_URL${NC}"
    echo -e "${GREEN}  • Health Check: $HEALTH_URL${NC}"
    
    # Wait for service to be fully ready
    echo -e "${YELLOW}Waiting for service to be ready...${NC}"
    sleep 30
    
    # Test health check
    if curl -f $HEALTH_URL > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Health check passed!${NC}"
        echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    else
        echo -e "${RED}❌ Health check failed. Please check the logs.${NC}"
        echo -e "${YELLOW}To check logs, run:${NC}"
        echo "aws logs tail /ecs/$ENVIRONMENT-citusflo-patient-api --follow --region $AWS_REGION"
        exit 1
    fi
}

# Function to show deployment summary
show_summary() {
    echo -e "${BLUE}📊 Deployment Summary${NC}"
    echo -e "${BLUE}====================${NC}"
    echo -e "${GREEN}✅ ECR Repository: $ECR_REPOSITORY${NC}"
    echo -e "${GREEN}✅ ECS Cluster: $ECS_CLUSTER${NC}"
    echo -e "${GREEN}✅ ECS Service: $ECS_SERVICE${NC}"
    echo -e "${GREEN}✅ Load Balancer: production-patient-lb${NC}"
    echo -e "${GREEN}✅ Database: PostgreSQL RDS${NC}"
    echo -e "${GREEN}✅ Environment: $ENVIRONMENT${NC}"
    
    echo -e "${YELLOW}🔧 Configuration:${NC}"
    echo -e "${YELLOW}  • VPC: $VPC_ID${NC}"
    echo -e "${YELLOW}  • Public Subnets: $PUBLIC_SUBNET_1, $PUBLIC_SUBNET_2${NC}"
    echo -e "${YELLOW}  • All Subnets: $ALL_SUBNETS${NC}"
    
    echo -e "${BLUE}🔗 Useful Commands:${NC}"
    echo -e "${BLUE}  • View logs: aws logs tail /ecs/$ENVIRONMENT-citusflo-patient-api --follow --region $AWS_REGION${NC}"
    echo -e "${BLUE}  • Check service: aws ecs describe-services --cluster $ECS_CLUSTER --services $ECS_SERVICE --region $AWS_REGION${NC}"
    echo -e "${BLUE}  • Delete stack: aws cloudformation delete-stack --stack-name citusflo-patient-journey-api-infrastructure --region $AWS_REGION${NC}"
}

# Main execution
main() {
    check_prerequisites
    create_ecr_repository
    build_and_push_image
    deploy_infrastructure
    update_ecs_service
    verify_deployment
    show_summary
}

# Run main function
main "$@"
