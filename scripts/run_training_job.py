#!/usr/bin/env python
"""
SageMaker Training Job Launcher

Tento skript spustí SageMaker Training Job pre house price model.
Použitie:
    python scripts/run_training_job.py --s3-data s3://bucket/data/ --job-name my-training-job

Features:
  - Nahrá Docker image do ECR
  - Spustí SageMaker Training Job
  - Monitoruje job progress
  - Loguje do MLflow (ak je MLFLOW_TRACKING_URI nastavený)
"""
import argparse
import os
import sys
import time
import logging
from datetime import datetime

import boto3
import sagemaker
from sagemaker.estimator import Estimator

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Spusti SageMaker Training Job pre house prices"
    )

    # --- Required ---
    parser.add_argument(
        "--s3-data",
        type=str,
        required=True,
        help="S3 URI k tréningovým dátam (napr. s3://bucket/data/train.csv)",
    )

    # --- Optional ---
    parser.add_argument(
        "--job-name",
        type=str,
        default=None,
        help="Názov training jobu (default: house-price-{timestamp})",
    )
    parser.add_argument(
        "--instance-type",
        type=str,
        default="ml.m5.xlarge",
        help="SageMaker instance type (default: ml.m5.xlarge)",
    )
    parser.add_argument(
        "--instance-count",
        type=int,
        default=1,
        help="Počet SageMaker instancií (default: 1)",
    )
    parser.add_argument(
        "--ecr-image",
        type=str,
        default=None,
        help="ECR image URI (ak nie je zadaný, použije sa default SageMaker XGBoost container)",
    )
    parser.add_argument(
        "--role",
        type=str,
        default=None,
        help="SageMaker execution role ARN (default: načíta z SageMaker session)",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default=None,
        help="S3 output path pre model (default: s3://sagemaker-{region}-{account}/jobs/)",
    )
    parser.add_argument(
        "--mlflow-tracking-uri",
        type=str,
        default=os.environ.get("MLFLOW_TRACKING_URI", ""),
        help="MLflow tracking URI (default: $MLFLOW_TRACKING_URI)",
    )
    parser.add_argument(
        "--mlflow-experiment-name",
        type=str,
        default="house-prices-sagemaker",
        help="MLflow experiment name (default: house-prices-sagemaker)",
    )

    # --- Hyperparameters ---
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--subsample", type=float, default=0.8)
    parser.add_argument("--colsample-bytree", type=float, default=0.8)

    return parser.parse_args()


def get_default_image_uri(region: str) -> str:
    """Vráti default XGBoost container image pre SageMaker."""
    from sagemaker.image_uris import retrieve

    return retrieve(
        framework="xgboost",
        region=region,
        version="1.7-1",  # Najnovšia podporovaná verzia
        image_scope="training",
    )


def create_estimator(args, role: str, region: str, image_uri: str) -> Estimator:
    """
    Vytvorí SageMaker Estimator.

    Args:
        args: CLI argumenty
        role: SageMaker execution role ARN
        region: AWS region
        image_uri: Docker image URI

    Returns:
        sagemaker.estimator.Estimator
    """
    # Output path
    output_path = args.output_path
    if not output_path:
        session = boto3.Session()
        account_id = session.client("sts").get_caller_identity()["Account"]
        output_path = f"s3://sagemaker-{region}-{account_id}/house-price-jobs"

    # Hyperparameters
    hyperparameters = {
        "n-estimators": args.n_estimators,
        "max-depth": args.max_depth,
        "learning-rate": args.learning_rate,
        "subsample": args.subsample,
        "colsample-bytree": args.colsample_bytree,
        "mlflow-tracking-uri": args.mlflow_tracking_uri,
        "mlflow-experiment-name": args.mlflow_experiment_name,
    }

    estimator = Estimator(
        image_uri=image_uri,
        role=role,
        instance_count=args.instance_count,
        instance_type=args.instance_type,
        output_path=output_path,
        hyperparameters=hyperparameters,
        base_job_name="house-price",
        # Metrics pre SageMaker console
        metric_definitions=[
            {"Name": "train:rmse", "Regex": "train_rmse: ([0-9.]+)"},
            {"Name": "validation:rmse", "Regex": "Validation metrics:.*'rmse': ([0-9.]+)"},
            {"Name": "validation:r2", "Regex": "Validation metrics:.*'r2': ([0-9.]+)"},
        ],
        enable_sagemaker_metrics=True,
    )

    return estimator


def run_training_job(args):
    """Hlavná funkcia - spustí SageMaker Training Job."""
    logger.info("=== Spúšťam SageMaker Training Job ===\n")

    # SageMaker session
    session = sagemaker.Session()
    region = session.boto_region_name

    # Role
    role = args.role
    if not role:
        role = sagemaker.get_execution_role()
    logger.info(f"Using role: {role}")

    # Image URI
    image_uri = args.ecr_image
    if not image_uri:
        image_uri = get_default_image_uri(region)
    logger.info(f"Using image: {image_uri}")

    # Job name
    job_name = args.job_name
    if not job_name:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        job_name = f"house-price-{timestamp}"
    logger.info(f"Job name: {job_name}\n")

    # Vytvor estimator
    estimator = create_estimator(args, role, region, image_uri)

    # Spusti training
    logger.info(f"Spúšťam training job s dátami: {args.s3_data}")
    logger.info("Tento proces môže trvať 5-15 minút...\n")

    try:
        estimator.fit(
            inputs={"train": args.s3_data},
            job_name=job_name,
            wait=True,  # Počkaj na dokončenie
            logs="All",  # Zobraz všetky logy
        )

        logger.info("\n✓ Training job dokončený úspešne!")
        logger.info(f"Model output: {estimator.model_data}")
        logger.info(f"Job name: {estimator.latest_training_job.name}")

        return estimator

    except Exception as e:
        logger.error(f"\n✗ Training job zlyhal: {e}")
        sys.exit(1)


def main():
    args = parse_args()

    # Validácia
    if not args.s3_data.startswith("s3://"):
        logger.error("--s3-data musí byť S3 URI (začína s s3://)")
        sys.exit(1)

    # Spusti training
    estimator = run_training_job(args)

    logger.info("\n" + "=" * 60)
    logger.info("Training job info:")
    logger.info(f"  Job name: {estimator.latest_training_job.name}")
    logger.info(f"  Model S3: {estimator.model_data}")
    logger.info(f"  Region: {estimator.sagemaker_session.boto_region_name}")
    logger.info("=" * 60)

    logger.info("\nĎalšie kroky:")
    logger.info("1. Skontroluj MLflow UI pre metriky")
    logger.info("2. Deploy model cez: python scripts/deploy_endpoint.py")


if __name__ == "__main__":
    main()
