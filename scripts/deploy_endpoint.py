#!/usr/bin/env python
"""
SageMaker Endpoint Deployment Script

Tento skript deployuje model z MLflow Model Registry na SageMaker real-time endpoint.

Použitie:
    # Deploy konkrétnu verziu z MLflow Registry
    python scripts/deploy_endpoint.py --model-name house-price-xgboost --version 3

    # Deploy production stage
    python scripts/deploy_endpoint.py --model-name house-price-xgboost --stage Production

    # Deploy z S3 (ak nemáš MLflow)
    python scripts/deploy_endpoint.py --model-s3-uri s3://bucket/model.tar.gz
"""
import argparse
import os
import sys
import logging
from datetime import datetime

import boto3
import sagemaker
from sagemaker.model import Model
from sagemaker.predictor import Predictor
import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Deploy model na SageMaker endpoint"
    )

    # --- Model source (buď MLflow alebo S3) ---
    model_source = parser.add_mutually_exclusive_group(required=True)
    model_source.add_argument(
        "--model-name",
        type=str,
        help="MLflow registered model name",
    )
    model_source.add_argument(
        "--model-s3-uri",
        type=str,
        help="S3 URI k model.tar.gz (ak nepoužívaš MLflow)",
    )

    # --- MLflow options (ak používaš --model-name) ---
    parser.add_argument(
        "--version",
        type=int,
        default=None,
        help="MLflow model version (napr. 3). Ak nie je zadané, použije sa --stage",
    )
    parser.add_argument(
        "--stage",
        type=str,
        default="Production",
        choices=["Staging", "Production", "Archived"],
        help="MLflow model stage (default: Production)",
    )
    parser.add_argument(
        "--mlflow-tracking-uri",
        type=str,
        default=os.environ.get("MLFLOW_TRACKING_URI", ""),
        help="MLflow tracking URI (default: $MLFLOW_TRACKING_URI)",
    )

    # --- SageMaker options ---
    parser.add_argument(
        "--endpoint-name",
        type=str,
        default=None,
        help="Názov endpointu (default: house-price-{stage/version})",
    )
    parser.add_argument(
        "--instance-type",
        type=str,
        default="ml.m5.large",
        help="SageMaker instance type (default: ml.m5.large)",
    )
    parser.add_argument(
        "--instance-count",
        type=int,
        default=1,
        help="Počet SageMaker instancií (default: 1)",
    )
    parser.add_argument(
        "--role",
        type=str,
        default=None,
        help="SageMaker execution role ARN (default: načíta z SageMaker session)",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Ak endpoint už existuje, aktualizuj ho (inak vytvor nový)",
    )

    return parser.parse_args()


def get_model_from_mlflow(args) -> str:
    """
    Stiahne model z MLflow Model Registry a vráti S3 URI.

    Args:
        args: CLI argumenty

    Returns:
        str: S3 URI k model artifacts
    """
    if args.mlflow_tracking_uri:
        mlflow.set_tracking_uri(args.mlflow_tracking_uri)

    client = MlflowClient()
    model_name = args.model_name

    # Získaj model version
    if args.version:
        logger.info(f"Načítavam model {model_name} version {args.version}...")
        model_version = args.version
    else:
        logger.info(f"Načítavam model {model_name} stage={args.stage}...")
        versions = client.get_latest_versions(model_name, stages=[args.stage])
        if not versions:
            logger.error(f"Žiadna verzia v stage '{args.stage}' pre model {model_name}")
            sys.exit(1)
        model_version = versions[0].version

    # Získaj model metadata
    model_version_info = client.get_model_version(model_name, model_version)
    run_id = model_version_info.run_id
    artifact_uri = model_version_info.source

    logger.info(f"  Model version: {model_version}")
    logger.info(f"  Run ID: {run_id}")
    logger.info(f"  Artifact URI: {artifact_uri}")

    # Predpokladáme že artifact_uri je S3 path (ak MLflow používa S3 backend)
    if not artifact_uri.startswith("s3://"):
        logger.error("MLflow artifact URI musí byť S3 path pre SageMaker deployment")
        logger.error("Nastav MLflow s S3 artifact store alebo použi --model-s3-uri")
        sys.exit(1)

    return artifact_uri


def create_sagemaker_model(
    model_data: str,
    role: str,
    image_uri: str,
    model_name: str,
) -> Model:
    """
    Vytvorí SageMaker Model objekt.

    Args:
        model_data: S3 URI k model.tar.gz
        role: SageMaker execution role ARN
        image_uri: Docker image URI pre inference
        model_name: Názov SageMaker modelu

    Returns:
        sagemaker.model.Model
    """
    model = Model(
        model_data=model_data,
        image_uri=image_uri,
        role=role,
        name=model_name,
        # Môžeš pridať environment variables pre inference
        env={
            "MODEL_SERVER_TIMEOUT": "120",
            "MODEL_SERVER_WORKERS": "1",
        },
    )

    return model


def deploy_endpoint(args):
    """Hlavná funkcia - deployuje model na SageMaker endpoint."""
    logger.info("=== Deploying SageMaker Endpoint ===\n")

    # SageMaker session
    session = sagemaker.Session()
    region = session.boto_region_name

    # Role
    role = args.role
    if not role:
        role = sagemaker.get_execution_role()
    logger.info(f"Using role: {role}")

    # Model S3 URI
    if args.model_name:
        model_data = get_model_from_mlflow(args)
    else:
        model_data = args.model_s3_uri
        logger.info(f"Using S3 model: {model_data}")

    # Image URI (použi default XGBoost inference container)
    from sagemaker.image_uris import retrieve
    image_uri = retrieve(
        framework="xgboost",
        region=region,
        version="1.7-1",
        image_scope="inference",
    )
    logger.info(f"Using inference image: {image_uri}\n")

    # Endpoint name
    endpoint_name = args.endpoint_name
    if not endpoint_name:
        if args.model_name:
            stage_or_version = args.stage if args.stage else f"v{args.version}"
            endpoint_name = f"house-price-{stage_or_version.lower()}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            endpoint_name = f"house-price-{timestamp}"

    logger.info(f"Endpoint name: {endpoint_name}")

    # Model name (musí byť unique)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_name = f"house-price-model-{timestamp}"

    # Vytvor model
    logger.info("Vytváram SageMaker Model...")
    model = create_sagemaker_model(model_data, role, image_uri, model_name)

    # Check či endpoint už existuje
    sm_client = boto3.client("sagemaker", region_name=region)
    try:
        sm_client.describe_endpoint(EndpointName=endpoint_name)
        endpoint_exists = True
        logger.info(f"Endpoint '{endpoint_name}' už existuje.")
    except sm_client.exceptions.ClientError:
        endpoint_exists = False

    # Deploy
    try:
        if endpoint_exists and args.update_existing:
            logger.info(f"Aktualizujem existujúci endpoint '{endpoint_name}'...")
            predictor = model.deploy(
                initial_instance_count=args.instance_count,
                instance_type=args.instance_type,
                endpoint_name=endpoint_name,
                update_endpoint=True,
                wait=True,
            )
        elif endpoint_exists and not args.update_existing:
            logger.error(f"Endpoint '{endpoint_name}' už existuje.")
            logger.error("Použi --update-existing pre aktualizáciu alebo zmeň --endpoint-name")
            sys.exit(1)
        else:
            logger.info(f"Vytváram nový endpoint '{endpoint_name}'...")
            logger.info("Tento proces môže trvať 5-10 minút...\n")
            predictor = model.deploy(
                initial_instance_count=args.instance_count,
                instance_type=args.instance_type,
                endpoint_name=endpoint_name,
                wait=True,
            )

        logger.info("\n✓ Endpoint úspešne deploynutý!")
        logger.info(f"Endpoint name: {endpoint_name}")
        logger.info(f"Region: {region}")

        return predictor

    except Exception as e:
        logger.error(f"\n✗ Deployment zlyhal: {e}")
        sys.exit(1)


def test_endpoint(endpoint_name: str, region: str):
    """Otestuj endpoint s ukážkovými dátami."""
    logger.info("\n=== Testujem endpoint ===")

    predictor = Predictor(
        endpoint_name=endpoint_name,
        sagemaker_session=sagemaker.Session(boto3.Session(region_name=region)),
    )

    # Test data
    test_payload = {
        "LotArea": 8450,
        "OverallQual": 7,
        "OverallCond": 5,
        "YearBuilt": 2003,
        "YearRemodAdd": 2003,
        "TotalBsmtSF": 856,
        "1stFlrSF": 856,
        "2ndFlrSF": 854,
        "GrLivArea": 1710,
        "FullBath": 2,
        "HalfBath": 1,
        "BedroomAbvGr": 3,
        "TotRmsAbvGrd": 8,
        "GarageCars": 2,
        "GarageArea": 548,
        "WoodDeckSF": 0,
        "OpenPorchSF": 61,
    }

    try:
        import json
        response = predictor.predict(
            json.dumps(test_payload),
            initial_args={"ContentType": "application/json"}
        )
        logger.info(f"Test response: {response}")
        logger.info("✓ Endpoint funguje správne!")
    except Exception as e:
        logger.warning(f"Test zlyhal: {e}")
        logger.warning("Skontroluj endpoint manuálne")


def main():
    args = parse_args()

    # Validácia
    if args.model_name and not args.mlflow_tracking_uri:
        logger.error("--mlflow-tracking-uri je required ak používaš --model-name")
        logger.error("Nastav MLFLOW_TRACKING_URI environment variable alebo použi --mlflow-tracking-uri")
        sys.exit(1)

    # Deploy
    predictor = deploy_endpoint(args)

    # Test endpoint
    session = sagemaker.Session()
    test_endpoint(predictor.endpoint_name, session.boto_region_name)

    logger.info("\n" + "=" * 60)
    logger.info("Endpoint info:")
    logger.info(f"  Name: {predictor.endpoint_name}")
    logger.info(f"  Region: {session.boto_region_name}")
    logger.info("=" * 60)

    logger.info("\nPouži endpoint:")
    logger.info("  aws sagemaker-runtime invoke-endpoint \\")
    logger.info(f"    --endpoint-name {predictor.endpoint_name} \\")
    logger.info("    --body '{\"LotArea\": 8450, ...}' \\")
    logger.info("    --content-type application/json \\")
    logger.info("    output.json")


if __name__ == "__main__":
    main()
