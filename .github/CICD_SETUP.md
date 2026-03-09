# CI/CD Setup Guide

Complete guide pre nastavenie GitHub Actions workflows pre house-price-mlops projekt.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GitHub Secrets Configuration](#github-secrets-configuration)
3. [GitHub Environments Setup](#github-environments-setup)
4. [Workflows Overview](#workflows-overview)
5. [First-Time Setup](#first-time-setup)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Pred nastavením CI/CD pipelines musíš mať:

- ✅ **AWS Account** s credentials (Access Key ID + Secret Access Key)
- ✅ **Terraform Infrastructure Deployed**:
  - MLflow server (KROK 2)
  - SageMaker resources (KROK 4)
  - Endpoint infrastructure (KROK 5)
- ✅ **ECR Repository** vytvorený (cez Terraform)
- ✅ **Training Data** uploadnutá do S3
- ✅ **GitHub Repository** s admin prístupom

---

## GitHub Secrets Configuration

### 1. Navigate to Repository Settings

```
GitHub Repository → Settings → Secrets and variables → Actions → New repository secret
```

### 2. Required Secrets

Pridaj nasledujúce secrets:

#### AWS Credentials

| Secret Name | Description | Example Value | Where to Get |
|------------|-------------|---------------|--------------|
| `AWS_ACCESS_KEY_ID` | AWS Access Key ID | `AKIAIOSFODNN7EXAMPLE` | AWS IAM Console |
| `AWS_SECRET_ACCESS_KEY` | AWS Secret Access Key | `wJalrXUtnFEMI/K7MDENG/...` | AWS IAM Console |

**How to create AWS credentials:**
```bash
# Option 1: AWS Console
1. Go to IAM → Users → Your user → Security credentials
2. Create access key → Use case: CLI
3. Download .csv file

# Option 2: AWS CLI
aws iam create-access-key --user-name your-username
```

**IAM Permissions Required:**
- AmazonEC2ContainerRegistryFullAccess
- AmazonSageMakerFullAccess
- AmazonS3FullAccess
- CloudWatchFullAccess (optional)

#### SageMaker Configuration

| Secret Name | Description | Example Value | Where to Get |
|------------|-------------|---------------|--------------|
| `SAGEMAKER_ROLE_ARN` | SageMaker execution role ARN | `arn:aws:iam::123456789:role/...` | Terraform output |
| `S3_DATA_BUCKET` | S3 bucket pre training data | `house-price-mlops-prod-data-abc123` | Terraform output |

**Get from Terraform:**
```bash
cd infra/terraform/sagemaker
terraform output sagemaker_execution_role_arn
terraform output s3_data_bucket_name
```

#### MLflow Configuration

| Secret Name | Description | Example Value | Where to Get |
|------------|-------------|---------------|--------------|
| `MLFLOW_TRACKING_URI` | MLflow server URL | `http://mlflow-alb-123.eu-west-1.elb.amazonaws.com` | Terraform output |

**Get from Terraform:**
```bash
cd infra/terraform/mlflow-server
terraform output mlflow_tracking_uri
```

### 3. Verify Secrets

Po pridaní secretov by si mal vidieť:

```
Repository secrets (5)
├── AWS_ACCESS_KEY_ID
├── AWS_SECRET_ACCESS_KEY
├── SAGEMAKER_ROLE_ARN
├── S3_DATA_BUCKET
└── MLFLOW_TRACKING_URI
```

---

## GitHub Environments Setup

GitHub Environments umožňujú:
- Manual approval pre production deployments
- Environment-specific secrets
- Deployment history tracking

### 1. Create Environments

```
GitHub Repository → Settings → Environments → New environment
```

Create **2 environments**:

#### Environment: `staging`

- **Deployment branches**: Selected branches → `main`
- **Environment secrets**: None (uses repository secrets)
- **Reviewers**: None (automatic deployment)

#### Environment: `production`

- **Deployment branches**: Selected branches → `main`
- **Environment secrets**: None (uses repository secrets)
- **Reviewers**: Add yourself or team members
  - ✅ **Required reviewers**: 1 person minimum
  - This ensures manual approval before production deployment

### 2. Environment Protection Rules (Optional)

Pre production environment môžeš pridať:

- **Wait timer**: 5 minutes delay before deployment
- **Deployment branches**: Only `main` branch
- **Prevent self-review**: Reviewers cannot approve their own deployments

---

## Workflows Overview

### Workflow 1: `ci.yml` - Continuous Integration

**Trigger:** Pull requests a push do `main`/`develop`

**Jobs:**
1. **lint** - Code quality checks (Black, Flake8, isort)
2. **test** - Unit tests s coverage (Python 3.10, 3.11)
3. **security** - Security scan (Bandit)
4. **dependencies** - Vulnerability check (pip-audit)
5. **ci-success** - Summary job (required for merge)

**Duration:** ~3-5 minutes

**Status Required for Merge:** Yes (via branch protection)

---

### Workflow 2: `cd.yml` - Continuous Deployment

**Trigger:** Push do `main` branch alebo manual dispatch

**Jobs:**
1. **build-image** - Build a push Docker image do ECR
2. **train** - Run SageMaker training job
3. **register-model** - Register model to MLflow Staging
4. **deploy-staging** - Deploy to staging endpoint (automatic)
5. **deploy-production** - Deploy to production endpoint (manual approval)

**Duration:** ~15-20 minutes (training: ~10min, deployment: ~5min)

**Manual Approval:** Required for production step

**Inputs (manual dispatch):**
- `deploy_to_production` - Skip staging, deploy directly to prod

---

### Workflow 3: `scheduled-retrain.yml` - Scheduled Retraining

**Trigger:** Weekly (Monday 2 AM UTC) alebo manual dispatch

**Jobs:**
1. **check-data** - Check if retraining is needed
2. **get-image** - Get latest ECR image
3. **train** - Run training job
4. **evaluate** - Evaluate model metrics (RMSE, R²)
5. **register** - Register model if metrics pass threshold
6. **notify** - Send notification summary

**Decision Criteria:**
- **RMSE < 0.15** (customizable)
- **R² > 0.80** (customizable)
- If criteria met → Register to Staging
- If criteria fail → Manual review needed

**Duration:** ~10-15 minutes

**Inputs (manual dispatch):**
- `instance_type` - SageMaker instance type
- `experiment_name` - MLflow experiment name

---

### Workflow 4: `deploy-model.yml` - Manual Model Deployment

**Trigger:** Manual dispatch only

**Jobs:**
1. **validate** - Validate inputs
2. **get-image** - Get ECR image
3. **deploy-mlflow** - Deploy from MLflow Registry
4. **deploy-s3** - Deploy from S3 URI
5. **summary** - Print deployment summary

**Use Cases:**
- Deploy specific model version
- Rollback to previous version
- Test model in staging before production
- Deploy from S3 without MLflow

**Inputs:**
- `model_source` - mlflow-staging | mlflow-production | mlflow-version | s3-uri
- `model_version` - MLflow version number (if source=mlflow-version)
- `model_s3_uri` - S3 path to model.tar.gz (if source=s3-uri)
- `environment` - staging | production
- `instance_type` - ml.t2.medium | ml.m5.large | ml.m5.xlarge | ml.m5.2xlarge
- `instance_count` - Number of instances (1-10)
- `update_existing` - Update existing endpoint (zero-downtime)

**Duration:** ~5-10 minutes

---

## First-Time Setup

### Step 1: Configure Secrets

```bash
# 1. Get Terraform outputs
cd infra/terraform/sagemaker
terraform output

cd ../mlflow-server
terraform output

# 2. Add secrets to GitHub
# Go to: Settings → Secrets and variables → Actions
# Add all required secrets (see table above)
```

### Step 2: Upload Training Data

```bash
# Upload train.csv to S3
DATA_BUCKET=$(cd infra/terraform/sagemaker && terraform output -raw s3_data_bucket_name)
aws s3 cp data/train.csv s3://$DATA_BUCKET/data/train.csv
```

### Step 3: Build Initial Docker Image

```bash
# Build and push Docker image
./scripts/build_and_push.sh eu-west-1

# Verify image exists
aws ecr describe-images --repository-name house-price-mlops
```

### Step 4: Run First Training Job (Manual)

```bash
# Option A: Via GitHub Actions
# Go to: Actions → CD - Train and Deploy → Run workflow

# Option B: Via CLI
python scripts/run_training_job.py \
  --s3-data s3://$DATA_BUCKET/data/train.csv \
  --job-name initial-training \
  --ecr-image <ECR_IMAGE_URI>:latest \
  --role <SAGEMAKER_ROLE_ARN> \
  --mlflow-tracking-uri <MLFLOW_URI> \
  --instance-type ml.m5.xlarge
```

### Step 5: Verify Workflow Runs

```bash
# Check GitHub Actions status
# Go to: Actions tab

# Expected workflows after push to main:
# ✅ CI - Tests and Linting
# ✅ CD - Train and Deploy (if push to main)
```

---

## Usage Examples

### Example 1: Regular Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/improve-model

# 2. Make changes
# ... edit src/train/train.py ...

# 3. Commit and push
git add .
git commit -m "Improve model hyperparameters"
git push origin feature/improve-model

# 4. Create PR
# → Triggers CI workflow (lint, test, security)

# 5. Merge to main
# → Triggers CD workflow (build, train, deploy to staging)

# 6. Approve production deployment
# Go to: Actions → CD workflow → Review deployments → Approve
```

### Example 2: Deploy Specific Model Version

```bash
# Scenario: Want to deploy model version 5 to production

# 1. Go to: Actions → Deploy Model to Endpoint → Run workflow
# 2. Set inputs:
#    - model_source: mlflow-version
#    - model_version: 5
#    - environment: production
#    - instance_type: ml.m5.xlarge
#    - instance_count: 2
#    - update_existing: true
# 3. Run workflow
# 4. Approve production deployment
```

### Example 3: Rollback to Previous Model

```bash
# Scenario: Production model has issues, rollback to staging

# 1. Go to: Actions → Deploy Model to Endpoint → Run workflow
# 2. Set inputs:
#    - model_source: mlflow-staging
#    - environment: production
#    - instance_type: ml.m5.xlarge
#    - instance_count: 2
#    - update_existing: true
# 3. Run workflow
# 4. Approve deployment
```

### Example 4: Scheduled Retraining

```bash
# Automatic: Runs every Monday at 2 AM UTC

# Manual trigger:
# 1. Go to: Actions → Scheduled Model Retraining → Run workflow
# 2. Set inputs (optional):
#    - instance_type: ml.m5.xlarge
#    - experiment_name: house-prices-manual
# 3. Run workflow

# Check results:
# 1. Go to workflow run
# 2. View "Notification" step for summary
# 3. If metrics pass → Model registered to Staging
# 4. If metrics fail → Manual review needed
```

---

## Troubleshooting

### Issue 1: CI Tests Failing

**Symptom:** Black/Flake8/isort checks fail

**Solution:**
```bash
# Run locally to fix
black src/ tests/ scripts/
isort src/ tests/ scripts/
flake8 src/ tests/ scripts/ --max-line-length=100 --extend-ignore=E203,W503

# Commit fixes
git add .
git commit -m "Fix code formatting"
git push
```

### Issue 2: Docker Build Fails

**Symptom:** ECR push fails in CD workflow

**Possible Causes:**
- ❌ AWS credentials expired
- ❌ ECR repository doesn't exist
- ❌ Dockerfile syntax error

**Solution:**
```bash
# Check ECR repository exists
aws ecr describe-repositories --repository-names house-price-mlops

# Test build locally
docker build -t house-price-mlops:test .

# Check AWS credentials
aws sts get-caller-identity
```

### Issue 3: Training Job Fails

**Symptom:** SageMaker training job fails

**Possible Causes:**
- ❌ S3 data doesn't exist
- ❌ IAM role missing permissions
- ❌ Docker image issue

**Solution:**
```bash
# Check training data exists
aws s3 ls s3://$DATA_BUCKET/data/train.csv

# Check SageMaker logs
aws logs tail /aws/sagemaker/TrainingJobs --follow

# Verify IAM role permissions
aws iam get-role --role-name <ROLE_NAME>
```

### Issue 4: MLflow Registry Fails

**Symptom:** Model registration to MLflow fails

**Possible Causes:**
- ❌ MLflow server unreachable
- ❌ Wrong MLFLOW_TRACKING_URI
- ❌ Experiment doesn't exist

**Solution:**
```bash
# Test MLflow connection
curl $MLFLOW_TRACKING_URI/health

# Check experiment exists
python -c "
import mlflow
mlflow.set_tracking_uri('$MLFLOW_TRACKING_URI')
print(mlflow.get_experiment_by_name('house-prices-production'))
"
```

### Issue 5: Endpoint Deployment Fails

**Symptom:** SageMaker endpoint deployment fails

**Possible Causes:**
- ❌ Model artifacts missing in S3
- ❌ Docker image inference.py error
- ❌ Endpoint already exists (without --update-existing)

**Solution:**
```bash
# Check model exists
aws s3 ls $MODEL_S3_URI

# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name house-price-staging

# View endpoint logs
aws logs tail /aws/sagemaker/Endpoints/house-price-staging --follow

# Delete and recreate
aws sagemaker delete-endpoint --endpoint-name house-price-staging
# Re-run deployment workflow
```

### Issue 6: Production Approval Timeout

**Symptom:** Production deployment waiting for approval

**Solution:**
```bash
# 1. Go to: Actions → CD workflow run
# 2. Scroll to "deploy-production" job
# 3. Click "Review deployments"
# 4. Select "production" environment
# 5. Click "Approve and deploy"

# Note: Approval expires after 30 days (GitHub default)
```

---

## Best Practices

### 1. Branch Protection Rules

Enable in: `Settings → Branches → Add rule`

For `main` branch:
- ✅ Require a pull request before merging
- ✅ Require status checks to pass: `CI Success`
- ✅ Require conversation resolution before merging
- ✅ Do not allow bypassing the above settings

### 2. Monitoring

Set up monitoring:
- CloudWatch Alarms (via Terraform endpoint module)
- Email notifications for failed workflows
- Slack integration for deployment notifications

### 3. Security

- 🔒 Never commit AWS credentials to repository
- 🔒 Rotate AWS access keys regularly (every 90 days)
- 🔒 Use least-privilege IAM roles
- 🔒 Enable GitHub secret scanning
- 🔒 Review Dependabot alerts

### 4. Cost Optimization

- Use Spot instances for training (70% discount)
- Delete unused endpoints after testing
- Schedule endpoint scale-down at night
- Use ml.t2.medium for staging (cheap)

### 5. Testing

Before production deployment:
1. Run smoke tests on staging
2. Load test endpoint
3. Verify model metrics
4. Check CloudWatch alarms
5. Review CloudWatch logs

---

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS SageMaker Documentation](https://docs.aws.amazon.com/sagemaker/)
- [MLflow Documentation](https://mlflow.org/docs/latest/index.html)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

## Support

For issues with:
- **CI/CD Workflows**: Check GitHub Actions logs
- **AWS Resources**: Check CloudWatch logs
- **MLflow**: Check MLflow UI and server logs
- **Terraform**: Check Terraform state and outputs

**Emergency Rollback:**
```bash
# If production is broken, rollback immediately:
# 1. Go to: Actions → Deploy Model to Endpoint
# 2. Deploy previous working version from MLflow Registry
# 3. Approve production deployment
# 4. Verify endpoint health
```

---

## License

MIT
