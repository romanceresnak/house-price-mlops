import os
import sys
import json
import argparse
import logging

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
logging.basicConfig(level=logging.INFO)


def parse_args():
    parser = argparse.ArgumentParser()

    # --- SageMaker data channels ---
    parser.add_argument("--train", type=str, default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--output-data-dir", type=str, default=os.environ.get("SM_OUTPUT_DATA_DIR", "/opt/ml/output"))
    parser.add_argument("--model-dir", type=str, default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))

    # --- MLflow ---
    parser.add_argument("--mlflow-tracking-uri", type=str, default=os.environ.get("MLFLOW_TRACKING_URI", ""))
    parser.add_argument("--mlflow-experiment-name", type=str, default=os.environ.get("MLFLOW_EXPERIMENT_NAME", "house-prices"))

    # --- XGBoost hyperparametre ---
    parser.add_argument("--n-estimators", type=int, default=500)
    parser.add_argument("--max-depth", type=int, default=6)
    parser.add_argument("--learning-rate", type=float, default=0.05)
    parser.add_argument("--subsample", type=float, default=0.8)
    parser.add_argument("--colsample-bytree", type=float, default=0.8)
    parser.add_argument("--min-child-weight", type=int, default=3)
    parser.add_argument("--reg-alpha", type=float, default=0.1)
    parser.add_argument("--reg-lambda", type=float, default=1.0)

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
    # --- Nastav MLflow ---
    if args.mlflow_tracking_uri:
        mlflow.set_tracking_uri(args.mlflow_tracking_uri)
        logger.info(f"MLflow tracking URI: {args.mlflow_tracking_uri}")

    mlflow.set_experiment(args.mlflow_experiment_name)

    # --- Načítaj dáta ---
    train_csv = os.path.join(args.train, "train.csv")
    logger.info(f"Načítavam dáta z: {train_csv}")
    X, y = load_data(train_csv)

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
        })

        # --- Trénuj model ---
        model = xgb.XGBRegressor(
            **hyperparams,
            random_state=42,
            n_jobs=-1,
            early_stopping_rounds=50,
            eval_metric="rmse",
        )

        model.fit(
            X_train_processed,
            y_train,
            eval_set=[(X_val_processed, y_val)],
            verbose=100,
        )

        # --- Evaluácia ---
        y_pred_val = model.predict(X_val_processed)
        metrics = compute_metrics(y_val.values, y_pred_val)
        mlflow.log_metrics(metrics)
        logger.info(f"Validation metrics: {metrics}")

        # Train metriky
        y_pred_train = model.predict(X_train_processed)
        train_metrics = compute_metrics(y_train.values, y_pred_train)
        mlflow.log_metrics({f"train_{k}": v for k, v in train_metrics.items()})

        # --- Ulož model do MLflow ---
        # mlflow.xgboost.log_model uloží model vrátane signatúry
        signature = mlflow.models.infer_signature(
            X_val_processed, y_pred_val
        )
        mlflow.xgboost.log_model(
            model,
            artifact_path="model",
            signature=signature,
            registered_model_name="house-price-xgboost",
        )

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

        logger.info(f"Model uložený. Run ID: {run.info.run_id}")

    # --- Ulož model pre SageMaker (do /opt/ml/model/) ---
    # SageMaker očakáva model v tomto adresári
    model_output_path = os.path.join(args.model_dir, "xgboost-model")
    model.save_model(model_output_path)
    logger.info(f"SageMaker model uložený do: {model_output_path}")

    # Ulož aj pipeline
    import pickle
    pipeline_sm_path = os.path.join(args.model_dir, "preprocessing_pipeline.pkl")
    with open(pipeline_sm_path, "wb") as f:
        pickle.dump(preprocess, f)


if __name__ == "__main__":
    args = parse_args()
    train(args)
