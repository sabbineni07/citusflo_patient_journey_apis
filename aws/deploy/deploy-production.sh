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

# Try to find citusflo-vpc first, fallback to first available VPC
VPC_ID=$(aws ec2 describe-vpcs --region $AWS_REGION --filters "Name=tag:Name,Values=citusflo-vpc" --query 'Vpcs[0].VpcId' --output text 2>/dev/null || echo "")
if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    print_warning "citusflo-vpc not found, using first available VPC"
    VPC_ID=$(aws ec2 describe-vpcs --region $AWS_REGION --query 'Vpcs[0].VpcId' --output text)
fi

if [ "$VPC_ID" = "None" ] || [ -z "$VPC_ID" ]; then
    print_error "No VPC found in region $AWS_REGION"
    exit 1
fi

print_status "Using VPC: $VPC_ID"

# Get all subnets in the VPC with their public/private status
ALL_SUBNETS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[].SubnetId' --output text | tr '\t' ',' | sed 's/[[:space:]]/,/g' | sed 's/,,*/,/g' | sed 's/^,//;s/,$//')

# Get public subnets for ALB (subnets with MapPublicIpOnLaunch=true)
ALB_SUBNETS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" "Name=map-public-ip-on-launch,Values=true" --query 'Subnets[].SubnetId' --output text | tr '\t' ',' | sed 's/[[:space:]]/,/g' | sed 's/,,*/,/g' | sed 's/^,//;s/,$//')

# If no public subnets found, use first 2 subnets as fallback
if [ -z "$ALB_SUBNETS" ] || [ "$ALB_SUBNETS" = "None" ]; then
    print_warning "No public subnets found, using first 2 subnets"
    ALB_SUBNETS=$(aws ec2 describe-subnets --region $AWS_REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[:2].SubnetId' --output text | tr '\t' ',' | sed 's/[[:space:]]/,/g' | sed 's/,,*/,/g' | sed 's/^,//;s/,$//')
fi

print_status "All subnets: $ALL_SUBNETS"
print_status "ALB subnets: $ALB_SUBNETS"

# Generate or retrieve secure passwords
print_status "🔐 Setting up secure passwords..."

# Check for existing database password secret
OLD_DB_SECRET="production/patient-journey/database-credentials"
if aws secretsmanager describe-secret --secret-id "$OLD_DB_SECRET" --region $AWS_REGION &>/dev/null 2>&1; then
    print_status "Found existing database credentials secret, extracting password..."
    DB_CREDS_JSON=$(aws secretsmanager get-secret-value --secret-id "$OLD_DB_SECRET" --region $AWS_REGION --query SecretString --output text 2>/dev/null)
    if [ -n "$DB_CREDS_JSON" ]; then
        DB_PASSWORD=$(echo "$DB_CREDS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('password', ''))" 2>/dev/null)
        if [ -n "$DB_PASSWORD" ]; then
            print_success "✅ Extracted database password from existing secret (${#DB_PASSWORD} chars)"
        else
            print_warning "Could not extract password from JSON, generating new one..."
            DB_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
        fi
    else
        DB_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
    fi
else
    print_status "No existing database secret found, generating new password..."
    DB_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
fi

# Always generate new SECRET_KEY and JWT_SECRET (these are new secrets)
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 64)
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 64)

# Check for existing admin password secret (but generate new one if insecure)
OLD_ADMIN_SECRET="production/patient-journey/admin-credentials"
ADMIN_PASSWORD=""
if [ -z "$ADMIN_PASSWORD" ] && aws secretsmanager describe-secret --secret-id "$OLD_ADMIN_SECRET" --region $AWS_REGION &>/dev/null 2>&1; then
    print_status "Found existing admin credentials secret, checking password..."
    ADMIN_CREDS_JSON=$(aws secretsmanager get-secret-value --secret-id "$OLD_ADMIN_SECRET" --region $AWS_REGION --query SecretString --output text 2>/dev/null)
    if [ -n "$ADMIN_CREDS_JSON" ]; then
        EXISTING_ADMIN_PASSWORD=$(echo "$ADMIN_CREDS_JSON" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('password', ''))" 2>/dev/null)
        if [ -n "$EXISTING_ADMIN_PASSWORD" ]; then
            # Check if password meets HIPAA requirements (12+ chars)
            if [ ${#EXISTING_ADMIN_PASSWORD} -ge 12 ]; then
                ADMIN_PASSWORD="$EXISTING_ADMIN_PASSWORD"
                print_success "✅ Using existing admin password (meets HIPAA requirements, ${#EXISTING_ADMIN_PASSWORD} chars)"
            else
                print_warning "Existing admin password (${#EXISTING_ADMIN_PASSWORD} chars) does not meet HIPAA requirements (needs 12+ chars)"
                print_status "Generating new secure admin password..."
                ADMIN_PASSWORD=$(python3 -c "import secrets, string; alphabet = string.ascii_letters + string.digits + '!@#$%^&*'; print(''.join(secrets.choice(alphabet) for _ in range(16)))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)
            fi
        fi
    fi
fi

# Generate admin password if not set (from environment variable or extracted from existing secret)
if [ -z "$ADMIN_PASSWORD" ]; then
    ADMIN_PASSWORD=${ADMIN_PASSWORD:-$(python3 -c "import secrets, string; alphabet = string.ascii_letters + string.digits + '!@#$%^&*'; print(''.join(secrets.choice(alphabet) for _ in range(16)))" 2>/dev/null || head /dev/urandom | tr -dc A-Za-z0-9 | head -c 32)}
fi

print_success "✅ All passwords configured"

# Setup AWS Secrets Manager
print_status "🔐 Setting up AWS Secrets Manager..."
ENVIRONMENT="production"
SECRET_BASE_PATH="citusflo/${ENVIRONMENT}"

# Function to create or update secret
create_or_update_secret() {
    local secret_name=$1
    local secret_value=$2
    local description=$3
    
    if aws secretsmanager describe-secret --secret-id "$secret_name" --region $AWS_REGION &>/dev/null 2>&1; then
        print_status "Secret '$secret_name' exists, updating..."
        aws secretsmanager update-secret \
            --secret-id "$secret_name" \
            --secret-string "$secret_value" \
            --region $AWS_REGION > /dev/null
        print_success "Updated secret: $secret_name"
    else
        print_status "Creating secret: $secret_name"
        aws secretsmanager create-secret \
            --name "$secret_name" \
            --secret-string "$secret_value" \
            --description "$description" \
            --region $AWS_REGION > /dev/null
        print_success "Created secret: $secret_name"
    fi
}

# Create secrets in Secrets Manager
create_or_update_secret "${SECRET_BASE_PATH}/secret-key" "$SECRET_KEY" "Flask SECRET_KEY for CitusFlo ${ENVIRONMENT}"
create_or_update_secret "${SECRET_BASE_PATH}/jwt-secret-key" "$JWT_SECRET" "JWT_SECRET_KEY for CitusFlo ${ENVIRONMENT}"
create_or_update_secret "${SECRET_BASE_PATH}/admin-password" "$ADMIN_PASSWORD" "Admin password for initial citusflo_admin user in ${ENVIRONMENT}"
create_or_update_secret "${SECRET_BASE_PATH}/database-password" "$DB_PASSWORD" "Database password for CitusFlo ${ENVIRONMENT} RDS"

print_success "✅ All secrets created/updated in AWS Secrets Manager"
print_warning "⚠️  Admin password: ${ADMIN_PASSWORD:0:8}... (stored in Secrets Manager, first 8 chars shown)"

# ECR setup - Need to create repo manually before CloudFormation (template references image URI)
print_status "🐳 Setting up ECR repository..."

# Create ECR repository if it doesn't exist (or delete and recreate to avoid conflicts)
if aws ecr describe-repositories --region $AWS_REGION --repository-names $ECR_REPO_NAME &>/dev/null; then
    print_status "ECR repository exists, deleting it to avoid CloudFormation conflict..."
    aws ecr delete-repository --region $AWS_REGION --repository-name $ECR_REPO_NAME --force 2>/dev/null || true
    print_status "Waiting 5 seconds for repository deletion to complete..."
    sleep 5
fi

print_status "Creating ECR repository: $ECR_REPO_NAME"
aws ecr create-repository --region $AWS_REGION --repository-name $ECR_REPO_NAME > /dev/null

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

print_success "Image pushed successfully: $ECR_URI"

# Deploy CloudFormation stack
print_status "☁️  Deploying CloudFormation stack..."

# Choose template based on deployment type
if [ "$DEPLOYMENT_TYPE" = "https-only" ]; then
    TEMPLATE_FILE="aws/deploy/cloudformation-https.yaml"
    STACK_NAME="$STACK_NAME-https"
else
    TEMPLATE_FILE="aws/deploy/cloudformation-production.yaml"
fi

# Check if stack exists
if aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME &>/dev/null; then
    print_status "Stack exists, updating..."
    OPERATION="update-stack"
else
    print_status "Creating new stack..."
    OPERATION="create-stack"
fi

# Check if DNS record already exists (Option A: Make DNS creation optional)
CREATE_DNS_RECORD="true"
DNS_RECORD_EXISTS="false"
if [ "$CUSTOM_DOMAIN" = "true" ]; then
    print_status "🔍 Checking if DNS record already exists..."
    HOSTED_ZONE_ID="Z074839530U7S7LIQMR0M"
    DNS_RECORD=$(aws route53 list-resource-record-sets \
        --hosted-zone-id $HOSTED_ZONE_ID \
        --query "ResourceRecordSets[?Name=='${API_SUBDOMAIN}.' || Name=='${API_SUBDOMAIN}'].Name" \
        --output text 2>/dev/null || echo "")
    
    if [ -n "$DNS_RECORD" ]; then
        print_warning "DNS record for ${API_SUBDOMAIN} already exists - CloudFormation will skip DNS creation"
        CREATE_DNS_RECORD="false"
        DNS_RECORD_EXISTS="true"
    else
        print_status "DNS record for ${API_SUBDOMAIN} does not exist - CloudFormation will create it"
    fi
fi

# Create JSON parameter file to avoid comma-separated value parsing issues
PARAM_FILE=$(mktemp)
if [ "$CUSTOM_DOMAIN" = "true" ]; then
    cat > "$PARAM_FILE" <<EOF
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "production"
  },
  {
    "ParameterKey": "VpcId",
    "ParameterValue": "$VPC_ID"
  },
  {
    "ParameterKey": "SubnetIds",
    "ParameterValue": "$ALL_SUBNETS"
  },
  {
    "ParameterKey": "AlbSubnetIds",
    "ParameterValue": "$ALB_SUBNETS"
  },
  {
    "ParameterKey": "DatabasePassword",
    "ParameterValue": "$DB_PASSWORD"
  },
  {
    "ParameterKey": "DomainName",
    "ParameterValue": "$API_SUBDOMAIN"
  },
  {
    "ParameterKey": "CertificateArn",
    "ParameterValue": "arn:aws:acm:us-east-1:681885653444:certificate/8c346b5b-ee34-4b2f-a368-cd808ca5fd37"
  },
  {
    "ParameterKey": "HostedZoneId",
    "ParameterValue": "Z074839530U7S7LIQMR0M"
  },
  {
    "ParameterKey": "CreateDNSRecord",
    "ParameterValue": "$CREATE_DNS_RECORD"
  }
]
EOF
else
    cat > "$PARAM_FILE" <<EOF
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "production"
  },
  {
    "ParameterKey": "VpcId",
    "ParameterValue": "$VPC_ID"
  },
  {
    "ParameterKey": "SubnetIds",
    "ParameterValue": "$ALL_SUBNETS"
  },
  {
    "ParameterKey": "AlbSubnetIds",
    "ParameterValue": "$ALB_SUBNETS"
  },
  {
    "ParameterKey": "DatabasePassword",
    "ParameterValue": "$DB_PASSWORD"
  },
  {
    "ParameterKey": "SecretKey",
    "ParameterValue": "DEPRECATED_USE_SECRETS_MANAGER"
  },
  {
    "ParameterKey": "JWTSecretKey",
    "ParameterValue": "DEPRECATED_USE_SECRETS_MANAGER"
  },
  {
    "ParameterKey": "AdminPassword",
    "ParameterValue": "DEPRECATED_USE_SECRETS_MANAGER"
  },
  {
    "ParameterKey": "DomainName",
    "ParameterValue": "api.citusflo.com"
  },
  {
    "ParameterKey": "CertificateArn",
    "ParameterValue": "arn:aws:acm:us-east-1:681885653444:certificate/8c346b5b-ee34-4b2f-a368-cd808ca5fd37"
  },
  {
    "ParameterKey": "HostedZoneId",
    "ParameterValue": "Z074839530U7S7LIQMR0M"
  },
  {
    "ParameterKey": "CreateDNSRecord",
    "ParameterValue": "$CREATE_DNS_RECORD"
  }
]
EOF
fi

# Deploy the stack using JSON parameter file
aws cloudformation $OPERATION \
    --region $AWS_REGION \
    --stack-name $STACK_NAME \
    --template-body file://$TEMPLATE_FILE \
    --capabilities CAPABILITY_IAM \
    --parameters file://"$PARAM_FILE" \
    --tags \
        Key=Project,Value=CitusFlo \
        Key=Environment,Value=Production \
        Key=Service,Value=PatientJourneyAPI

# Clean up parameter file
rm -f "$PARAM_FILE"

print_status "Waiting for stack operation to complete..."
aws cloudformation wait stack-${OPERATION%-stack}-complete --region $AWS_REGION --stack-name $STACK_NAME

# After stack is created, login to ECR and push image
if [ "${OPERATION}" = "create-stack" ]; then
    print_status "Stack created successfully, pushing Docker image to ECR..."
    aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
    
    ECR_URI="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO_NAME:$IMAGE_TAG"
    docker tag $CONTAINER_NAME:latest $ECR_URI
    docker push $ECR_URI
    print_success "Image pushed successfully: $ECR_URI"
    
    # Update ECS service to use new image
    print_status "Updating ECS service with new image..."
    ECS_CLUSTER=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' --output text)
    ECS_SERVICE=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSServiceName`].OutputValue' --output text)
    
    # Get current task definition and update with new image
    TASK_DEF_ARN=$(aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE --query 'services[0].taskDefinition' --output text)
    aws ecs update-service --region $AWS_REGION --cluster $ECS_CLUSTER --service $ECS_SERVICE --force-new-deployment > /dev/null
    print_success "ECS service is being updated with new image"
fi

# Get stack outputs
print_status "📋 Getting deployment information..."
LB_DNS=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text)
APP_URL=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' --output text 2>/dev/null || echo "Not available")

# Update DNS record manually if CloudFormation skipped it (Option A)
if [ "$DNS_RECORD_EXISTS" = "true" ] && [ "$CUSTOM_DOMAIN" = "true" ] && [ -n "$LB_DNS" ]; then
    print_status "🌐 Updating existing DNS record to point to new load balancer..."
    HOSTED_ZONE_ID="Z074839530U7S7LIQMR0M"
    
    # Get current DNS record value
    CURRENT_RECORD=$(aws route53 list-resource-record-sets \
        --hosted-zone-id $HOSTED_ZONE_ID \
        --query "ResourceRecordSets[?Name=='${API_SUBDOMAIN}.'].{Name:Name,Type:Type,TTL:TTL,Value:ResourceRecords[0].Value}" \
        --output json 2>/dev/null)
    
    if [ -n "$CURRENT_RECORD" ] && [ "$CURRENT_RECORD" != "[]" ]; then
        # Extract current value
        CURRENT_VALUE=$(echo "$CURRENT_RECORD" | grep -o '"Value": "[^"]*"' | cut -d'"' -f4)
        
        # Update DNS record to point to new load balancer
        CHANGE_BATCH=$(cat <<EOF
{
  "Changes": [{
    "Action": "UPSERT",
    "ResourceRecordSet": {
      "Name": "${API_SUBDOMAIN}.",
      "Type": "CNAME",
      "TTL": 300,
      "ResourceRecords": [{"Value": "${LB_DNS}"}]
    }
  }]
}
EOF
)
        
        CHANGE_ID=$(aws route53 change-resource-record-sets \
            --hosted-zone-id $HOSTED_ZONE_ID \
            --change-batch "$CHANGE_BATCH" \
            --query 'ChangeInfo.Id' \
            --output text 2>/dev/null)
        
        if [ -n "$CHANGE_ID" ]; then
            print_success "DNS record updated successfully (Change ID: ${CHANGE_ID})"
            print_status "Updated ${API_SUBDOMAIN} → ${LB_DNS}"
            print_status "Previous value was: ${CURRENT_VALUE}"
        else
            print_warning "Failed to update DNS record automatically. Please update manually:"
            print_warning "  Route53 Hosted Zone: ${HOSTED_ZONE_ID}"
            print_warning "  Record: ${API_SUBDOMAIN}"
            print_warning "  New Value: ${LB_DNS}"
        fi
    else
        print_warning "Could not find existing DNS record to update"
    fi
fi

# Wait for ECS service to be stable
print_status "⏳ Waiting for ECS service to be stable..."
ECS_CLUSTER=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' --output text)
ECS_SERVICE=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSServiceName`].OutputValue' --output text)

aws ecs wait services-stable --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE

# Initialize database after ECS service is stable
print_status "🗄️  Initializing database..."
print_status "Running database initialization (flask init-db)..."

# Get the current task definition
TASK_DEFINITION=$(aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE --query 'services[0].taskDefinition' --output text)

# Run database initialization task
INIT_TASK_ARN=$(aws ecs run-task \
    --cluster $ECS_CLUSTER \
    --task-definition $TASK_DEFINITION \
    --launch-type FARGATE \
    --network-configuration "awsvpcConfiguration={subnets=[$ALB_SUBNETS],securityGroups=[$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroupId`].OutputValue' --output text)],assignPublicIp=ENABLED}" \
    --overrides '{"containerOverrides":[{"name":"patient-api","command":["flask","init-db"]}]}' \
    --region $AWS_REGION \
    --query 'tasks[0].taskArn' --output text)

print_status "Database initialization task started: $INIT_TASK_ARN"

# Wait for database initialization to complete
print_status "Waiting for database initialization to complete..."
aws ecs wait tasks-stopped --region $AWS_REGION --cluster $ECS_CLUSTER --tasks $INIT_TASK_ARN

# Check if database initialization was successful
INIT_EXIT_CODE=$(aws ecs describe-tasks --region $AWS_REGION --cluster $ECS_CLUSTER --tasks $INIT_TASK_ARN --query 'tasks[0].containers[0].exitCode' --output text)

if [ "$INIT_EXIT_CODE" = "0" ]; then
    print_success "✅ Database initialized successfully!"
    print_success "Super admin user created: username=citusflo_admin"
    print_warning "⚠️  Password set from ADMIN_PASSWORD environment variable or generated (see ECS task logs)"
else
    print_error "❌ Database initialization failed with exit code: $INIT_EXIT_CODE"
    print_error "Check the logs for details:"
    print_error "aws logs get-log-events --log-group-name /ecs/$STACK_NAME --log-stream-name ecs/patient-api/$INIT_TASK_ARN --region $AWS_REGION"
    exit 1
fi

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
echo "1. Test your application endpoints"
echo "2. Login with super admin credentials: citusflo_admin"
echo "   Password: Set via ADMIN_PASSWORD environment variable or generated (check ECS task logs)"
echo "3. Update your frontend to use HTTPS URLs"
echo "4. Monitor the deployment"
echo ""
echo "🔐 SUPER ADMIN CREDENTIALS:"
echo "==========================="
echo "Username: citusflo_admin"
echo "Password: Set via ADMIN_PASSWORD environment variable (check ECS task logs for generated password if not set)"
echo "Email: account@citusflo.com"
echo "Role: super_admin"
echo ""
echo "💡 TROUBLESHOOTING:"
echo "==================="
echo "To check deployment status:"
echo "aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME"
echo ""
echo "To view application logs:"
echo "aws logs describe-log-groups --region $AWS_REGION --log-group-name-prefix /ecs/$STACK_NAME"
echo ""
echo "To check ECS service status:"
echo "aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE"
echo ""
echo "If API endpoints return 504 timeout, check database connectivity:"
echo "1. Verify RDS security group allows ECS access on port 5432"
echo "2. Run database initialization manually if needed:"
echo "   aws ecs run-task --cluster $ECS_CLUSTER --task-definition $TASK_DEFINITION \\"
echo "     --launch-type FARGATE --network-configuration 'awsvpcConfiguration={subnets=[$ALB_SUBNETS],securityGroups=[...],assignPublicIp=ENABLED}' \\"
echo "     --overrides '{\"containerOverrides\":[{\"name\":\"patient-api\",\"command\":[\"flask\",\"init-db\"]}]}'"
echo ""
