# GitHub Actions Workflows

CI/CD pipelines pre house-price-mlops projekt.

## 📋 Workflows Overview

### 🔍 CI - Tests and Linting (`ci.yml`)

**Trigger:** PR a push do `main`/`develop`

**What it does:**
- ✅ Code quality checks (Black, Flake8, isort)
- ✅ Unit tests (Python 3.10, 3.11)
- ✅ Security scan (Bandit)
- ✅ Dependency vulnerabilities (pip-audit)

**Duration:** ~3-5 minutes

---

### 🚀 CD - Train and Deploy (`cd.yml`)

**Trigger:** Push do `main` alebo manual

**What it does:**
1. Build Docker image → push do ECR
2. Run SageMaker training job
3. Register model do MLflow Staging
4. Deploy to **staging** endpoint (automatic)
5. Deploy to **production** endpoint (manual approval required)

**Duration:** ~15-20 minutes

**Manual Inputs:**
- `deploy_to_production` - Skip staging, go directly to prod

---

### 🔄 Scheduled Retraining (`scheduled-retrain.yml`)

**Trigger:** Weekly (Monday 2 AM UTC) alebo manual

**What it does:**
1. Check if retraining is needed
2. Run training with latest data
3. Evaluate model metrics (RMSE, R²)
4. Register to Staging **only if metrics pass threshold**
5. Send notification summary

**Quality Gates:**
- RMSE < 0.15
- R² > 0.80

**Duration:** ~10-15 minutes

**Manual Inputs:**
- `instance_type` - Training instance type
- `experiment_name` - MLflow experiment name

---

### 🎯 Deploy Model (`deploy-model.yml`)

**Trigger:** Manual only

**What it does:**
Deploy specific model version to staging/production endpoint.

**Use Cases:**
- Deploy specific MLflow version
- Rollback to previous model
- Deploy from S3 without MLflow
- Test model before production

**Inputs:**
- `model_source` - Where to get model:
  - `mlflow-staging` - Latest from Staging stage
  - `mlflow-production` - Latest from Production stage
  - `mlflow-version` - Specific version number
  - `s3-uri` - Direct S3 path to model.tar.gz
- `model_version` - Version number (if source=mlflow-version)
- `model_s3_uri` - S3 URI (if source=s3-uri)
- `environment` - Target: `staging` | `production`
- `instance_type` - Instance type (ml.t2.medium, ml.m5.large, etc.)
- `instance_count` - Number of instances
- `update_existing` - Update endpoint with zero downtime

**Duration:** ~5-10 minutes

---

## 🎬 Quick Start

### 1. Setup GitHub Secrets

See [CICD_SETUP.md](../CICD_SETUP.md) for detailed instructions.

Required secrets:
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
SAGEMAKER_ROLE_ARN
S3_DATA_BUCKET
MLFLOW_TRACKING_URI
```

### 2. Setup GitHub Environments

Create 2 environments:
- **staging** - Automatic deployment
- **production** - Requires manual approval (add reviewers)

### 3. Run First Workflow

```bash
# Push to main triggers CD workflow
git push origin main

# Or run manually:
# Go to: Actions → CD - Train and Deploy → Run workflow
```

---

## 📊 Workflow Decision Matrix

| Scenario | Workflow | Trigger | Approval |
|----------|----------|---------|----------|
| Code change → test | CI | Automatic (PR) | None |
| Code change → deploy | CD | Automatic (push to main) | Production step |
| Weekly retraining | Scheduled Retrain | Automatic (cron) | None |
| Deploy specific version | Deploy Model | Manual | Production env |
| Rollback model | Deploy Model | Manual | Production env |
| Test staging | CD or Deploy Model | Manual | None |

---

## 🔄 Typical Development Flow

### Feature Development
```
1. Create branch: feature/new-model
2. Make changes
3. Push → Triggers CI (lint, test, security)
4. Create PR → CI must pass
5. Merge to main → Triggers CD
6. CD runs: build → train → deploy staging
7. Approve production → Deploy to prod
```

### Scheduled Maintenance
```
1. Monday 2 AM UTC: Scheduled retrain runs
2. If metrics good → Register to Staging
3. If metrics bad → Manual review needed
4. Manually deploy to prod (Deploy Model workflow)
```

### Emergency Rollback
```
1. Go to: Actions → Deploy Model to Endpoint
2. Select: model_source=mlflow-production (previous working version)
3. Select: environment=production
4. Run workflow
5. Approve deployment
```

---

## 🛠 Common Tasks

### Deploy Latest Staging Model to Production
```
Actions → Deploy Model to Endpoint → Run workflow
├── model_source: mlflow-staging
├── environment: production
├── instance_type: ml.m5.xlarge
├── instance_count: 2
└── update_existing: true
```

### Deploy Specific Model Version
```
Actions → Deploy Model to Endpoint → Run workflow
├── model_source: mlflow-version
├── model_version: 5
├── environment: staging (test first!)
└── update_existing: true
```

### Rollback Production
```
Actions → Deploy Model to Endpoint → Run workflow
├── model_source: mlflow-version
├── model_version: <previous-version>
├── environment: production
└── update_existing: true
```

### Manual Retrain with Custom Settings
```
Actions → Scheduled Model Retraining → Run workflow
├── instance_type: ml.m5.2xlarge (for faster training)
└── experiment_name: house-prices-manual
```

---

## 📈 Monitoring Workflows

### View Workflow Runs
```
GitHub → Actions → Select workflow → View runs
```

### Check Logs
```
Click workflow run → Click job → View step logs
```

### Download Artifacts
```
Click workflow run → Artifacts section → Download
```

---

## 🐛 Debugging

### Workflow Failed?

1. **Check logs**: Click failed job → View step logs
2. **Check AWS**: CloudWatch logs for SageMaker/ECR errors
3. **Check MLflow**: MLflow UI for experiment/registry issues
4. **Re-run**: Click "Re-run failed jobs"

### Common Issues

| Error | Solution |
|-------|----------|
| AWS credentials invalid | Rotate secrets in GitHub |
| ECR repository not found | Create via Terraform |
| S3 data not found | Upload train.csv to S3 |
| MLflow unreachable | Check MLflow server status |
| Endpoint already exists | Use `update_existing: true` |

---

## 📚 Documentation

- **Setup Guide**: [CICD_SETUP.md](../CICD_SETUP.md) - Detailed setup instructions
- **Main README**: [../README.md](../../README.md) - Project overview
- **Terraform READMEs**: Infrastructure documentation

---

## 💡 Best Practices

1. **Always test in staging first** before production
2. **Review CloudWatch metrics** after deployment
3. **Monitor costs** - delete unused endpoints
4. **Rotate AWS credentials** every 90 days
5. **Use branch protection** for main branch
6. **Enable required reviewers** for production
7. **Tag releases** when deploying to production

---

## 🔒 Security

- ✅ All secrets stored in GitHub Secrets
- ✅ AWS credentials never in code
- ✅ Production requires manual approval
- ✅ Security scan on every PR (Bandit)
- ✅ Dependency vulnerability check (pip-audit)

---

## 📞 Support

Need help?
1. Check [CICD_SETUP.md](../CICD_SETUP.md) troubleshooting section
2. Review GitHub Actions logs
3. Check CloudWatch logs for AWS issues
4. Review MLflow UI for model registry issues

---

## License

MIT
