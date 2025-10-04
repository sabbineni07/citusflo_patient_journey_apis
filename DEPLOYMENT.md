# CitusFlo Patient Journey APIs - Deployment Guide

## 🎯 Overview

This guide provides comprehensive instructions for deploying the CitusFlo Patient Journey APIs to AWS with HTTPS support and custom domain configuration.

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed and running
- Domain name (optional, for custom domain setup)
- Basic understanding of AWS services

## 🚀 Quick Start

### Option 1: Automated Deployment (Recommended)

```bash
# Full deployment with custom domain
./deploy-production.sh --domain

# Full deployment without custom domain
./deploy-production.sh

# Update existing deployment
./deploy-production.sh --type update

# Add HTTPS support only
./deploy-production.sh --type https-only
```

### Option 2: Manual Deployment

Follow the step-by-step guide below for manual deployment.

## 🔧 Architecture

The deployment creates the following AWS resources:

- **ECS Fargate Cluster**: Container orchestration
- **Application Load Balancer**: HTTPS termination and routing
- **RDS PostgreSQL**: Managed database
- **ECR Repository**: Container image storage
- **Route53**: DNS management (if custom domain)
- **ACM**: SSL certificate management
- **CloudWatch**: Logging and monitoring

## 📁 File Structure

```
├── deploy-production.sh          # Main deployment script
├── cloudformation-production.yaml # Complete infrastructure template
├── cloudformation.yaml          # Basic infrastructure template
├── cloudformation-https.yaml    # HTTPS-enabled template
├── DEPLOYMENT.md                # This guide
├── CORS-CONFIGURATION.md        # CORS setup guide
└── README.md                    # Project overview
```

## 🛠️ Deployment Options

### 1. Basic Deployment (HTTP only)

```bash
./deploy-production.sh
```

**What it creates:**
- ECS cluster and service
- Application Load Balancer (HTTP)
- RDS PostgreSQL database
- ECR repository
- Basic security groups

### 2. HTTPS Deployment (AWS-managed certificate)

```bash
./deploy-production.sh --type full
```

**What it adds:**
- SSL certificate via ACM
- HTTPS listener on port 443
- HTTP to HTTPS redirect
- Security group updates

### 3. Custom Domain Deployment

```bash
./deploy-production.sh --domain
```

**What it adds:**
- Route53 hosted zone (if needed)
- Custom SSL certificate
- DNS records for your domain
- Professional HTTPS URLs

## 🌐 Custom Domain Setup

### Prerequisites

- Domain registered (e.g., `yourdomain.com`)
- Access to domain's DNS settings

### Setup Process

1. **Run deployment with custom domain:**
   ```bash
   ./deploy-production.sh --domain
   ```

2. **Update domain nameservers:**
   - The script will provide nameservers to update at your domain registrar
   - Wait 24-48 hours for DNS propagation

3. **Test your domain:**
   ```bash
   curl https://api.yourdomain.com/health
   ```

### Manual Custom Domain Setup

If you prefer manual setup:

1. **Create SSL certificate:**
   ```bash
   aws acm request-certificate \
     --region us-east-1 \
     --domain-name api.yourdomain.com \
     --validation-method DNS
   ```

2. **Add validation records to Route53**

3. **Update HTTPS listener with certificate**

4. **Add CNAME record:**
   ```
   api.yourdomain.com → your-load-balancer-dns
   ```

## 🔐 Security Configuration

### SSL/TLS

- **Automatic HTTP to HTTPS redirect**
- **TLS 1.2+ encryption**
- **AWS-managed or custom SSL certificates**
- **HSTS headers** (configurable)

### Network Security

- **VPC isolation**
- **Security groups with minimal access**
- **Private subnets for database**
- **Public subnets for load balancer only**

### Database Security

- **Encryption at rest**
- **Network isolation**
- **Automated backups**
- **Multi-AZ deployment**

## 📊 Monitoring and Logging

### CloudWatch Integration

- **ECS task logs** in CloudWatch Logs
- **Load balancer metrics**
- **Database performance insights**
- **Custom application metrics**

### Health Checks

- **Application health endpoint**: `/health`
- **Load balancer health checks**
- **ECS service health monitoring**

## 🧪 Testing Deployment

### Health Check

```bash
curl https://your-domain.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "patient-api"
}
```

### API Endpoints

```bash
# Login
curl https://your-domain.com/api/auth/login \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Get patients (with JWT token)
curl https://your-domain.com/api/patients \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🔍 Troubleshooting

### Common Issues

1. **DNS Resolution Issues**
   - Check nameserver configuration
   - Wait for DNS propagation (24-48 hours)
   - Verify Route53 hosted zone

2. **SSL Certificate Issues**
   - Ensure certificate validation records are added
   - Check certificate status in ACM
   - Verify domain ownership

3. **Load Balancer Issues**
   - Check security group rules
   - Verify target group health
   - Ensure ECS tasks are running

4. **Database Connection Issues**
   - Check security group rules
   - Verify database endpoint
   - Check connection string format

### Useful Commands

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name your-stack-name

# Check ECS service status
aws ecs describe-services --cluster your-cluster --services your-service

# Check load balancer health
aws elbv2 describe-target-health --target-group-arn your-target-group

# View application logs
aws logs tail /ecs/your-log-group --follow
```

## 💰 Cost Optimization

### Resource Sizing

- **ECS Tasks**: Start with 0.5 vCPU, 1GB RAM
- **RDS**: Use db.t3.micro for development
- **Load Balancer**: Application Load Balancer (fixed cost)

### Monitoring Costs

- **CloudWatch Logs**: Set retention periods
- **RDS**: Monitor storage usage
- **Data Transfer**: Monitor ALB data transfer

## 🔄 Updates and Maintenance

### Application Updates

```bash
# Update application code
./deploy-production.sh --type update
```

### Infrastructure Updates

```bash
# Update CloudFormation template
aws cloudformation update-stack \
  --stack-name your-stack \
  --template-body file://cloudformation-production.yaml
```

### Database Maintenance

- **Automated backups**: 7-day retention
- **Maintenance windows**: Configured automatically
- **Multi-AZ**: Automatic failover

## 📝 Environment Variables

The application uses the following environment variables:

- `FLASK_ENV`: Environment (production/staging/development)
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: Flask secret key
- `JWT_SECRET_KEY`: JWT signing key

## 🚨 Security Best Practices

1. **Regular Updates**: Keep dependencies updated
2. **Access Control**: Use IAM roles with minimal permissions
3. **Monitoring**: Set up CloudWatch alarms
4. **Backups**: Regular database backups
5. **SSL/TLS**: Always use HTTPS in production

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Review AWS CloudWatch logs
3. Verify resource configurations
4. Check security group rules

## 🎉 Success Indicators

Your deployment is successful when:

- ✅ Health endpoint returns 200 OK
- ✅ HTTPS URLs work without certificate warnings
- ✅ API endpoints respond correctly
- ✅ Database connections work
- ✅ Logs are being generated
- ✅ Load balancer shows healthy targets

---

**Next Steps:**
1. Test all API endpoints
2. Configure monitoring alerts
3. Set up automated backups
4. Update your frontend to use HTTPS URLs
5. Configure CI/CD pipeline (optional)
