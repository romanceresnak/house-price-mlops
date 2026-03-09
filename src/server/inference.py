import os
import json
import pickle
import logging

import numpy as np
import pandas as pd
import xgboost as xgb

logger = logging.getLogger(__name__)


def model_fn(model_dir: str):
    """
    Načíta XGBoost model a preprocessing pipeline z model_dir.
    SageMaker volá túto funkciu pri štarte inference kontajnera.
    """
    logger.info(f"Načítavam model z: {model_dir}")

    # Načítaj XGBoost model
    model = xgb.XGBRegressor()
    model_path = os.path.join(model_dir, "xgboost-model")
    model.load_model(model_path)

    # Načítaj preprocessing pipeline
    pipeline_path = os.path.join(model_dir, "preprocessing_pipeline.pkl")
    with open(pipeline_path, "rb") as f:
        pipeline = pickle.load(f)

    logger.info("Model a pipeline úspešne načítané")
    return {"model": model, "pipeline": pipeline}


def input_fn(request_body: str, content_type: str = "application/json"):
    """
    Deserializuje vstup do pandas DataFrame.
    
    Akceptovaný formát:
      Single: { "features": { "GrLivArea": 1500, ... } }
      Batch:  { "instances": [{ "GrLivArea": 1500, ... }, ...] }
    """
    if content_type != "application/json":
        raise ValueError(f"Nepodporovaný content type: {content_type}. Používaj application/json.")

    payload = json.loads(request_body)

    if "features" in payload:
        # Single prediction
        df = pd.DataFrame([payload["features"]])
    elif "instances" in payload:
        # Batch prediction
        df = pd.DataFrame(payload["instances"])
    else:
        raise ValueError("Payload musí obsahovať 'features' alebo 'instances' kľúč.")

    return df


def predict_fn(input_data: pd.DataFrame, model_artifacts: dict):
    """
    Spustí preprocessing + predikciu.
    
    Vracia numpy array s predikciami v log-priestore.
    """
    model = model_artifacts["model"]
    pipeline = model_artifacts["pipeline"]

    # Preprocessing (imputer + scaler)
    X_processed = pipeline.transform(input_data)

    # Predikcia (v log-priestore)
    log_predictions = model.predict(X_processed)

    return log_predictions


def output_fn(predictions: np.ndarray, accept: str = "application/json"):
    """
    Serializuje predikcie do JSON.
    
    Konvertuje z log-priestoru späť na reálne ceny (expm1).
    """
    # Konverzia z log(SalePrice+1) → SalePrice
    real_prices = np.expm1(predictions).tolist()
    log_prices = predictions.tolist()

    if len(real_prices) == 1:
        response = {
            "prediction": real_prices[0],
            "prediction_log": log_prices[0],
        }
    else:
        response = {
            "predictions": real_prices,
            "predictions_log": log_prices,
            "count": len(real_prices),
        }

    return json.dumps(response), accept
