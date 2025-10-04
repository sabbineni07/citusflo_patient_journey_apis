#!/bin/bash

# CitusFlo Patient Journey APIs - Production Deployment Script
# This script handles complete deployment with HTTPS support and custom domain

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
STACK_NAME="citusflo-patient-journey-api"
ECR_REPO_NAME="production-citusflo-patient-journey-api"
IMAGE_TAG="latest"
CONTAINER_NAME="patient-api"
DOMAIN_NAME="citusflo.com"
API_SUBDOMAIN="api.citusflo.com"

# Parse command line arguments
DEPLOYMENT_TYPE="full"  # full, update, https-only
CUSTOM_DOMAIN="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        --domain)
            CUSTOM_DOMAIN="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [--type full|update|https-only] [--domain]"
            echo ""
            echo "Options:"
            echo "  --type full        Full deployment (default)"
            echo "  --type update      Update existing deployment"
            echo "  --type https-only  Add HTTPS support only"
            echo "  --domain           Enable custom domain setup"
            echo "  --help             Show this help"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

print_status "🚀 Starting CitusFlo Patient Journey APIs Deployment"
print_status "Deployment Type: $DEPLOYMENT_TYPE"
print_status "Custom Domain: $CUSTOM_DOMAIN"

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

# Get VPC and subnet information
print_status "🔍 Getting VPC and subnet information..."

# Get default VPC or first available VPC
VPC_ID=$(aws ec2 describe-vpcs --region $AWS_REGION --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    print_error "No VPC found in region $AWS_REGION"
    exit 1
fi

print_status "Using VPC: $VPC_ID"

# Get all subnets in the VPC
ALL_SUBNETS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[].SubnetId' --output text | tr '\t' ',')

# Get public subnets for ALB (first 2 subnets)
ALB_SUBNETS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[:2].SubnetId' --output text | tr '\t' ',')

print_status "All subnets: $ALL_SUBNETS"
print_status "ALB subnets: $ALB_SUBNETS"

# Generate secure passwords
print_status "🔐 Generating secure passwords..."
DB_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
SECRET_KEY=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 64)
JWT_SECRET=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 64)

print_success "Generated secure credentials"

# ECR setup
print_status "🐳 Setting up ECR repository..."

# Create ECR repository if it doesn't exist
if ! aws ecr describe-repositories --region $AWS_REGION --repository-names $ECR_REPO_NAME &>/dev/null; then
    print_status "Creating ECR repository: $ECR_REPO_NAME"
    aws ecr create-repository --region $AWS_REGION --repository-name $ECR_REPO_NAME
else
    print_status "ECR repository already exists: $ECR_REPO_NAME"
fi

# Login to ECR
print_status "Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Docker image
print_status "🔨 Building Docker image..."
docker build --platform linux/amd64 -t $CONTAINER_NAME .

# Tag and push image
ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG"
docker tag $CONTAINER_NAME:latest $ECR_URI

print_status "Pushing image to ECR: $ECR_URI"
docker push $ECR_URI

# Get the image digest
IMAGE_DIGEST=$(aws ecr describe-images --region $AWS_REGION --repository-name $ECR_REPO_NAME --image-ids imageTag=$IMAGE_TAG --query 'imageDetails[0].imageDigest' --output text)
FULL_IMAGE_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME@$IMAGE_DIGEST"

print_success "Image pushed successfully: $FULL_IMAGE_URI"

# Deploy CloudFormation stack
print_status "☁️  Deploying CloudFormation stack..."

# Choose template based on deployment type
if [ "$DEPLOYMENT_TYPE" = "https-only" ]; then
    TEMPLATE_FILE="cloudformation-https.yaml"
    STACK_NAME="$STACK_NAME-https"
else
    TEMPLATE_FILE="cloudformation.yaml"
fi

# Check if stack exists
if aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME &>/dev/null; then
    print_status "Stack exists, updating..."
    OPERATION="update-stack"
else
    print_status "Creating new stack..."
    OPERATION="create-stack"
fi

# Deploy the stack
if [ "$CUSTOM_DOMAIN" = "true" ]; then
    aws cloudformation $OPERATION \
        --region $AWS_REGION \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --capabilities CAPABILITY_IAM \
        --parameters \
            ParameterKey=Environment,ParameterValue=production \
            ParameterKey=VpcId,ParameterValue=$VPC_ID \
            ParameterKey=SubnetIds,ParameterValue="$ALL_SUBNETS" \
            ParameterKey=AlbSubnetIds,ParameterValue="$ALB_SUBNETS" \
            ParameterKey=DatabasePassword,ParameterValue="$DB_PASSWORD" \
            ParameterKey=SecretKey,ParameterValue="$SECRET_KEY" \
            ParameterKey=JWTSecretKey,ParameterValue="$JWT_SECRET" \
            ParameterKey=DomainName,ParameterValue="$API_SUBDOMAIN" \
        --tags \
            Key=Project,Value=CitusFlo \
            Key=Environment,Value=Production \
            Key=Service,Value=PatientJourneyAPI
else
    aws cloudformation $OPERATION \
        --region $AWS_REGION \
        --stack-name $STACK_NAME \
        --template-body file://$TEMPLATE_FILE \
        --capabilities CAPABILITY_IAM \
        --parameters \
            ParameterKey=Environment,ParameterValue=production \
            ParameterKey=VpcId,ParameterValue=$VPC_ID \
            ParameterKey=SubnetIds,ParameterValue="$ALL_SUBNETS" \
            ParameterKey=AlbSubnetIds,ParameterValue="$ALB_SUBNETS" \
            ParameterKey=DatabasePassword,ParameterValue="$DB_PASSWORD" \
            ParameterKey=SecretKey,ParameterValue="$SECRET_KEY" \
            ParameterKey=JWTSecretKey,ParameterValue="$JWT_SECRET" \
        --tags \
            Key=Project,Value=CitusFlo \
            Key=Environment,Value=Production \
            Key=Service,Value=PatientJourneyAPI
fi

print_status "Waiting for stack operation to complete..."
aws cloudformation wait stack-${OPERATION%-stack}-complete --region $AWS_REGION --stack-name $STACK_NAME

# Get stack outputs
print_status "📋 Getting deployment information..."
LB_DNS=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text)
APP_URL=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' --output text 2>/dev/null || echo "Not available")

# Wait for ECS service to be stable
print_status "⏳ Waiting for ECS service to be stable..."
ECS_CLUSTER=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' --output text)
ECS_SERVICE=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSServiceName`].OutputValue' --output text)

aws ecs wait services-stable --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE

# Test the deployment
print_status "🧪 Testing deployment..."

# Test health endpoint
print_status "Testing health endpoint..."
HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -k "https://$LB_DNS/health" || echo "000")
if [[ "$HEALTH_RESPONSE" == "200" ]]; then
    print_success "Health endpoint working"
else
    print_warning "Health endpoint test returned status: $HEALTH_RESPONSE"
fi

# Test API endpoint
print_status "Testing API endpoint..."
API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -k "https://$LB_DNS/api/auth/login" -X POST -H "Content-Type: application/json" -d '{"username":"test","password":"test"}' || echo "000")
if [[ "$API_RESPONSE" == "401" ]] || [[ "$API_RESPONSE" == "400" ]]; then
    print_success "API endpoint accessible (returned expected auth error)"
else
    print_warning "API endpoint test returned status: $API_RESPONSE"
fi

# Display deployment summary
echo ""
print_success "🎉 Deployment completed successfully!"
echo ""
echo "📊 DEPLOYMENT SUMMARY:"
echo "======================"
echo "Stack Name: $STACK_NAME"
echo "Environment: Production"
echo "Region: $AWS_REGION"
echo ""
echo "🌐 APPLICATION URLs:"
echo "==================="
if [ "$CUSTOM_DOMAIN" = "true" ]; then
    echo "HTTPS URL: https://$API_SUBDOMAIN"
    echo "Health Check: https://$API_SUBDOMAIN/health"
    echo "Load Balancer DNS: $LB_DNS"
else
    echo "HTTPS URL: https://$LB_DNS"
    echo "Health Check: https://$LB_DNS/health"
    echo "Load Balancer DNS: $LB_DNS"
fi
echo ""
echo "🔐 SECURITY:"
echo "============"
echo "SSL Certificate: AWS-managed"
echo "HTTP to HTTPS: Automatic redirect"
echo "Database: Encrypted at rest"
echo ""
echo "📝 NEXT STEPS:"
echo "=============="
echo "1. Test your application"
echo "2. Update your frontend to use HTTPS URLs"
echo "3. Monitor the deployment"
echo ""
echo "💡 TROUBLESHOOTING:"
echo "==================="
echo "To check deployment status:"
echo "aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME"
echo ""
echo "To view logs:"
echo "aws logs describe-log-groups --region $AWS_REGION --log-group-name-prefix /ecs/$STACK_NAME"
echo ""
