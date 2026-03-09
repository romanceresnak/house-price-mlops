"""
SageMaker Inference Handler

Tento modul definuje funkcie pre SageMaker real-time endpoint:
  - model_fn: načíta model z /opt/ml/model/
  - input_fn: spracuje príchodzí request (JSON → pandas DataFrame)
  - predict_fn: urob predikciu
  - output_fn: naformátuj response
"""
import os
import sys
import json
import pickle
import logging

import pandas as pd
import numpy as np
import xgboost as xgb

# Pridaj src/ do path pre import preprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from data.preprocess import build_preprocessing_pipeline, NUMERIC_FEATURES

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def model_fn(model_dir: str):
    """
    Načíta model a preprocessing pipeline zo SageMaker model directory.

    Args:
        model_dir: Cesta k adresáru s modelom (zvyčajne /opt/ml/model/)

    Returns:
        dict: {'model': xgb_model, 'preprocessor': sklearn_pipeline}
    """
    logger.info(f"Načítavam model z: {model_dir}")

    # XGBoost model
    model_path = os.path.join(model_dir, "xgboost-model")
    model = xgb.XGBRegressor()
    model.load_model(model_path)

    # Preprocessing pipeline
    pipeline_path = os.path.join(model_dir, "preprocessing_pipeline.pkl")
    with open(pipeline_path, "rb") as f:
        preprocessor = pickle.load(f)

    logger.info("Model a preprocessor načítané úspešne")
    return {
        "model": model,
        "preprocessor": preprocessor,
    }


def input_fn(request_body, request_content_type):
    """
    Spracuje príchodzí request do formátu vhodného pre predikciu.

    Args:
        request_body: Telo requestu (bytes alebo str)
        request_content_type: MIME type (napr. 'application/json')

    Returns:
        pd.DataFrame: Vstupné dáta pre predikciu
    """
    if request_content_type == "application/json":
        data = json.loads(request_body)

        # Podporujeme dva formáty:
        # 1. Single instance: {"LotArea": 8450, "OverallQual": 7, ...}
        # 2. Batch: {"instances": [{"LotArea": 8450, ...}, {...}]}

        if "instances" in data:
            # Batch format
            df = pd.DataFrame(data["instances"])
        else:
            # Single instance
            df = pd.DataFrame([data])

        # Validuj že máme požadované features
        missing = set(NUMERIC_FEATURES) - set(df.columns)
        if missing:
            logger.warning(f"Chýbajúce features (budú imputované): {missing}")

        return df[NUMERIC_FEATURES]

    else:
        raise ValueError(f"Nepodporovaný content type: {request_content_type}")


def predict_fn(input_data, model_dict):
    """
    Urobí predikciu na vstupných dátach.

    Args:
        input_data: pd.DataFrame zo input_fn
        model_dict: Dict s 'model' a 'preprocessor' z model_fn

    Returns:
        np.ndarray: Predikované ceny (v originálnej škále, nie log)
    """
    model = model_dict["model"]
    preprocessor = model_dict["preprocessor"]

    # Preprocessing
    X_processed = preprocessor.transform(input_data)

    # Predikcia (model bol trénovaný na log(price))
    log_predictions = model.predict(X_processed)

    # Transformuj späť z log-priestoru
    predictions = np.expm1(log_predictions)  # inverse of np.log1p

    return predictions


def output_fn(predictions, response_content_type):
    """
    Naformátuj výstup do požadovaného formátu.

    Args:
        predictions: np.ndarray z predict_fn
        response_content_type: Požadovaný MIME type

    Returns:
        str: Serializovaný response
    """
    if response_content_type == "application/json":
        return json.dumps({
            "predictions": predictions.tolist()
        })
    else:
        raise ValueError(f"Nepodporovaný response content type: {response_content_type}")


# ============================================================================
# Local testing
# ============================================================================

if __name__ == "__main__":
    """
    Lokálne testovanie inference handlera.
    """
    print("=== Testovanie SageMaker inference handlera ===\n")

    # Mock dáta
    test_data = {
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

    # Test input_fn
    print("1. Testing input_fn...")
    request_body = json.dumps(test_data)
    df = input_fn(request_body, "application/json")
    print(f"   ✓ Input shape: {df.shape}")
    print(f"   ✓ Columns: {list(df.columns)}\n")

    # Test batch format
    print("2. Testing batch input...")
    batch_data = {"instances": [test_data, test_data]}
    request_body = json.dumps(batch_data)
    df_batch = input_fn(request_body, "application/json")
    print(f"   ✓ Batch shape: {df_batch.shape}\n")

    print("✓ Všetky testy prešli. Inference handler je ready.")
    print("\nPre plné testovanie s modelom spusti:")
    print("  python src/train/train.py --train ./data --model-dir ./models")
    print("  python src/serve/inference.py")
