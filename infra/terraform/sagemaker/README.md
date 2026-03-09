# SageMaker Infrastructure

Terraform konfigurácia pre AWS SageMaker resources.

## Resources

- **IAM Roles**: SageMaker execution role s prístupom k S3, ECR, CloudWatch
- **S3 Buckets**:
  - Data bucket pre training dáta
  - Model bucket pre output artifacts
- **ECR Repository**: Docker image registry pre custom training containers
- **VPC Endpoints** (optional): Privátna konektivita pre SageMaker

## Použitie

Táto konfigurácia bude vytvorená v **Kroku 2** roadmapy.

```bash
cd infra/terraform/sagemaker
terraform init
terraform plan
terraform apply
```

## Výstupy

- `sagemaker_execution_role_arn`: ARN role pre SageMaker jobs
- `s3_data_bucket`: S3 bucket pre training dáta
- `s3_model_bucket`: S3 bucket pre modely
- `ecr_repository_url`: ECR repository URL

## Permissions

SageMaker execution role bude mať prístup k:
- S3 buckets (read/write)
- ECR (pull images)
- CloudWatch Logs (write logs)
- MLflow S3 artifacts bucket (write)

---

**TODO**: Implementovať v Kroku 2
