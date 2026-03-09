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

### 🚧 KROK 2: MLflow Tracking Server na AWS
- [ ] Terraform: ECS Fargate cluster
- [ ] RDS PostgreSQL backend store
- [ ] S3 artifact store
- [ ] Application Load Balancer
- [ ] VPC + Security groups

### 🚧 KROK 3: Lokálny Experiment v SageMaker Studio
- [ ] EDA notebook
- [ ] Feature engineering experimenty
- [ ] MLflow tracking z notebooku
- [ ] Model prototyping

### 🚧 KROK 4: SageMaker Training Job
- [ ] Custom Docker image (Dockerfile)
- [ ] ECR push pipeline
- [ ] SageMaker Training Job script
- [ ] MLflow remote tracking z jobu

### 🚧 KROK 5: SageMaker Endpoint Deployment
- [ ] MLflow Model Registry integration
- [ ] SageMaker endpoint deployment
- [ ] Staging/Production environments
- [ ] Smoke testy

### 🚧 KROK 6: CI/CD GitHub Actions
- [ ] PR checks (lint, test)
- [ ] Auto-train na push do main
- [ ] Auto-deploy do staging
- [ ] Manual approval pre production

## Quick Start

### Predpoklady

```bash
# AWS CLI
aws --version

# Python 3.11+
python --version

# Terraform (pre Krok 2)
terraform --version
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
