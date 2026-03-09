# MLflow Tracking Server Infrastructure

Terraform konfigurácia pre MLflow Tracking Server na AWS.

## Architektúra

- **ECS Fargate**: Kontajnerizovaný MLflow server
- **RDS PostgreSQL**: Backend store pre metriky a metadata
- **S3**: Artifact store pre modely
- **Application Load Balancer**: HTTPS endpoint
- **VPC**: Izolovaná sieť s public/private subnets

## Použitie

Táto konfigurácia bude vytvorená v **Kroku 2** roadmapy.

```bash
cd infra/terraform/mlflow-server
terraform init
terraform plan
terraform apply
```

## Výstupy

- `mlflow_tracking_uri`: MLflow tracking URI (https://...)
- `mlflow_s3_bucket`: S3 bucket pre artifacts
- `mlflow_db_endpoint`: RDS PostgreSQL endpoint

## Náklady

Odhadované mesačné náklady: ~$50-100 (Fargate + RDS db.t3.micro + S3)

---

**TODO**: Implementovať v Kroku 2
