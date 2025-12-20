#!/bin/bash

# CitusFlo Patient Journey APIs - Deployment Troubleshooting Script
# This script helps diagnose and fix common deployment issues

set -e

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

print_status "🔍 CitusFlo Deployment Troubleshooting Tool"
print_status "=========================================="

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    print_error "AWS CLI not configured or no valid credentials"
    exit 1
fi

# Function to check CloudFormation stack
check_cloudformation() {
    print_status "📋 Checking CloudFormation stack..."
    
    if aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME &>/dev/null; then
        STACK_STATUS=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].StackStatus' --output text)
        print_success "Stack exists with status: $STACK_STATUS"
        return 0
    else
        print_error "Stack does not exist: $STACK_NAME"
        return 1
    fi
}

# Function to check ECS service
check_ecs() {
    print_status "🐳 Checking ECS service..."
    
    ECS_CLUSTER=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' --output text 2>/dev/null || echo "")
    ECS_SERVICE=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSServiceName`].OutputValue' --output text 2>/dev/null || echo "")
    
    if [ -n "$ECS_CLUSTER" ] && [ -n "$ECS_SERVICE" ]; then
        SERVICE_STATUS=$(aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE --query 'services[0].status' --output text)
        RUNNING_COUNT=$(aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE --query 'services[0].runningCount' --output text)
        DESIRED_COUNT=$(aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE --query 'services[0].desiredCount' --output text)
        
        print_success "ECS Service: $ECS_SERVICE"
        print_success "Status: $SERVICE_STATUS"
        print_success "Running: $RUNNING_COUNT/$DESIRED_COUNT tasks"
        
        if [ "$RUNNING_COUNT" != "$DESIRED_COUNT" ]; then
            print_warning "Service not fully running. Check task logs for details."
            return 1
        fi
        return 0
    else
        print_error "ECS service not found in stack outputs"
        return 1
    fi
}

# Function to check RDS database
check_rds() {
    print_status "🗄️  Checking RDS database..."
    
    DB_INSTANCE=$(aws rds describe-db-instances --region $AWS_REGION --db-instance-identifier production-citusflo-patient-db 2>/dev/null || echo "")
    
    if [ -n "$DB_INSTANCE" ]; then
        DB_STATUS=$(aws rds describe-db-instances --region $AWS_REGION --db-instance-identifier production-citusflo-patient-db --query 'DBInstances[0].DBInstanceStatus' --output text)
        print_success "Database status: $DB_STATUS"
        
        if [ "$DB_STATUS" = "available" ]; then
            return 0
        else
            print_warning "Database not available. Status: $DB_STATUS"
            return 1
        fi
    else
        print_error "Database instance not found"
        return 1
    fi
}

# Function to check load balancer
check_load_balancer() {
    print_status "⚖️  Checking Load Balancer..."
    
    LB_DNS=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text 2>/dev/null || echo "")
    
    if [ -n "$LB_DNS" ]; then
        print_success "Load Balancer DNS: $LB_DNS"
        
        # Test health endpoint
        HEALTH_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -k "https://$LB_DNS/health" || echo "000")
        if [ "$HEALTH_RESPONSE" = "200" ]; then
            print_success "Health endpoint working (HTTP $HEALTH_RESPONSE)"
            return 0
        else
            print_warning "Health endpoint returned HTTP $HEALTH_RESPONSE"
            return 1
        fi
    else
        print_error "Load Balancer DNS not found in stack outputs"
        return 1
    fi
}

# Function to check API endpoints
check_api() {
    print_status "🔌 Checking API endpoints..."
    
    LB_DNS=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`LoadBalancerDNS`].OutputValue' --output text 2>/dev/null || echo "")
    
    if [ -n "$LB_DNS" ]; then
        # Test users endpoint
        API_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" -k "https://$LB_DNS/api/auth/users" || echo "000")
        
        if [ "$API_RESPONSE" = "200" ]; then
            print_success "API endpoint working (HTTP $API_RESPONSE)"
            return 0
        elif [ "$API_RESPONSE" = "504" ]; then
            print_error "API endpoint returning 504 Gateway Timeout - Database likely not initialized"
            return 1
        else
            print_warning "API endpoint returned HTTP $API_RESPONSE"
            return 1
        fi
    else
        print_error "Cannot test API endpoints - Load Balancer DNS not found"
        return 1
    fi
}

# Function to check database initialization
check_database_init() {
    print_status "🗄️  Checking database initialization..."
    
    # Check logs for database initialization
    LOG_GROUP="/ecs/production-citusflo-patient-api"
    
    if aws logs describe-log-groups --region $AWS_REGION --log-group-name-prefix $LOG_GROUP &>/dev/null; then
        # Look for database initialization messages
        INIT_MESSAGE=$(aws logs filter-log-events --region $AWS_REGION --log-group-name $LOG_GROUP --filter-pattern "Database initialized successfully" --query 'events[0].message' --output text 2>/dev/null || echo "")
        
        if [ -n "$INIT_MESSAGE" ] && [ "$INIT_MESSAGE" != "None" ]; then
            print_success "Database initialization found in logs"
            return 0
        else
            print_error "Database initialization not found in logs"
            return 1
        fi
    else
        print_error "Log group not found: $LOG_GROUP"
        return 1
    fi
}

# Function to fix database initialization
fix_database_init() {
    print_status "🔧 Fixing database initialization..."
    
    ECS_CLUSTER=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSClusterName`].OutputValue' --output text 2>/dev/null || echo "")
    ECS_SERVICE=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSServiceName`].OutputValue' --output text 2>/dev/null || echo "")
    
    if [ -n "$ECS_CLUSTER" ] && [ -n "$ECS_SERVICE" ]; then
        TASK_DEFINITION=$(aws ecs describe-services --region $AWS_REGION --cluster $ECS_CLUSTER --services $ECS_SERVICE --query 'services[0].taskDefinition' --output text)
        
        print_status "Running database initialization task..."
        
        # Get subnet and security group information
        ALB_SUBNETS=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`AlbSubnetIds`].OutputValue' --output text 2>/dev/null || echo "")
        ECS_SG=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroupId`].OutputValue' --output text 2>/dev/null || echo "")
        
        # If CloudFormation outputs not available, use known values from actual infrastructure
        if [ -z "$ALB_SUBNETS" ]; then
            ALB_SUBNETS="subnet-0bdb6dd4f4f780305,subnet-035661356dc83d054"
            print_warning "Using known public subnets: $ALB_SUBNETS"
        fi
        if [ -z "$ECS_SG" ]; then
            ECS_SG="sg-0837e683efb9d04b0"
            print_warning "Using known ECS security group: $ECS_SG"
        fi
        
        if [ -n "$ALB_SUBNETS" ] && [ -n "$ECS_SG" ]; then
            INIT_TASK_ARN=$(aws ecs run-task \
                --cluster $ECS_CLUSTER \
                --task-definition $TASK_DEFINITION \
                --launch-type FARGATE \
                --network-configuration "awsvpcConfiguration={subnets=[$ALB_SUBNETS],securityGroups=[$ECS_SG],assignPublicIp=ENABLED}" \
                --overrides '{"containerOverrides":[{"name":"patient-api","command":["flask","init-db"]}]}' \
                --region $AWS_REGION \
                --query 'tasks[0].taskArn' --output text)
            
            print_status "Database initialization task started: $INIT_TASK_ARN"
            print_status "Waiting for completion..."
            
            aws ecs wait tasks-stopped --region $AWS_REGION --cluster $ECS_CLUSTER --tasks $INIT_TASK_ARN
            
            INIT_EXIT_CODE=$(aws ecs describe-tasks --region $AWS_REGION --cluster $ECS_CLUSTER --tasks $INIT_TASK_ARN --query 'tasks[0].containers[0].exitCode' --output text)
            
            if [ "$INIT_EXIT_CODE" = "0" ]; then
                print_success "✅ Database initialized successfully!"
                print_success "Super admin user created: username=citusflo_admin"
                print_warning "⚠️  Password set from ADMIN_PASSWORD environment variable or generated (check ECS task logs)"
                return 0
            else
                print_error "❌ Database initialization failed with exit code: $INIT_EXIT_CODE"
                return 1
            fi
        else
            print_error "Cannot get network configuration for database initialization"
            return 1
        fi
    else
        print_error "Cannot get ECS cluster/service information"
        return 1
    fi
}

# Function to check RDS security group
check_rds_security() {
    print_status "🔒 Checking RDS security group..."
    
    # Get database security group
    DB_SG=$(aws rds describe-db-instances --region $AWS_REGION --db-instance-identifier production-citusflo-patient-db --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text 2>/dev/null || echo "")
    
    # If not found, use known default security group
    if [ -z "$DB_SG" ] || [ "$DB_SG" = "None" ]; then
        DB_SG="sg-0ea7f4ff19f0587c3"
        print_warning "Using known database security group: $DB_SG"
    fi
    
    if [ -n "$DB_SG" ]; then
        # Check if ECS security group has access
        ECS_SG=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroupId`].OutputValue' --output text 2>/dev/null || echo "")
        
        # If not found, use known ECS security group
        if [ -z "$ECS_SG" ] || [ "$ECS_SG" = "None" ]; then
            ECS_SG="sg-0837e683efb9d04b0"
            print_warning "Using known ECS security group: $ECS_SG"
        fi
        
        if [ -n "$ECS_SG" ]; then
            # Check ingress rules
            HAS_ACCESS=$(aws ec2 describe-security-groups --region $AWS_REGION --group-ids $DB_SG --query "SecurityGroups[0].IpPermissions[?UserIdGroupPairs[0].GroupId=='$ECS_SG' && FromPort=='5432']" --output text 2>/dev/null || echo "")
            
            if [ -n "$HAS_ACCESS" ]; then
                print_success "RDS security group allows ECS access on port 5432"
                return 0
            else
                print_error "RDS security group does not allow ECS access on port 5432"
                return 1
            fi
        else
            print_error "Cannot get ECS security group ID"
            return 1
        fi
    else
        print_error "Cannot get database security group ID"
        return 1
    fi
}

# Function to fix RDS security group
fix_rds_security() {
    print_status "🔧 Fixing RDS security group..."
    
    # Get database security group
    DB_SG=$(aws rds describe-db-instances --region $AWS_REGION --db-instance-identifier production-citusflo-patient-db --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' --output text 2>/dev/null || echo "")
    ECS_SG=$(aws cloudformation describe-stacks --region $AWS_REGION --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`ECSSecurityGroupId`].OutputValue' --output text 2>/dev/null || echo "")
    
    # Use known values if CloudFormation outputs not available
    if [ -z "$DB_SG" ] || [ "$DB_SG" = "None" ]; then
        DB_SG="sg-0ea7f4ff19f0587c3"
        print_warning "Using known database security group: $DB_SG"
    fi
    if [ -z "$ECS_SG" ] || [ "$ECS_SG" = "None" ]; then
        ECS_SG="sg-0837e683efb9d04b0"
        print_warning "Using known ECS security group: $ECS_SG"
    fi
    
    if [ -n "$DB_SG" ] && [ -n "$ECS_SG" ]; then
        print_status "Adding ingress rule for ECS security group..."
        
        aws ec2 authorize-security-group-ingress \
            --group-id $DB_SG \
            --protocol tcp \
            --port 5432 \
            --source-group $ECS_SG \
            --region $AWS_REGION
        
        print_success "✅ RDS security group updated"
        return 0
    else
        print_error "Cannot get security group IDs"
        return 1
    fi
}

# Main troubleshooting flow
main() {
    print_status "Starting comprehensive deployment check..."
    echo ""
    
    # Check all components
    CF_OK=0
    ECS_OK=0
    RDS_OK=0
    LB_OK=0
    API_OK=0
    DB_INIT_OK=0
    RDS_SEC_OK=0
    
    check_cloudformation || CF_OK=1
    echo ""
    
    if [ $CF_OK -eq 0 ]; then
        check_ecs || ECS_OK=1
        echo ""
        
        check_rds || RDS_OK=1
        echo ""
        
        check_rds_security || RDS_SEC_OK=1
        echo ""
        
        check_load_balancer || LB_OK=1
        echo ""
        
        check_api || API_OK=1
        echo ""
        
        check_database_init || DB_INIT_OK=1
        echo ""
    fi
    
    # Summary and recommendations
    print_status "📊 TROUBLESHOOTING SUMMARY"
    print_status "========================="
    
    if [ $CF_OK -eq 0 ]; then
        print_success "✅ CloudFormation stack: OK"
    else
        print_error "❌ CloudFormation stack: ISSUES FOUND"
    fi
    
    if [ $ECS_OK -eq 0 ]; then
        print_success "✅ ECS service: OK"
    else
        print_error "❌ ECS service: ISSUES FOUND"
    fi
    
    if [ $RDS_OK -eq 0 ]; then
        print_success "✅ RDS database: OK"
    else
        print_error "❌ RDS database: ISSUES FOUND"
    fi
    
    if [ $RDS_SEC_OK -eq 0 ]; then
        print_success "✅ RDS security group: OK"
    else
        print_error "❌ RDS security group: ISSUES FOUND"
    fi
    
    if [ $LB_OK -eq 0 ]; then
        print_success "✅ Load balancer: OK"
    else
        print_error "❌ Load balancer: ISSUES FOUND"
    fi
    
    if [ $API_OK -eq 0 ]; then
        print_success "✅ API endpoints: OK"
    else
        print_error "❌ API endpoints: ISSUES FOUND"
    fi
    
    if [ $DB_INIT_OK -eq 0 ]; then
        print_success "✅ Database initialization: OK"
    else
        print_error "❌ Database initialization: ISSUES FOUND"
    fi
    
    echo ""
    
    # Auto-fix recommendations
    if [ $RDS_SEC_OK -ne 0 ]; then
        print_status "🔧 AUTO-FIX: RDS Security Group"
        read -p "Fix RDS security group to allow ECS access? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            fix_rds_security
            echo ""
        fi
    fi
    
    if [ $DB_INIT_OK -ne 0 ]; then
        print_status "🔧 AUTO-FIX: Database Initialization"
        read -p "Run database initialization? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            fix_database_init
            echo ""
        fi
    fi
    
    # Final recommendations
    echo ""
    print_status "💡 RECOMMENDATIONS"
    print_status "=================="
    
    if [ $CF_OK -ne 0 ]; then
        print_warning "1. Check CloudFormation stack events for deployment issues"
    fi
    
    if [ $ECS_OK -ne 0 ]; then
        print_warning "2. Check ECS service events and task logs"
    fi
    
    if [ $RDS_OK -ne 0 ]; then
        print_warning "3. Check RDS database status and configuration"
    fi
    
    if [ $RDS_SEC_OK -ne 0 ]; then
        print_warning "4. Fix RDS security group to allow ECS access on port 5432"
    fi
    
    if [ $LB_OK -ne 0 ]; then
        print_warning "5. Check load balancer configuration and health checks"
    fi
    
    if [ $API_OK -ne 0 ]; then
        print_warning "6. Check API endpoint responses and application logs"
    fi
    
    if [ $DB_INIT_OK -ne 0 ]; then
        print_warning "7. Run database initialization: flask init-db"
    fi
    
    echo ""
    print_status "🔍 For detailed logs, run:"
    print_status "aws logs describe-log-groups --region $AWS_REGION --log-group-name-prefix /ecs/production-citusflo-patient-api"
    print_status "aws ecs describe-services --region $AWS_REGION --cluster production-citusflo-patient-cluster --services production-citusflo-patient-service"
    echo ""
}

# Run main function
main "$@"
