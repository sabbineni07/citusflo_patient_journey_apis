# CitusFlo Patient Journey APIs - AWS Deployment Guide

This guide provides comprehensive instructions for deploying the CitusFlo Patient Journey APIs to AWS using ECS Fargate, RDS PostgreSQL, and Application Load Balancer.

## 📋 Prerequisites

Before deploying, ensure you have:

- **AWS CLI** installed and configured with appropriate permissions
- **Docker** installed and running
- **AWS Account** with the following permissions:
  - ECS (Elastic Container Service)
  - ECR (Elastic Container Registry)
  - RDS (Relational Database Service)
  - EC2 (VPC, Security Groups, Load Balancers)
  - CloudFormation
  - IAM (for creating roles)
  - CloudWatch Logs

## 🏗️ Architecture Overview

The deployment creates the following AWS resources:

- **ECS Fargate Cluster**: Runs the Flask application containers
- **RDS PostgreSQL Database**: Stores application data with Multi-AZ for high availability
- **Application Load Balancer**: Routes traffic to ECS tasks
- **ECR Repository**: Stores Docker images
- **VPC & Security Groups**: Network isolation and security
- **CloudWatch Logs**: Application logging

## 🚀 Automated Deployment

### Quick Start

1. **Clone the repository and navigate to the project directory**
   ```bash
   cd citusflo_patient_journey_apis
   ```

2. **Make the deployment script executable**
   ```bash
   chmod +x deploy.sh
   ```

3. **Update configuration in `deploy.sh`** (if needed):
   ```bash
   # Edit these values for your AWS environment
   VPC_ID="vpc-0204102b87fc02753"
   PUBLIC_SUBNET_1="subnet-035661356dc83d054"
   PUBLIC_SUBNET_2="subnet-0bdb6dd4f4f780305"
   ALL_SUBNETS="subnet-084c887eef0bbb19f,subnet-035661356dc83d054,subnet-0bdb6dd4f4f780305,subnet-0a2613df7d19ca3e3"
   ```

4. **Run the deployment script**
   ```bash
   ./deploy.sh
   ```

The script will:
- ✅ Check prerequisites (AWS CLI, Docker)
- ✅ Create ECR repository
- ✅ Build and push Docker image with correct architecture
- ✅ Deploy CloudFormation stack with all infrastructure
- ✅ Update ECS service with new image
- ✅ Verify deployment and health checks

## 🔧 Manual Deployment Steps

If you prefer to deploy manually or need to troubleshoot:

### Step 1: Prepare Docker Image

1. **Create ECR repository**
   ```bash
   aws ecr create-repository --repository-name citusflo-patient-journey-api --region us-east-1
   ```

2. **Build and push Docker image**
   ```bash
   # Login to ECR
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 681885653444.dkr.ecr.us-east-1.amazonaws.com
   
   # Build image with correct architecture
   docker build --platform linux/amd64 -t citusflo-patient-journey-api:latest .
   
   # Tag and push
   docker tag citusflo-patient-journey-api:latest 681885653444.dkr.ecr.us-east-1.amazonaws.com/citusflo-patient-journey-api:latest
   docker push 681885653444.dkr.ecr.us-east-1.amazonaws.com/citusflo-patient-journey-api:latest
   ```

### Step 2: Deploy Infrastructure

1. **Generate secure passwords**
   ```bash
   DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
   SECRET_KEY=$(openssl rand -base64 32)
   JWT_SECRET_KEY=$(openssl rand -base64 32)
   ```

2. **Deploy CloudFormation stack**
   ```bash
   aws cloudformation deploy \
     --template-file cloudformation.yaml \
     --stack-name citusflo-patient-journey-api-infrastructure \
     --parameter-overrides \
       Environment=production \
       VpcId=vpc-0204102b87fc02753 \
       SubnetIds="subnet-084c887eef0bbb19f,subnet-035661356dc83d054,subnet-0bdb6dd4f4f780305,subnet-0a2613df7d19ca3e3" \
       AlbSubnetIds="subnet-035661356dc83d054,subnet-0bdb6dd4f4f780305" \
       DatabasePassword="$DB_PASSWORD" \
       SecretKey="$SECRET_KEY" \
       JWTSecretKey="$JWT_SECRET_KEY" \
     --capabilities CAPABILITY_IAM \
     --region us-east-1
   ```

### Step 3: Verify Deployment

1. **Check ECS service status**
   ```bash
   aws ecs describe-services --cluster production-citusflo-patient-cluster --services production-citusflo-patient-service --region us-east-1
   ```

2. **Test health check**
   ```bash
   curl http://production-patient-lb-1572933777.us-east-1.elb.amazonaws.com/health
   ```

## 🔍 Verification & Testing

After deployment, verify the following:

### 1. ECS Service Health
```bash
aws ecs describe-services --cluster production-citusflo-patient-cluster --services production-citusflo-patient-service --region us-east-1 --query 'services[0].{RunningCount:runningCount,DesiredCount:desiredCount,Status:status}'
```

### 2. Target Group Health
```bash
aws elbv2 describe-target-health --target-group-arn "arn:aws:elasticloadbalancing:us-east-1:681885653444:targetgroup/production-patient-tg/971c1afdc7547382" --region us-east-1
```

### 3. Application Health Check
```bash
curl -f http://production-patient-lb-1572933777.us-east-1.elb.amazonaws.com/health
```

Expected response:
```json
{"service":"patient-api","status":"healthy"}
```

### 4. API Endpoints Test
```bash
# Test authentication endpoint
curl -X POST http://production-patient-lb-1572933777.us-east-1.elb.amazonaws.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Test health endpoint
curl http://production-patient-lb-1572933777.us-east-1.elb.amazonaws.com/api/health
```

## 📊 Monitoring & Logs

### View Application Logs
```bash
aws logs tail /ecs/production-citusflo-patient-api --follow --region us-east-1
```

### Monitor ECS Service
```bash
aws ecs describe-services --cluster production-citusflo-patient-cluster --services production-citusflo-patient-service --region us-east-1 --query 'services[0].events[0:5]'
```

### Check CloudFormation Stack
```bash
aws cloudformation describe-stacks --stack-name citusflo-patient-journey-api-infrastructure --region us-east-1
```

## 🛠️ Troubleshooting

### Common Issues

1. **Task fails to start**
   - Check logs: `aws logs tail /ecs/production-citusflo-patient-api --follow --region us-east-1`
   - Verify task definition has correct image and environment variables
   - Check ECS task execution role permissions

2. **Health check failures**
   - Verify application is responding on port 5000
   - Check security group rules allow traffic from load balancer
   - Ensure health check path `/health` is correct

3. **Database connection issues**
   - Verify RDS instance is running and accessible
   - Check database security group allows connections from application security group
   - Verify DATABASE_URL environment variable is correct

4. **Load balancer issues**
   - Check target group health
   - Verify ECS service has tasks running
   - Check security group rules for load balancer

### Useful Commands

```bash
# Check ECS task status
aws ecs list-tasks --cluster production-citusflo-patient-cluster --service-name production-citusflo-patient-service --region us-east-1

# Describe specific task
aws ecs describe-tasks --cluster production-citusflo-patient-cluster --tasks <TASK_ARN> --region us-east-1

# Check RDS status
aws rds describe-db-instances --db-instance-identifier production-patient-db --region us-east-1

# Check load balancer
aws elbv2 describe-load-balancers --region us-east-1 --query 'LoadBalancers[?LoadBalancerName==`production-patient-lb`]'
```

## 🔄 Updates & Scaling

### Update Application
1. Make code changes
2. Run `./deploy.sh` to rebuild and redeploy
3. Or manually push new image and update ECS service

### Scale Application
```bash
# Scale to 3 instances
aws ecs update-service --cluster production-citusflo-patient-cluster --service production-citusflo-patient-service --desired-count 3 --region us-east-1
```

### Update Infrastructure
1. Modify `cloudformation.yaml`
2. Run CloudFormation update:
   ```bash
   aws cloudformation deploy --template-file cloudformation.yaml --stack-name citusflo-patient-journey-api-infrastructure --region us-east-1
   ```

## 🗑️ Cleanup

To remove all resources:

```bash
# Delete CloudFormation stack (this removes most resources)
aws cloudformation delete-stack --stack-name citusflo-patient-journey-api-infrastructure --region us-east-1

# Delete ECR repository (optional)
aws ecr delete-repository --repository-name citusflo-patient-journey-api --force --region us-east-1

# Delete any remaining resources manually if needed
```

## 📝 Configuration Files

- `deploy.sh` - Main deployment script
- `cloudformation.yaml` - Infrastructure as Code template
- `Dockerfile` - Container configuration
- `app/__init__.py` - Flask application factory

## 🔐 Security Notes

- Database passwords are auto-generated and stored securely
- ECS tasks run with minimal required permissions
- Load balancer is internet-facing but application is in private subnets
- All traffic is logged via CloudWatch

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review AWS CloudFormation stack events
3. Check ECS service events and task logs
4. Verify all prerequisites are met

---

**Deployment completed successfully!** 🎉

Your CitusFlo Patient Journey APIs are now running on AWS with:
- ✅ High availability (Multi-AZ RDS)
- ✅ Auto-scaling (ECS Fargate)
- ✅ Load balancing (ALB)
- ✅ Monitoring (CloudWatch)
- ✅ Security (VPC, Security Groups)
