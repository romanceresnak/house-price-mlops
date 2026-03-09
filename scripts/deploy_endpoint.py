#!/usr/bin/env python
"""
SageMaker Endpoint Deployment Script

Tento skript deployuje model z MLflow Model Registry alebo S3 na SageMaker real-time endpoint.

Použitie:
    # Deploy konkrétnu verziu z MLflow Registry
    python scripts/deploy_endpoint.py --model-name house-price-xgboost --version 3

    # Deploy production stage
    python scripts/deploy_endpoint.py --model-name house-price-xgboost --stage Production

    # Deploy z S3 (ak nemáš MLflow)
    python scripts/deploy_endpoint.py --model-s3-uri s3://bucket/model.tar.gz --ecr-image-uri 123.dkr.ecr.eu-west-1.amazonaws.com/house-price:latest

    # Deploy s Terraform integration (automaticky načíta ECR image a role)
    python scripts/deploy_endpoint.py --model-s3-uri s3://bucket/model.tar.gz --use-terraform
"""
import argparse
import os
import sys
import logging
import subprocess
from datetime import datetime
from pathlib import Path

import boto3
import sagemaker
from sagemaker.model import Model
from sagemaker.predictor import Predictor
import mlflow
from mlflow.tracking import MlflowClient

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def get_terraform_output(key: str, tf_dir: str) -> str:
    """
    Získa hodnotu z Terraform output.

    Args:
        key: Terraform output key
        tf_dir: Path k Terraform directory

    Returns:
        str: Output value
    """
    try:
        result = subprocess.run(
            ["terraform", "output", "-raw", key],
            cwd=tf_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get Terraform output '{key}': {e.stderr}")
        raise


def load_terraform_config(base_dir: str = None) -> dict:
    """
    Načíta konfiguráciu z Terraform outputs.

    Args:
        base_dir: Base directory projektu (default: detekuje automaticky)

    Returns:
        dict: Configuration values
    """
    if base_dir is None:
        # Detekuj base_dir (scripts/ -> root)
        base_dir = Path(__file__).parent.parent.absolute()

    sagemaker_tf_dir = Path(base_dir) / "infra" / "terraform" / "sagemaker"

    if not sagemaker_tf_dir.exists():
        raise FileNotFoundError(f"Terraform directory not found: {sagemaker_tf_dir}")

    logger.info(f"Loading Terraform config from: {sagemaker_tf_dir}")

    config = {
        "execution_role_arn": get_terraform_output("sagemaker_execution_role_arn", str(sagemaker_tf_dir)),
        "ecr_repository_url": get_terraform_output("ecr_repository_url", str(sagemaker_tf_dir)),
        "aws_region": get_terraform_output("aws_region", str(sagemaker_tf_dir)),
    }

    logger.info(f"  Execution Role: {config['execution_role_arn']}")
    logger.info(f"  ECR Repository: {config['ecr_repository_url']}")
    logger.info(f"  AWS Region: {config['aws_region']}")

    return config


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
        default="ml.t2.medium",
        help="SageMaker instance type (default: ml.t2.medium)",
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
        help="SageMaker execution role ARN (default: z Terraform alebo SageMaker session)",
    )
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Ak endpoint už existuje, aktualizuj ho (inak vytvor nový)",
    )

    # --- Docker image ---
    parser.add_argument(
        "--ecr-image-uri",
        type=str,
        default=None,
        help="ECR image URI pre custom inference (default: z Terraform alebo AWS managed XGBoost)",
    )
    parser.add_argument(
        "--ecr-image-tag",
        type=str,
        default="latest",
        help="ECR image tag (default: latest)",
    )

    # --- Terraform integration ---
    parser.add_argument(
        "--use-terraform",
        action="store_true",
        help="Načítaj konfiguráciu (role, ECR image) z Terraform outputs",
    )
    parser.add_argument(
        "--terraform-dir",
        type=str,
        default=None,
        help="Path k Terraform directory (default: auto-detect)",
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
    use_custom_container: bool = True,
) -> Model:
    """
    Vytvorí SageMaker Model objekt.

    Args:
        model_data: S3 URI k model.tar.gz
        role: SageMaker execution role ARN
        image_uri: Docker image URI pre inference
        model_name: Názov SageMaker modelu
        use_custom_container: Či používame custom container (vs AWS managed)

    Returns:
        sagemaker.model.Model
    """
    # Environment variables pre inference
    env_vars = {
        "MODEL_SERVER_TIMEOUT": "120",
        "MODEL_SERVER_WORKERS": "1",
    }

    # Ak používame custom container, nastav SageMaker-specific env vars
    if use_custom_container:
        env_vars.update({
            "SAGEMAKER_PROGRAM": "src/serve/inference.py",
            "SAGEMAKER_SUBMIT_DIRECTORY": "/opt/ml/code",
        })

    model = Model(
        model_data=model_data,
        image_uri=image_uri,
        role=role,
        name=model_name,
        env=env_vars,
    )

    return model


def deploy_endpoint(args):
    """Hlavná funkcia - deployuje model na SageMaker endpoint."""
    logger.info("=" * 80)
    logger.info("SageMaker Endpoint Deployment")
    logger.info("=" * 80)

    # Load Terraform config ak required
    tf_config = None
    if args.use_terraform:
        logger.info("\nLoading Terraform configuration...")
        tf_config = load_terraform_config(args.terraform_dir)

    # SageMaker session
    session = sagemaker.Session()
    region = session.boto_region_name
    logger.info(f"\nAWS Region: {region}")

    # Role
    role = args.role
    if not role and tf_config:
        role = tf_config["execution_role_arn"]
        logger.info(f"Using role from Terraform: {role}")
    elif not role:
        role = sagemaker.get_execution_role()
        logger.info(f"Using default role: {role}")
    else:
        logger.info(f"Using provided role: {role}")

    # Model S3 URI
    if args.model_name:
        model_data = get_model_from_mlflow(args)
    else:
        model_data = args.model_s3_uri
        logger.info(f"Model S3 URI: {model_data}")

    # Image URI
    image_uri = args.ecr_image_uri
    use_custom_container = True

    if not image_uri and tf_config:
        # Use Terraform ECR repository
        ecr_repo = tf_config["ecr_repository_url"]
        image_uri = f"{ecr_repo}:{args.ecr_image_tag}"
        logger.info(f"Using custom ECR image from Terraform: {image_uri}")
    elif not image_uri:
        # Use AWS managed XGBoost container
        from sagemaker.image_uris import retrieve
        image_uri = retrieve(
            framework="xgboost",
            region=region,
            version="1.7-1",
            image_scope="inference",
        )
        use_custom_container = False
        logger.info(f"Using AWS managed XGBoost image: {image_uri}")
    else:
        logger.info(f"Using provided ECR image: {image_uri}")

    # Endpoint name
    endpoint_name = args.endpoint_name
    if not endpoint_name:
        if args.model_name:
            stage_or_version = args.stage if args.stage else f"v{args.version}"
            endpoint_name = f"house-price-{stage_or_version.lower()}"
        else:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            endpoint_name = f"house-price-{timestamp}"

    logger.info(f"\nEndpoint Configuration:")
    logger.info(f"  Name: {endpoint_name}")
    logger.info(f"  Instance Type: {args.instance_type}")
    logger.info(f"  Instance Count: {args.instance_count}")

    # Model name (musí byť unique)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    model_name = f"house-price-model-{timestamp}"

    # Vytvor model
    logger.info("\n" + "=" * 80)
    logger.info("Creating SageMaker Model...")
    logger.info("=" * 80)
    model = create_sagemaker_model(
        model_data=model_data,
        role=role,
        image_uri=image_uri,
        model_name=model_name,
        use_custom_container=use_custom_container
    )
    logger.info(f"✓ Model created: {model_name}")

    # Check či endpoint už existuje
    logger.info("\nChecking if endpoint exists...")
    sm_client = boto3.client("sagemaker", region_name=region)
    try:
        endpoint_info = sm_client.describe_endpoint(EndpointName=endpoint_name)
        endpoint_exists = True
        endpoint_status = endpoint_info["EndpointStatus"]
        logger.info(f"  Endpoint '{endpoint_name}' exists (status: {endpoint_status})")
    except sm_client.exceptions.ClientError:
        endpoint_exists = False
        logger.info(f"  Endpoint '{endpoint_name}' does not exist")

    # Deploy
    try:
        logger.info("\n" + "=" * 80)
        if endpoint_exists and args.update_existing:
            logger.info(f"Updating Existing Endpoint: {endpoint_name}")
            logger.info("=" * 80)
            logger.info("This will perform a rolling update with zero downtime...")
            logger.info("Expected time: 5-10 minutes")
            predictor = model.deploy(
                initial_instance_count=args.instance_count,
                instance_type=args.instance_type,
                endpoint_name=endpoint_name,
                update_endpoint=True,
                wait=True,
            )
        elif endpoint_exists and not args.update_existing:
            logger.error("=" * 80)
            logger.error(f"ERROR: Endpoint '{endpoint_name}' already exists")
            logger.error("=" * 80)
            logger.error("Options:")
            logger.error("  1. Use --update-existing to update the endpoint")
            logger.error("  2. Use --endpoint-name to create a new endpoint")
            logger.error("  3. Delete existing endpoint first:")
            logger.error(f"     aws sagemaker delete-endpoint --endpoint-name {endpoint_name}")
            sys.exit(1)
        else:
            logger.info(f"Creating New Endpoint: {endpoint_name}")
            logger.info("=" * 80)
            logger.info("Expected time: 5-10 minutes")
            logger.info("Endpoint will go through: Creating → InService")
            logger.info("")
            predictor = model.deploy(
                initial_instance_count=args.instance_count,
                instance_type=args.instance_type,
                endpoint_name=endpoint_name,
                wait=True,
            )

        logger.info("\n" + "=" * 80)
        logger.info("✓ DEPLOYMENT SUCCESSFUL!")
        logger.info("=" * 80)
        logger.info(f"Endpoint Name: {endpoint_name}")
        logger.info(f"Region: {region}")
        logger.info(f"Status: InService")
        logger.info(f"Instance Type: {args.instance_type}")
        logger.info(f"Instance Count: {args.instance_count}")
        logger.info("=" * 80)

        return predictor

    except Exception as e:
        logger.error("\n" + "=" * 80)
        logger.error("✗ DEPLOYMENT FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}")
        logger.error("\nCheck CloudWatch logs:")
        logger.error(f"  aws logs tail /aws/sagemaker/Endpoints/{endpoint_name} --follow")
        logger.error("=" * 80)
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
        logger.error("--mlflow-tracking-uri is required when using --model-name")
        logger.error("Set MLFLOW_TRACKING_URI environment variable or use --mlflow-tracking-uri")
        sys.exit(1)

    if args.use_terraform:
        # Validate terraform is installed
        try:
            subprocess.run(["terraform", "version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.error("Terraform not found. Install terraform or remove --use-terraform flag")
            sys.exit(1)

    # Deploy
    predictor = deploy_endpoint(args)

    # Test endpoint (optional - skip if update)
    if not args.update_existing:
        session = sagemaker.Session()
        test_endpoint(predictor.endpoint_name, session.boto_region_name)

    # Final instructions
    logger.info("\n" + "=" * 80)
    logger.info("NEXT STEPS")
    logger.info("=" * 80)
    logger.info("\n1. Test endpoint via AWS CLI:")
    logger.info("   aws sagemaker-runtime invoke-endpoint \\")
    logger.info(f"     --endpoint-name {predictor.endpoint_name} \\")
    logger.info("     --body file://test_input.json \\")
    logger.info("     --content-type application/json \\")
    logger.info("     output.json")

    logger.info("\n2. Monitor endpoint:")
    logger.info(f"   aws sagemaker describe-endpoint --endpoint-name {predictor.endpoint_name}")

    logger.info("\n3. View CloudWatch metrics:")
    session = sagemaker.Session()
    region = session.boto_region_name
    logger.info(f"   https://console.aws.amazon.com/cloudwatch/home?region={region}#metricsV2:graph=~();query=~'*7bAWS*2fSageMaker*2cEndpointName*2cVariantName*7d*20{predictor.endpoint_name}")

    logger.info("\n4. Delete endpoint (when done):")
    logger.info(f"   aws sagemaker delete-endpoint --endpoint-name {predictor.endpoint_name}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
