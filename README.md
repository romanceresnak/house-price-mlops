# House Price MLOps

Production-ready MLOps pipeline pre predikciu cien domov (Kaggle House Prices dataset) s AWS SageMaker, MLflow a CI/CD.

## Architektúra

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   GitHub    │─────▶│  SageMaker   │─────▶│   MLflow    │
│  Actions    │      │  Training    │      │  Tracking   │
└─────────────┘      └──────────────┘      └─────────────┘
       │                     │                     │
       │                     ▼                     │
       │              ┌──────────────┐             │
       └─────────────▶│  SageMaker   │◀────────────┘
                      │  Endpoint    │
                      └──────────────┘
```

## Tech Stack

- **Training**: AWS SageMaker Training Jobs + XGBoost
- **Tracking**: MLflow (ECS Fargate + RDS + S3)
- **Serving**: SageMaker Real-time Endpoints
- **Infrastructure**: Terraform
- **CI/CD**: GitHub Actions
- **Monitoring**: CloudWatch + MLflow

## Projekt Štruktúra

```
house-price-mlops/
├── .github/workflows/
│   ├── ci.yml          # PR checks: lint + tests
│   └── cd.yml          # CD: train → staging → production
├── src/
│   ├── data/
│   │   └── preprocess.py        # Feature engineering pipeline
│   ├── train/
│   │   └── train.py             # SageMaker training script
│   └── serve/
│       └── inference.py         # SageMaker inference handler
├── scripts/
│   ├── run_training_job.py      # CLI pre SageMaker Training Job
│   └── deploy_endpoint.py       # CLI pre endpoint deployment
├── tests/
│   └── test_preprocess.py       # Unit testy (10 testov)
├── infra/terraform/
│   ├── mlflow-server/           # MLflow infraštruktúra
│   └── sagemaker/               # SageMaker IAM + S3 + ECR
├── notebooks/
│   └── 01_eda.ipynb             # EDA notebook
├── Dockerfile                    # Custom SageMaker container
└── requirements.txt
```

## Roadmapa - 6 Krokov

### ✅ KROK 1: Repo + Projekt Štruktúra
- [x] GitHub repository
- [x] Adresárová štruktúra
- [x] Python package (src/data, src/train, src/serve)
- [x] Unit testy (pytest)
- [x] CI/CD workflows (.github/workflows/)
- [x] Requirements.txt

### ✅ KROK 2: MLflow Tracking Server na AWS
- [x] Terraform: ECS Fargate cluster
- [x] RDS PostgreSQL backend store
- [x] S3 artifact store
- [x] Application Load Balancer
- [x] VPC + Security groups
- [x] Auto-scaling + CloudWatch monitoring

### ✅ KROK 3: Lokálne Experimenty v Notebookoch
- [x] EDA notebook (01_eda.ipynb)
- [x] Feature engineering experiments (02_feature_engineering.ipynb)
- [x] MLflow tracking z notebooku (03_model_training.ipynb)
- [x] Model prototyping a comparison
- [x] Kaggle data download script

### ✅ KROK 4: SageMaker Training Job
- [x] Custom Docker image (multi-stage Dockerfile)
- [x] ECR repository a lifecycle policies
- [x] Build and push script (build_and_push.sh)
- [x] SageMaker Training Job script (run_training_job.py)
- [x] MLflow remote tracking z jobu
- [x] Terraform infrastructure (IAM, S3, ECR)
- [x] Example training notebook (04_sagemaker_training.ipynb)

### ✅ KROK 5: SageMaker Endpoint Deployment
- [x] MLflow Model Registry integration
- [x] SageMaker endpoint deployment (deploy_endpoint.py)
- [x] Staging/Production environments
- [x] Auto-scaling a CloudWatch alarms
- [x] Data capture pre model monitoring
- [x] Terraform infrastructure (endpoints, monitoring)
- [x] Example deployment notebook (05_endpoint_deployment.ipynb)

### ✅ KROK 6: CI/CD GitHub Actions
- [x] PR checks (lint, test, security, dependencies)
- [x] Auto-train na push do main
- [x] Auto-deploy do staging
- [x] Manual approval pre production
- [x] Scheduled retraining (weekly)
- [x] Manual model deployment workflow
- [x] Complete CI/CD documentation

## CI/CD Workflows

### 🔍 CI - Continuous Integration

**Trigger:** Pull requests a push do `main`/`develop`

**Jobs:**
- Code quality (Black, Flake8, isort)
- Unit tests (Python 3.10, 3.11) s coverage
- Security scan (Bandit)
- Dependency vulnerabilities (pip-audit)

### 🚀 CD - Continuous Deployment

**Trigger:** Push do `main`

**Flow:**
```
Build Docker → Train Model → Register to MLflow → Deploy Staging → [Approval] → Deploy Production
```

**Environments:**
- **Staging**: Automatic deployment
- **Production**: Requires manual approval

### 🔄 Scheduled Retraining

**Trigger:** Weekly (Monday 2 AM UTC)

**Flow:**
1. Check data freshness
2. Run training job
3. Evaluate metrics (RMSE < 0.15, R² > 0.80)
4. If pass → Register to Staging
5. If fail → Manual review needed

### 🎯 Manual Model Deployment

**Trigger:** Manual dispatch

**Use Cases:**
- Deploy specific model version
- Rollback to previous version
- Test before production

**See:** [.github/workflows/README.md](.github/workflows/README.md) for detailed documentation

---

## Quick Start

### Predpoklady

```bash
# AWS CLI
aws --version

# Python 3.11+
python --version

# Terraform
terraform --version

# Docker
docker --version
```

### 1. Inštalácia

```bash
git clone https://github.com/romanceresnak/house-price-mlops.git
cd house-price-mlops
pip install -r requirements.txt
```

### 2. Spustenie Testov

```bash
# Všetky testy
pytest tests/ -v

# S coverage reportom
pytest tests/ -v --cov=src --cov-report=html
```

### 3. Lokálne Trénovanie (bez SageMaker)

```bash
# Potrebuješ train.csv z Kaggle House Prices dataset
mkdir -p data
# Vlož train.csv do data/

python src/train/train.py \
  --train ./data \
  --output-data-dir ./outputs \
  --model-dir ./models
```

### 4. SageMaker Training Job (po Kroku 4)

```bash
# Nahraj dáta do S3
aws s3 cp data/train.csv s3://your-bucket/data/train.csv

# Spusti training job
python scripts/run_training_job.py \
  --s3-data s3://your-bucket/data/train.csv \
  --mlflow-tracking-uri http://your-mlflow-server:5000
```

### 5. Deploy Endpoint (po Kroku 5)

```bash
python scripts/deploy_endpoint.py \
  --model-name house-price-xgboost \
  --stage Production \
  --mlflow-tracking-uri http://your-mlflow-server:5000
```

### 6. Inference

```bash
aws sagemaker-runtime invoke-endpoint \
  --endpoint-name house-price-production \
  --body '{"LotArea": 8450, "OverallQual": 7, ...}' \
  --content-type application/json \
  output.json

cat output.json
```

## Development

### Code Quality

```bash
# Format code
black src/ tests/ scripts/

# Lint
flake8 src/ tests/ scripts/

# Sort imports
isort src/ tests/ scripts/
```

### Pre-commit Hooks (optional)

```bash
pip install pre-commit
pre-commit install
```

## MLflow UI

Po Kroku 2, MLflow UI bude dostupný na:
```
https://mlflow.your-domain.com
```

## Metriky

Model trackuje tieto metriky:
- **RMSE** (Root Mean Squared Error)
- **MAE** (Mean Absolute Error)
- **R²** (R-squared)
- **RMSLE** (Root Mean Squared Log Error) - Kaggle metrika

## CI/CD Pipeline

### Pull Request
1. Lint checks (Black, Flake8, isort)
2. Unit tests (pytest)
3. Security scan (Bandit)
4. Code coverage report

### Push to Main
1. Build Docker image → ECR
2. SageMaker Training Job
3. Register model → MLflow
4. Deploy → Staging endpoint
5. Smoke tests
6. **Manual approval** → Production

## Estimated Costs

| Service | Monthly Cost |
|---------|-------------|
| MLflow (ECS Fargate + RDS) | ~$50 |
| SageMaker Training (10 jobs/month) | ~$20 |
| SageMaker Endpoint (ml.m5.large) | ~$100 |
| S3 + ECR | ~$5 |
| **Total** | **~$175/month** |

## Environment Variables

Potrebné pre CI/CD:

```bash
# GitHub Secrets
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
S3_DATA_BUCKET
MLFLOW_TRACKING_URI
SAGEMAKER_ROLE_ARN
```

## Dataset

Používame [Kaggle House Prices](https://www.kaggle.com/c/house-prices-advanced-regression-techniques) dataset.

Features:
- **Numeric**: LotArea, OverallQual, YearBuilt, GrLivArea, ...
- **Engineered**: TotalSF, HouseAge, WasRemodeled, TotalBaths

Target: `SalePrice` (log-transformed)

## Contributing

1. Vytvor feature branch: `git checkout -b feature/my-feature`
2. Commit zmeny: `git commit -m 'Add feature'`
3. Push: `git push origin feature/my-feature`
4. Otvor Pull Request

## Ďalšie Kroky

- [ ] Add monitoring dashboards (CloudWatch)
- [ ] Implement A/B testing
- [ ] Add model explainability (SHAP)
- [ ] Implement data drift detection
- [ ] Add batch inference pipeline

## License

MIT

## Autor

Roman Ceresnak
