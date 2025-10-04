# Quick Reference - CitusFlo Patient Journey APIs

## 🚀 Quick Deployment

```bash
# Make script executable and run
chmod +x deploy.sh
./deploy.sh
```

## 🔗 Application URLs

- **Health Check**: `http://production-patient-lb-1572933777.us-east-1.elb.amazonaws.com/health`
- **API Base**: `http://production-patient-lb-1572933777.us-east-1.elb.amazonaws.com/api/`

## 📊 Key Commands

### Check Status
```bash
# ECS Service
aws ecs describe-services --cluster production-citusflo-patient-cluster --services production-citusflo-patient-service --region us-east-1

# Health Check
curl http://production-patient-lb-1572933777.us-east-1.elb.amazonaws.com/health

# Logs
aws logs tail /ecs/production-citusflo-patient-api --follow --region us-east-1
```

### Update Application
```bash
# Rebuild and redeploy
./deploy.sh

# Or manually update ECS service
aws ecs update-service --cluster production-citusflo-patient-cluster --service production-citusflo-patient-service --force-new-deployment --region us-east-1
```

### Scale Application
```bash
# Scale to 3 instances
aws ecs update-service --cluster production-citusflo-patient-cluster --service production-citusflo-patient-service --desired-count 3 --region us-east-1
```

## 🗑️ Cleanup
```bash
aws cloudformation delete-stack --stack-name citusflo-patient-journey-api-infrastructure --region us-east-1
```

## 📁 Key Files
- `deploy.sh` - Main deployment script
- `cloudformation.yaml` - Infrastructure template
- `DEPLOYMENT_GUIDE.md` - Detailed documentation
