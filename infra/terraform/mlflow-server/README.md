# MLflow Tracking Server Infrastructure

Production-ready Terraform konfigurácia pre MLflow Tracking Server na AWS.

## Architektúra

```
┌─────────────────────────────────────────────────────────────┐
│                          Internet                            │
└───────────────────────────┬─────────────────────────────────┘
                            │
                    ┌───────▼────────┐
                    │ Application    │
                    │ Load Balancer  │
                    │  (Public)      │
                    └───────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼─────┐       ┌─────▼────┐       ┌─────▼────┐
   │ ECS Task │       │ ECS Task │       │ ECS Task │
   │  MLflow  │       │  MLflow  │       │  MLflow  │
   │ (Private)│       │ (Private)│       │ (Private)│
   └────┬─────┘       └─────┬────┘       └─────┬────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
        ┌─────▼────┐               ┌──────▼──────┐
        │   RDS    │               │  S3 Bucket  │
        │ Postgres │               │  Artifacts  │
        │(Private) │               └─────────────┘
        └──────────┘
```

## Features

- ✅ **Fargate ECS**: Serverless containers bez server management
- ✅ **RDS PostgreSQL**: Managed databáza pre MLflow metadata
- ✅ **S3 Artifact Store**: Škálovateľný storage pre modely
- ✅ **Application Load Balancer**: HTTPS/HTTP endpoint
- ✅ **VPC**: Izolovaná sieť s public/private subnets
- ✅ **Auto-scaling**: CPU/Memory based scaling
- ✅ **CloudWatch**: Monitoring a logy
- ✅ **Secrets Manager**: Bezpečné ukladanie DB credentials
- ✅ **Security Groups**: Network isolation
- ✅ **Cost optimized**: NAT Gateway, lifecycle policies

## Resources Created

| Resource | Popis | Počet |
|----------|-------|-------|
| VPC | Virtual Private Cloud | 1 |
| Subnets | Public (2) + Private (2) | 4 |
| NAT Gateway | Internet access pre private subnets | 2 |
| ALB | Application Load Balancer | 1 |
| ECS Cluster | Fargate cluster | 1 |
| ECS Service | MLflow service | 1 |
| RDS PostgreSQL | Backend store | 1 |
| S3 Buckets | Artifacts + ALB logs | 2 |
| IAM Roles | ECS execution + task roles | 2 |
| Security Groups | ALB, ECS, RDS | 3 |
| CloudWatch | Log groups + alarms | 4 |
| Secrets Manager | DB credentials | 1 |

## Predpoklady

```bash
# Terraform 1.5+
terraform --version

# AWS CLI nakonfigurované
aws --version
aws sts get-caller-identity

# Dostatočné AWS permissions pre:
# - VPC, Subnets, Internet Gateway, NAT Gateway
# - ECS (Fargate), ECR
# - RDS, S3, Secrets Manager
# - IAM roles a policies
# - CloudWatch Logs a Alarms
```

## Quick Start

### 1. Konfigurácia

```bash
cd infra/terraform/mlflow-server

# Kopíruj example config
cp terraform.tfvars.example terraform.tfvars

# Uprav terraform.tfvars
vim terraform.tfvars
```

**Dôležité nastavenia v `terraform.tfvars`:**
```hcl
aws_region  = "eu-west-1"
environment = "prod"

# RDS credentials
db_username = "mlflow_admin"
db_password = "CHANGE_ME_STRONG_PASSWORD"  # ⚠️ Zmeň!

# ECS resources
mlflow_cpu           = 512   # 0.5 vCPU
mlflow_memory        = 1024  # 1 GB RAM
mlflow_desired_count = 1
```

### 2. Deploy

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy infrastructure
terraform apply

# Potvrď s "yes"
```

Deploy trvá **~10-15 minút**.

### 3. Get MLflow URI

```bash
# Po úspešnom deploy
terraform output mlflow_tracking_uri

# Príklad výstupu:
# http://mlflow-alb-123456789.eu-west-1.elb.amazonaws.com
```

### 4. Test Connection

```bash
# Nastav environment variable
export MLFLOW_TRACKING_URI=$(terraform output -raw mlflow_tracking_uri)

# Test z Pythonu
python -c "
import mlflow
mlflow.set_tracking_uri('$MLFLOW_TRACKING_URI')
print('✅ Connected to MLflow:', mlflow.get_tracking_uri())
"
```

## Outputs

Po úspešnom deploy dostaneš:

```bash
# Všetky outputs
terraform output

# Dôležité outputs:
mlflow_tracking_uri        # MLflow tracking URI
mlflow_s3_bucket_name      # S3 bucket pre artifacts
mlflow_db_endpoint         # RDS endpoint
ecs_cluster_name           # ECS cluster
vpc_id                     # VPC ID
```

## Configuration Options

### Production Setup

Pre production:

```hcl
# terraform.tfvars
environment = "prod"

# RDS
db_instance_class = "db.t3.small"  # Alebo db.r5.large
multi_az          = true

# ECS
mlflow_cpu           = 1024  # 1 vCPU
mlflow_memory        = 2048  # 2 GB
mlflow_desired_count = 2     # Min 2 tasks

# Security
enable_https    = true
certificate_arn = "arn:aws:acm:eu-west-1:123456789:certificate/..."
```

### HTTPS Setup

1. Vytvor ACM certifikát v AWS Console
2. Validuj doménu (DNS alebo email)
3. Nastav v `terraform.tfvars`:

```hcl
enable_https    = true
certificate_arn = "arn:aws:acm:..."
domain_name     = "mlflow.yourdomain.com"
```

4. V Route53 vytvor A record:
   - Name: `mlflow.yourdomain.com`
   - Type: A - Alias
   - Target: ALB DNS name

### Cost Optimization

**Development:**
```hcl
db_instance_class    = "db.t3.micro"
mlflow_cpu           = 256
mlflow_memory        = 512
mlflow_desired_count = 1
availability_zones   = ["eu-west-1a"]  # Single AZ
```

**Production:**
```hcl
db_instance_class    = "db.t3.small"
mlflow_cpu           = 1024
mlflow_memory        = 2048
mlflow_desired_count = 2
availability_zones   = ["eu-west-1a", "eu-west-1b"]
```

## Monitoring

### CloudWatch Dashboards

```bash
# ECS Metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ClusterName,Value=$(terraform output -raw ecs_cluster_name) \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### Logs

```bash
# MLflow logs
aws logs tail /ecs/house-price-mlops-prod-mlflow --follow

# RDS logs
aws rds describe-db-log-files \
  --db-instance-identifier $(terraform output -raw mlflow_db_endpoint | cut -d: -f1)
```

### Alarms

Terraform vytvorí tieto alarmy:
- RDS High CPU (>80%)
- RDS Low Storage (<2GB)

## Maintenance

### Update MLflow Version

```hcl
# terraform.tfvars
mlflow_image = "ghcr.io/mlflow/mlflow:2.10.0"  # Specific version
```

```bash
terraform apply
```

### Scale Up/Down

```hcl
# terraform.tfvars
mlflow_desired_count = 3  # Scale to 3 tasks
```

```bash
terraform apply
```

### Backup & Restore

RDS automaticky vytvára daily backups (retention: 7 dní).

**Manual snapshot:**
```bash
aws rds create-db-snapshot \
  --db-instance-identifier house-price-mlops-prod-mlflow-db \
  --db-snapshot-identifier manual-snapshot-$(date +%Y%m%d)
```

## Troubleshooting

### MLflow nedostupný

```bash
# 1. Check ECS tasks
aws ecs list-tasks --cluster $(terraform output -raw ecs_cluster_name)

# 2. Check task logs
aws logs tail /ecs/house-price-mlops-prod-mlflow --follow

# 3. Check ALB target health
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw alb_target_group_arn)
```

### RDS Connection Issues

```bash
# Test DB connectivity z ECS task
aws ecs execute-command \
  --cluster $(terraform output -raw ecs_cluster_name) \
  --task <task-id> \
  --container mlflow \
  --interactive \
  --command "/bin/bash"

# Inside container:
psql -h $DB_ENDPOINT -U mlflow_admin -d mlflow
```

### High Costs

Najväčšie náklady:
1. **NAT Gateway**: ~$35/месяц per AZ
   - Solution: Použi VPC Endpoints pre S3 (už v konfigurácii)
2. **RDS Multi-AZ**: 2x cena
   - Solution: Single AZ pre dev/test
3. **Fargate**: Závisí od CPU/Memory
   - Solution: Right-size resources

## Security

### Network Security
- ✅ Private subnets pre ECS a RDS
- ✅ Security groups s least privilege
- ✅ No public IP na ECS tasks
- ✅ RDS accessible len z ECS tasks

### Data Security
- ✅ RDS encryption at rest
- ✅ S3 encryption (AES256)
- ✅ Secrets Manager pre credentials
- ✅ VPC endpoints pre S3

### Best Practices
- ✅ Use strong DB password
- ✅ Enable HTTPS v produkcii
- ✅ Regularly update MLflow image
- ✅ Monitor CloudWatch alarms

## Cleanup

```bash
# POZOR: Vymaže všetku infraštruktúru!
terraform destroy

# Ak máš deletion_protection = true, najprv:
# 1. Nastav deletion_protection = false v RDS
# 2. Nastav enable_deletion_protection = false v ALB
terraform apply
terraform destroy
```

## Cost Estimate

| Component | Configuration | Monthly Cost (USD) |
|-----------|--------------|-------------------|
| ECS Fargate | 1 task (0.5 vCPU, 1GB) | ~$15 |
| RDS PostgreSQL | db.t3.micro | ~$15 |
| NAT Gateway | 2 AZs | ~$70 |
| ALB | Standard | ~$20 |
| S3 | <100GB | ~$5 |
| **Total** | | **~$125/month** |

**Cost reduction tips:**
- Single AZ (dev): -$35 (1 NAT GW)
- Remove NAT (use VPC endpoints only): -$70
- Spot instances (not supported na Fargate)

## Support

Issues: https://github.com/romanceresnak/house-price-mlops/issues

## License

MIT
