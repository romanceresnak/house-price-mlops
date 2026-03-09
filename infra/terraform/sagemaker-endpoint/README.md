# SageMaker Endpoint Infrastructure

Terraform konfigurácia pre AWS SageMaker real-time inference endpoints.

## Resources Created

| Resource | Popis | Počet |
|----------|-------|-------|
| SageMaker Model | ML model pre inference | 1 |
| Endpoint Config | Configuration pre endpoint | 1 |
| SageMaker Endpoint | Real-time inference endpoint | 1 |
| Auto-scaling Policy | Automatic instance scaling | 0-1 |
| CloudWatch Alarms | Monitoring a alerting | 6 |
| SNS Topic | Email notifications | 0-1 |
| S3 Bucket | Data capture (optional) | 0-1 |
| CloudWatch Dashboard | Metrics visualization | 0-1 |

## Features

- ✅ **Real-time Inference**: HTTPS endpoint pre model predictions
- ✅ **Auto-scaling**: Automatic scaling based on traffic
- ✅ **Monitoring**: CloudWatch metrics a alarms
- ✅ **Data Capture**: Request/response logging pre model monitoring
- ✅ **High Availability**: Multi-instance deployment support
- ✅ **Cost Optimization**: Spot instances support, scheduled scaling
- ✅ **Security**: IAM-based access control, encryption at rest

## Prerequisites

Pred deployment musíš mať:

1. ✅ **Deployed SageMaker infrastructure** (z `../sagemaker/`)
   ```bash
   cd ../sagemaker
   terraform output sagemaker_execution_role_arn
   terraform output ecr_repository_url
   ```

2. ✅ **Trained model** uložený v S3
   - Model artifacts (model.tar.gz) z training jobu
   - S3 URL v formate: `s3://bucket/path/to/model.tar.gz`

3. ✅ **Docker image** v ECR
   - Image s inference kódom (src/serve/inference.py)
   - Pushnutý do ECR repository

## Quick Start

### 1. Konfigurácia

```bash
cd infra/terraform/sagemaker-endpoint

# Kopíruj example config
cp terraform.tfvars.example terraform.tfvars

# Uprav terraform.tfvars
vim terraform.tfvars
```

**Mandatory variables:**
```hcl
# Z predchádzajúceho terraform output
sagemaker_execution_role_arn = "arn:aws:iam::123456789:role/..."
ecr_image_uri                = "123456789.dkr.ecr.eu-west-1.amazonaws.com/house-price-mlops:latest"

# Z training job output
model_data_url = "s3://your-bucket/training-jobs/job-name/output/model.tar.gz"
```

### 2. Deploy Endpoint

```bash
# Initialize
terraform init

# Plan
terraform plan

# Deploy
terraform apply
```

Deploy trvá **~5-7 minút** (SageMaker endpoint initialization).

### 3. Get Endpoint Info

```bash
# Všetky outputs
terraform output

# Endpoint name
terraform output endpoint_name

# Endpoint URL
terraform output endpoint_url
```

## Usage

### Test Endpoint (AWS CLI)

```bash
# Get endpoint name
ENDPOINT_NAME=$(terraform output -raw endpoint_name)
REGION=$(terraform output -raw aws_region)

# Prepare test data (JSON)
cat > test_input.json <<EOF
{
  "data": [
    [1710, 2003, 8, 5, 1, 856, 854, 0, 0, 3, 1710, 1, 1, 2, 1, 7, 2003, 2003, 548]
  ]
}
EOF

# Invoke endpoint
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name $ENDPOINT_NAME \
  --body file://test_input.json \
  --content-type application/json \
  --region $REGION \
  output.json

# Check response
cat output.json
```

### Test Endpoint (Python - boto3)

```python
import boto3
import json
import numpy as np

# Create SageMaker runtime client
runtime = boto3.client('sagemaker-runtime', region_name='eu-west-1')

# Prepare test data
test_data = {
    "data": [
        [1710, 2003, 8, 5, 1, 856, 854, 0, 0, 3, 1710, 1, 1, 2, 1, 7, 2003, 2003, 548]
    ]
}

# Invoke endpoint
response = runtime.invoke_endpoint(
    EndpointName='house-price-mlops-prod-endpoint',
    ContentType='application/json',
    Body=json.dumps(test_data)
)

# Parse response
result = json.loads(response['Body'].read().decode())
print(f"Prediction: ${np.exp(result['predictions'][0]):.2f}")
```

### Monitor Endpoint

```bash
# Check endpoint status
aws sagemaker describe-endpoint \
  --endpoint-name $ENDPOINT_NAME \
  --region $REGION

# View metrics (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/SageMaker \
  --metric-name Invocations \
  --dimensions Name=EndpointName,Value=$ENDPOINT_NAME Name=VariantName,Value=AllTraffic \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region $REGION
```

## Instance Types & Pricing

| Instance Type | vCPUs | Memory | Price/hour | Use Case |
|--------------|-------|--------|------------|----------|
| ml.t2.medium | 2 | 4 GB | $0.065 | Low traffic, dev/staging |
| ml.t2.large | 2 | 8 GB | $0.13 | Low-medium traffic |
| ml.m5.large | 2 | 8 GB | $0.134 | Production, low latency |
| ml.m5.xlarge | 4 | 16 GB | $0.269 | High traffic |
| ml.c5.xlarge | 4 | 8 GB | $0.238 | CPU-intensive inference |

**Cost Example (ml.t2.medium, 1 instance):**
- Hourly: $0.065
- Daily: ~$1.56
- Monthly: ~$47

**Cost Optimization:**
- Use auto-scaling (scale to 0 instances when idle - not supported for SageMaker)
- Use scheduled scaling (1 instance at night, 3 during day)
- Use smaller instance types for low-traffic endpoints

## Auto-scaling Configuration

### Enable Auto-scaling

V `terraform.tfvars`:
```hcl
enable_autoscaling              = true
min_instance_count              = 1
max_instance_count              = 3
target_invocations_per_instance = 1000
```

### How it Works

1. **Target Tracking**: Scales based on `InvocationsPerInstance` metric
2. **Scale Out**: When > 1000 invocations/instance (1 min cooldown)
3. **Scale In**: When < 1000 invocations/instance (5 min cooldown)

### Example Scenario

- **Low traffic** (< 1000 req/min): 1 instance
- **Medium traffic** (1000-2000 req/min): 2 instances
- **High traffic** (2000-3000 req/min): 3 instances

## Monitoring & Alarms

### CloudWatch Alarms

Auto-vytvorené alarmy:

| Alarm | Threshold | Akcia |
|-------|-----------|-------|
| 4XX Errors | > 10 errors/5min | SNS notification |
| 5XX Errors | > 5 errors/5min | SNS notification |
| High Latency | > 5000ms avg | SNS notification |
| High CPU | > 80% avg | SNS notification |
| High Memory | > 85% avg | SNS notification |

### CloudWatch Dashboard

Po deploy môžeš zobraziť dashboard:
```bash
terraform output cloudwatch_dashboard_url
```

Dashboard obsahuje:
- **Invocations & Errors** - počet requestov a error rates
- **Model Latency** - avg/p50/p99 latency
- **Resource Utilization** - CPU a memory usage

### Email Notifications

Nastav v `terraform.tfvars`:
```hcl
alarm_email = "your-email@example.com"
```

Po apply **potvrď subscription** v emaile od AWS SNS.

## Data Capture (Model Monitoring)

### Enable Data Capture

V `terraform.tfvars`:
```hcl
enable_data_capture              = true
data_capture_sampling_percentage = 100  # Capture 100% requestov
```

### Captured Data Structure

```
s3://house-price-mlops-prod-endpoint-data-capture/
└── data-capture/
    ├── AllTraffic/
    │   ├── 2024/03/09/10/
    │   │   ├── request-00001.jsonl
    │   │   ├── response-00001.jsonl
    │   │   └── ...
```

### Use Cases

- **Model Drift Detection**: Compare input distributions over time
- **Performance Monitoring**: Analyze prediction quality
- **Debugging**: Investigate failed requests
- **Retraining**: Collect real-world data for model updates

Data sa automaticky **vymazáva po 30 dňoch** (lifecycle policy).

## Troubleshooting

### Endpoint Failed to Deploy

```bash
# Check endpoint status
aws sagemaker describe-endpoint --endpoint-name $ENDPOINT_NAME

# Check CloudWatch logs
aws logs tail /aws/sagemaker/Endpoints/$ENDPOINT_NAME --follow
```

**Common issues:**
- ❌ Invalid model_data_url (S3 path doesn't exist)
- ❌ Missing IAM permissions (role can't access S3/ECR)
- ❌ Docker image not found in ECR
- ❌ Inference code error (check logs)

### High Latency

```bash
# Check instance metrics
aws cloudwatch get-metric-statistics \
  --namespace /aws/sagemaker/Endpoints \
  --metric-name CPUUtilization \
  --dimensions Name=EndpointName,Value=$ENDPOINT_NAME \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Solutions:**
- ✅ Enable auto-scaling
- ✅ Use larger instance type (ml.m5.xlarge)
- ✅ Optimize inference code
- ✅ Use batch predictions (Batch Transform)

### 4XX/5XX Errors

```bash
# Get error details from logs
aws logs tail /aws/sagemaker/Endpoints/$ENDPOINT_NAME --follow
```

**Common causes:**
- ❌ Invalid input format (check Content-Type)
- ❌ Missing features in input data
- ❌ Model inference error (check inference.py)

### Endpoint Not Scaling

```bash
# Check auto-scaling policy
aws application-autoscaling describe-scaling-policies \
  --service-namespace sagemaker \
  --resource-id endpoint/$ENDPOINT_NAME/variant/AllTraffic
```

**Verify:**
- ✅ Auto-scaling enabled in terraform.tfvars
- ✅ InvocationsPerInstance metric has data
- ✅ Cooldown period hasn't passed yet

## Updating Endpoint

### Deploy New Model Version

```bash
# 1. Train new model (get new model_data_url)
# 2. Update terraform.tfvars
model_data_url = "s3://bucket/new-model/model.tar.gz"

# 3. Apply changes
terraform apply

# SageMaker updates endpoint with zero downtime (rolling update)
```

### Change Instance Type

```bash
# Update terraform.tfvars
instance_type = "ml.m5.large"

# Apply (causes brief downtime)
terraform apply
```

### Update Docker Image

```bash
# 1. Build a push new image
./scripts/build_and_push.sh eu-west-1

# 2. Update terraform.tfvars
ecr_image_uri = "123456789.dkr.ecr.eu-west-1.amazonaws.com/house-price-mlops:new-tag"

# 3. Apply
terraform apply
```

## Cleanup

```bash
# POZOR: Vymaže endpoint a všetky resources!
terraform destroy

# Estimated savings: ~$47/month (1x ml.t2.medium)
```

**Note:** Model artifacts v S3 ostanú zachované (môžeš ich použiť neskôr).

## Integration s MLflow

### Deploy Model z MLflow Registry

```python
import mlflow
from mlflow.tracking import MlflowClient

# Connect to MLflow
mlflow.set_tracking_uri("http://your-mlflow-server.com")
client = MlflowClient()

# Get model from registry
model_name = "house-price-xgboost"
model_version = client.get_latest_versions(model_name, stages=["Production"])[0]

# Get model S3 path
model_uri = model_version.source
# Example: s3://mlflow-bucket/artifacts/123/abc/artifacts/model

# Download model artifacts a re-upload ako model.tar.gz
# ... (alebo použi MLflow SageMaker deployment plugin)
```

## Next Steps

Po úspešnom endpoint deployment:

1. **Load Testing** - Test endpoint under load (JMeter, Locust)
2. **A/B Testing** - Deploy multiple variants, split traffic
3. **Canary Deployment** - Gradual rollout of new models
4. **Multi-model Endpoints** - Host multiple models on 1 endpoint
5. **Batch Transform** - Batch predictions pre large datasets

See notebooks/05_endpoint_deployment.ipynb for examples!

## Cost Estimate

**Minimal Setup (dev/staging):**
- 1x ml.t2.medium instance: ~$47/month
- Data capture S3 (10 GB): ~$0.23/month
- CloudWatch alarms: ~$0.10/month
- **Total: ~$47/month**

**Production Setup:**
- 3x ml.m5.large instances (peak): ~$289/month
- Auto-scaling (avg 1.5 instances): ~$145/month
- Data capture S3 (100 GB): ~$2.30/month
- CloudWatch alarms + dashboard: ~$1/month
- SNS notifications: ~$0.01/month
- **Total: ~$148/month** (with auto-scaling)

## License

MIT
