# AWS Deployment Files

This folder contains all deployment-related files for the CitusFlo Patient Journey APIs.

## 📁 Contents

### Deployment Scripts
- **`deploy-production.sh`** - Main deployment script with automated database initialization
- **`troubleshoot-deployment.sh`** - Comprehensive troubleshooting and diagnostics tool

### CloudFormation Templates
- **`cloudformation-production.yaml`** - Complete production infrastructure template
- **`cloudformation.yaml`** - Basic infrastructure template
- **`cloudformation-https.yaml`** - HTTPS-enabled template

### Documentation
- **`DEPLOYMENT.md`** - Comprehensive deployment guide with troubleshooting

## 🚀 Quick Start

### Deploy to AWS
```bash
# From project root directory
./aws/deploy/deploy-production.sh --domain
```

### Troubleshoot Issues
```bash
# From project root directory
./aws/deploy/troubleshoot-deployment.sh
```

## 📋 Prerequisites

- AWS CLI configured with appropriate permissions
- Docker installed and running
- Domain name (optional, for custom domain setup)

## 🔧 Features

- **Automated Database Initialization** - Creates tables and admin user
- **HTTPS Support** - SSL/TLS certificates via ACM
- **Custom Domain Integration** - Route53 DNS management
- **Comprehensive Troubleshooting** - Auto-diagnosis and fix capabilities
- **Security Best Practices** - Proper VPC, security groups, and encryption

## 🆘 Support

For deployment issues:
1. Run `./aws/deploy/troubleshoot-deployment.sh`
2. Check `DEPLOYMENT.md` for detailed troubleshooting
3. Review AWS CloudWatch logs

## 📝 Default Super Admin Credentials

After successful deployment:
- **Username**: `username`
- **Password**: `password`
- **Email**: `account@citusflo.com`
- **Role**: `super_admin`

> ⚠️ **Important**: Change these credentials in production!
