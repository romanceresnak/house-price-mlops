# SageMaker Infrastructure

Terraform konfigurácia pre AWS SageMaker resources.

## Resources Created

| Resource | Popis | Počet |
|----------|-------|-------|
| IAM Role | SageMaker execution role | 1 |
| IAM Policies | S3, ECR, CloudWatch, VPC access | 4 |
| S3 Buckets | Data + Models | 2 |
| ECR Repository | Docker images pre training | 1 |

## Features

- ✅ **IAM Roles**: Least privilege pre SageMaker training jobs
- ✅ **S3 Buckets**: Separated data and model storage
- ✅ **ECR Repository**: Container registry pre custom images
- ✅ **Encryption**: S3 encryption at rest (AES256)
- ✅ **Versioning**: S3 versioning enabled
- ✅ **Lifecycle**: Auto-cleanup old artifacts
- ✅ **Security**: Public access blocked na S3

## Quick Start

### 1. Konfigurácia

```bash
cd infra/terraform/sagemaker

# Kopíruj example config
cp terraform.tfvars.example terraform.tfvars

# Uprav terraform.tfvars
vim terraform.tfvars
```

### 2. Deploy

```bash
# Initialize
terraform init

# Plan
terraform plan

# Deploy
terraform apply
```

Deploy trvá **~1-2 minúty**.

### 3. Get Outputs

```bash
# Všetky outputs
terraform output

# Specific outputs
terraform output sagemaker_execution_role_arn
terraform output ecr_repository_url
terraform output s3_data_bucket_name
```

## Usage

### Upload Training Data

```bash
# Get bucket name
DATA_BUCKET=$(terraform output -raw s3_data_bucket_name)

# Upload data
aws s3 cp data/train.csv s3://$DATA_BUCKET/data/train.csv
aws s3 cp data/test.csv s3://$DATA_BUCKET/data/test.csv
```

### Build and Push Docker Image

```bash
# Get ECR URL
ECR_URL=$(terraform output -raw ecr_repository_url)
REGION=$(terraform output -raw aws_region)

# Build and push
./scripts/build_and_push.sh $REGION
```

### Run Training Job

```bash
# Get role ARN
ROLE_ARN=$(terraform output -raw sagemaker_execution_role_arn)
ECR_IMAGE=$(terraform output -raw ecr_repository_url):latest

# Run training
python scripts/run_training_job.py \
  --s3-data s3://$DATA_BUCKET/data/train.csv \
  --ecr-image $ECR_IMAGE \
  --role $ROLE_ARN
```

## Outputs

Po úspešnom deploy dostaneš:

```
sagemaker_execution_role_arn  = "arn:aws:iam::123456789:role/..."
s3_data_bucket_name           = "house-price-mlops-prod-data-abc12345"
s3_model_bucket_name          = "house-price-mlops-prod-models-abc12345"
ecr_repository_url            = "123456789.dkr.ecr.eu-west-1.amazonaws.com/house-price-mlops"
```

## IAM Permissions

SageMaker execution role má prístup k:

- ✅ S3: Data a Model buckets (read/write)
- ✅ S3: MLflow artifacts bucket (read/write) - ak nastavený
- ✅ ECR: Pull Docker images
- ✅ CloudWatch: Write logs
- ✅ VPC: Network interface management (pre VPC training)
- ✅ SageMaker: Full access

## S3 Bucket Structure

### Data Bucket

```
s3://house-price-mlops-prod-data-abc12345/
├── data/
│   ├── train.csv
│   └── test.csv
└── processed/
    └── ...
```

### Model Bucket

```
s3://house-price-mlops-prod-models-abc12345/
├── training-jobs/
│   ├── job-1/
│   │   └── model.tar.gz
│   └── job-2/
│       └── model.tar.gz
└── endpoints/
    └── ...
```

## ECR Repository

### Lifecycle Policy

- Keep last 10 tagged images (`latest`)
- Expire untagged images older than 14 days

### Image Scanning

- Automatic scanning on push
- Vulnerability detection

## Cost Estimate

| Component | Monthly Cost (USD) |
|-----------|-------------------|
| S3 Storage (100GB) | ~$2-3 |
| ECR Storage (10GB) | ~$1 |
| IAM Roles | $0 |
| **Total** | **~$3-4/month** |

**Notes:**
- SageMaker training jobs účtované separately (per hour)
- Data transfer costs môžu apply

## Monitoring

### S3 Metrics

```bash
# List objects
aws s3 ls s3://$(terraform output -raw s3_data_bucket_name)/

# Bucket size
aws s3 ls s3://$(terraform output -raw s3_data_bucket_name) --recursive --summarize --human-readable
```

### ECR Metrics

```bash
# List images
aws ecr list-images --repository-name $(terraform output -raw ecr_repository_name)

# Image details
aws ecr describe-images --repository-name $(terraform output -raw ecr_repository_name)
```

### SageMaker Jobs

```bash
# List training jobs
aws sagemaker list-training-jobs

# Job details
aws sagemaker describe-training-job --training-job-name <job-name>
```

## Troubleshooting

### ECR Push Failed

```bash
# Re-authenticate
aws ecr get-login-password --region eu-west-1 | \
  docker login --username AWS --password-stdin \
  $(terraform output -raw ecr_repository_url)
```

### S3 Access Denied

```bash
# Check IAM role permissions
aws iam get-role-policy \
  --role-name $(terraform output -raw sagemaker_execution_role_name) \
  --policy-name s3-access
```

### Training Job Failed

```bash
# Check CloudWatch logs
aws logs tail /aws/sagemaker/TrainingJobs --follow
```

## Integration s MLflow

Ak chceš integrovať s MLflow:

1. Deploy MLflow server (Krok 2)
2. Get MLflow S3 bucket ARN:
   ```bash
   cd ../mlflow-server
   terraform output mlflow_s3_bucket_arn
   ```
3. Nastav v `terraform.tfvars`:
   ```hcl
   mlflow_s3_bucket_arn = "arn:aws:s3:::mlflow-bucket"
   ```
4. Re-apply:
   ```bash
   terraform apply
   ```

## Cleanup

```bash
# POZOR: Vymaže všetky resources!
terraform destroy

# Ak chceš ponechať S3 data:
# 1. Nastav s3_force_destroy = false
# 2. terraform apply
# 3. terraform destroy
```

## License

MIT
