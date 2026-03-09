import os
import sys
import json
import argparse
import logging
from pathlib import Path

import pandas as pd
import numpy as np
import xgboost as xgb
import mlflow
import mlflow.xgboost
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Pridaj src/ do Python path (pre import preprocess)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data.preprocess import build_preprocessing_pipeline, load_data, NUMERIC_FEATURES

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(asctime)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def load_sagemaker_hyperparameters():
    """
    Načíta hyperparametre zo SageMaker hyperparameters.json súboru.
    SageMaker uloží všetky hyperparametre do /opt/ml/input/config/hyperparameters.json
    """
    hp_file = "/opt/ml/input/config/hyperparameters.json"
    if os.path.exists(hp_file):
        with open(hp_file, "r") as f:
            return json.load(f)
    return {}


def parse_args():
    parser = argparse.ArgumentParser()

    # Načítaj SageMaker hyperparametre ak existujú
    sm_hps = load_sagemaker_hyperparameters()

    # --- SageMaker data channels ---
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--output-data-dir", type=str, default=os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output"))
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))

    # --- SageMaker environment info ---
    parser.add_argument("--num-cpus", type=int, default=int(os.environ.get("SM_NUM_CPUS", "1")))
    parser.add_argument("--num-gpus", type=int, default=int(os.environ.get("SM_NUM_GPUS", "0")))
    parser.add_argument("--current-host", type=str, default=os.environ.get("SM_CURRENT_HOST", "localhost"))
    parser.add_argument("--hosts", type=str, default=os.environ.get("SM_HOSTS", '["localhost"]'))

    # --- MLflow ---
    parser.add_argument("--mlflow-tracking-uri", type=str, default=sm_hps.get("mlflow-tracking-uri", os.environ.get("MLFLOW_TRACKING_URI", "")))
    parser.add_argument("--mlflow-experiment-name", type=str, default=sm_hps.get("mlflow-experiment-name", os.environ.get("MLFLOW_EXPERIMENT_NAME", "house-prices")))

    # --- XGBoost hyperparametre ---
    parser.add_argument("--n-estimators", type=int, default=int(sm_hps.get("n-estimators", 500)))
    parser.add_argument("--max-depth", type=int, default=int(sm_hps.get("max-depth", 6)))
    parser.add_argument("--learning-rate", type=float, default=float(sm_hps.get("learning-rate", 0.05)))
    parser.add_argument("--subsample", type=float, default=float(sm_hps.get("subsample", 0.8)))
    parser.add_argument("--colsample-bytree", type=float, default=float(sm_hps.get("colsample-bytree", 0.8)))
    parser.add_argument("--min-child-weight", type=int, default=int(sm_hps.get("min-child-weight", 3)))
    parser.add_argument("--reg-alpha", type=float, default=float(sm_hps.get("reg-alpha", 0.1)))
    parser.add_argument("--reg-lambda", type=float, default=float(sm_hps.get("reg-lambda", 1.0)))

    return parser.parse_args()


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """
    Vypočíta štandardné regresné metriky.
    Pracuje v log-priestore (SalePrice je log-transformovaný).
    """
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mae = mean_absolute_error(y_true, y_pred)
    r2 = r2_score(y_true, y_pred)

    # RMSLE (Root Mean Squared Log Error) — štandardná metrika pre Kaggle house prices
    rmsle = np.sqrt(mean_squared_error(y_true, y_pred))  # y je už v log-priestore

    return {
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "rmsle": rmsle,
    }


def train(args):
    # --- Log SageMaker environment ---
    logger.info("=" * 80)
    logger.info("SageMaker Training Job Started")
    logger.info("=" * 80)
    logger.info(f"Current host: {args.current_host}")
    logger.info(f"Available CPUs: {args.num_cpus}")
    logger.info(f"Available GPUs: {args.num_gpus}")
    logger.info(f"Train data path: {args.train}")
    logger.info(f"Model output path: {args.model_dir}")
    logger.info("=" * 80)

    # --- Nastav MLflow ---
    if args.mlflow_tracking_uri:
        mlflow.set_tracking_uri(args.mlflow_tracking_uri)
        logger.info(f"MLflow tracking URI: {args.mlflow_tracking_uri}")
    else:
        logger.warning("MLflow tracking URI not set - metrics will only be logged locally")

    mlflow.set_experiment(args.mlflow_experiment_name)

    # --- Načítaj dáta ---
    train_csv = os.path.join(args.train, "train.csv")
    logger.info(f"Načítavam dáta z: {train_csv}")

    if not os.path.exists(train_csv):
        raise FileNotFoundError(f"Training data not found: {train_csv}")

    X, y = load_data(train_csv)
    logger.info(f"Data loaded successfully: {X.shape[0]} samples, {X.shape[1]} features")

    # Train/validation split (80/20)
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    logger.info(f"Train: {X_train.shape}, Val: {X_val.shape}")

    # --- Preprocessing pipeline ---
    preprocess = build_preprocessing_pipeline()
    X_train_processed = preprocess.fit_transform(X_train)
    X_val_processed = preprocess.transform(X_val)

    # --- MLflow run ---
    with mlflow.start_run() as run:
        logger.info(f"MLflow run ID: {run.info.run_id}")

        # Hyperparametre
        hyperparams = {
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "learning_rate": args.learning_rate,
            "subsample": args.subsample,
            "colsample_bytree": args.colsample_bytree,
            "min_child_weight": args.min_child_weight,
            "reg_alpha": args.reg_alpha,
            "reg_lambda": args.reg_lambda,
        }
        mlflow.log_params(hyperparams)

        # Tags
        mlflow.set_tags({
            "framework": "xgboost",
            "dataset": "kaggle-house-prices",
            "region": "eu-west-1",
            "training_env": "sagemaker",
            "sagemaker_host": args.current_host,
            "num_cpus": str(args.num_cpus),
        })

        # --- Trénuj model ---
        # Použij dostupné CPUs (n_jobs=-1 používa všetky, alebo nastav konkrétny počet)
        n_jobs = args.num_cpus if args.num_cpus > 0 else -1
        logger.info(f"Training model with {n_jobs} CPUs")

        model = xgb.XGBRegressor(
            **hyperparams,
            random_state=42,
            n_jobs=n_jobs,
            early_stopping_rounds=50,
            eval_metric="rmse",
        )

        logger.info("Starting model training...")
        model.fit(
            X_train_processed,
            y_train,
            eval_set=[(X_val_processed, y_val)],
            verbose=100,
        )
        logger.info("Model training completed!")

        # --- Evaluácia ---
        logger.info("Evaluating model on validation set...")
        y_pred_val = model.predict(X_val_processed)
        metrics = compute_metrics(y_val.values, y_pred_val)
        mlflow.log_metrics(metrics)

        logger.info("=" * 80)
        logger.info("VALIDATION METRICS:")
        for metric, value in metrics.items():
            logger.info(f"  {metric.upper()}: {value:.6f}")
        logger.info("=" * 80)

        # Train metriky
        y_pred_train = model.predict(X_train_processed)
        train_metrics = compute_metrics(y_train.values, y_pred_train)
        mlflow.log_metrics({f"train_{k}": v for k, v in train_metrics.items()})

        # --- Ulož model do MLflow ---
        if args.mlflow_tracking_uri:
            logger.info("Saving model to MLflow...")
            # mlflow.xgboost.log_model uloží model vrátane signatúry
            signature = mlflow.models.infer_signature(
                X_val_processed, y_pred_val
            )
            try:
                mlflow.xgboost.log_model(
                    model,
                    artifact_path="model",
                    signature=signature,
                    registered_model_name="house-price-xgboost",
                )
                logger.info("Model successfully saved to MLflow registry")
            except Exception as e:
                logger.warning(f"Failed to register model to MLflow: {e}")
                # Continue execution - model will still be saved to SageMaker

            # Ulož aj preprocessing pipeline ako artifact
            import pickle
            pipeline_path = os.path.join(args.output_data_dir, "preprocessing_pipeline.pkl")
            os.makedirs(args.output_data_dir, exist_ok=True)
            with open(pipeline_path, "wb") as f:
                pickle.dump(preprocess, f)
            mlflow.log_artifact(pipeline_path, artifact_path="preprocessing")

            # Ulož feature importance
            feat_importance = pd.DataFrame({
                "feature": NUMERIC_FEATURES[:X_train_processed.shape[1]],
                "importance": model.feature_importances_[:len(NUMERIC_FEATURES)],
            }).sort_values("importance", ascending=False)
            importance_path = os.path.join(args.output_data_dir, "feature_importance.csv")
            feat_importance.to_csv(importance_path, index=False)
            mlflow.log_artifact(importance_path)

            logger.info(f"MLflow artifacts saved. Run ID: {run.info.run_id}")
        else:
            logger.info("Skipping MLflow model registration (no tracking URI set)")

    # --- Ulož model pre SageMaker (do /opt/ml/model/) ---
    # SageMaker očakáva model v tomto adresári
    logger.info("=" * 80)
    logger.info("Saving model for SageMaker deployment...")
    logger.info("=" * 80)

    try:
        os.makedirs(args.model_dir, exist_ok=True)

        model_output_path = os.path.join(args.model_dir, "xgboost-model")
        model.save_model(model_output_path)
        logger.info(f"✓ Model saved: {model_output_path}")

        # Ulož aj pipeline
        import pickle
        pipeline_sm_path = os.path.join(args.model_dir, "preprocessing_pipeline.pkl")
        with open(pipeline_sm_path, "wb") as f:
            pickle.dump(preprocess, f)
        logger.info(f"✓ Preprocessing pipeline saved: {pipeline_sm_path}")

        logger.info("=" * 80)
        logger.info("Training job completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Failed to save model: {e}")
        raise


if __name__ == "__main__":
    try:
        args = parse_args()
        train(args)
    except Exception as e:
        logger.error("=" * 80)
        logger.error("TRAINING JOB FAILED")
        logger.error("=" * 80)
        logger.error(f"Error: {str(e)}", exc_info=True)
        logger.error("=" * 80)
        # Exit with error code so SageMaker marks job as failed
        sys.exit(1)
