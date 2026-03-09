"""
Unit testy pre src/data/preprocess.py

Spustenie testov:
    pytest tests/test_preprocess.py -v
    pytest tests/test_preprocess.py -v --cov=src/data --cov-report=html
"""
import os
import sys
import tempfile

import pytest
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline

# Pridaj src/ do Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from data.preprocess import (
    FeatureEngineer,
    build_preprocessing_pipeline,
    build_feature_list,
    load_data,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_df():
    """Vytvorí ukážkový DataFrame pre testovanie."""
    return pd.DataFrame({
        "LotArea": [8450, 9600, 11250],
        "OverallQual": [7, 6, 7],
        "OverallCond": [5, 8, 5],
        "YearBuilt": [2003, 1976, 2001],
        "YearRemodAdd": [2003, 1976, 2002],
        "TotalBsmtSF": [856, 1262, 920],
        "1stFlrSF": [856, 1262, 920],
        "2ndFlrSF": [854, 0, 866],
        "GrLivArea": [1710, 1262, 1786],
        "FullBath": [2, 2, 2],
        "HalfBath": [1, 0, 1],
        "BedroomAbvGr": [3, 3, 3],
        "TotRmsAbvGrd": [8, 6, 6],
        "GarageCars": [2, 2, 2],
        "GarageArea": [548, 460, 608],
        "WoodDeckSF": [0, 298, 0],
        "OpenPorchSF": [61, 0, 42],
        "YrSold": [2008, 2007, 2008],
        TARGET_COLUMN: [208500, 181500, 223500],
    })


@pytest.fixture
def sample_csv(sample_df):
    """Vytvorí dočasný CSV súbor pre testovanie load_data."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        sample_df.to_csv(f.name, index=False)
        yield f.name
    os.unlink(f.name)


# ============================================================================
# Test 1: FeatureEngineer - TotalSF
# ============================================================================

def test_feature_engineer_total_sf(sample_df):
    """Test že FeatureEngineer správne vytvorí TotalSF feature."""
    fe = FeatureEngineer()
    result = fe.fit_transform(sample_df)

    expected_total_sf = (
        sample_df["TotalBsmtSF"] + sample_df["1stFlrSF"] + sample_df["2ndFlrSF"]
    )

    assert "TotalSF" in result.columns
    pd.testing.assert_series_equal(
        result["TotalSF"], expected_total_sf, check_names=False
    )


# ============================================================================
# Test 2: FeatureEngineer - HouseAge
# ============================================================================

def test_feature_engineer_house_age(sample_df):
    """Test že FeatureEngineer správne počíta HouseAge."""
    fe = FeatureEngineer()
    result = fe.fit_transform(sample_df)

    expected_age = sample_df["YrSold"] - sample_df["YearBuilt"]

    assert "HouseAge" in result.columns
    pd.testing.assert_series_equal(
        result["HouseAge"], expected_age, check_names=False
    )


# ============================================================================
# Test 3: FeatureEngineer - WasRemodeled
# ============================================================================

def test_feature_engineer_was_remodeled(sample_df):
    """Test že FeatureEngineer správne detekuje remodeling."""
    fe = FeatureEngineer()
    result = fe.fit_transform(sample_df)

    # Row 0: YearBuilt == YearRemodAdd → not remodeled
    # Row 1: YearBuilt == YearRemodAdd → not remodeled
    # Row 2: YearBuilt != YearRemodAdd → remodeled
    expected = pd.Series([0, 0, 1], dtype=int)

    assert "WasRemodeled" in result.columns
    pd.testing.assert_series_equal(
        result["WasRemodeled"], expected, check_names=False
    )


# ============================================================================
# Test 4: FeatureEngineer - TotalBaths
# ============================================================================

def test_feature_engineer_total_baths(sample_df):
    """Test že FeatureEngineer správne počíta TotalBaths."""
    fe = FeatureEngineer()
    result = fe.fit_transform(sample_df)

    expected_baths = sample_df["FullBath"] + 0.5 * sample_df["HalfBath"]

    assert "TotalBaths" in result.columns
    pd.testing.assert_series_equal(
        result["TotalBaths"], expected_baths, check_names=False
    )


# ============================================================================
# Test 5: FeatureEngineer - handling missing YrSold
# ============================================================================

def test_feature_engineer_missing_yrsold(sample_df):
    """Test že FeatureEngineer správne funguje aj bez YrSold column."""
    # Odstráň YrSold
    df_no_yrsold = sample_df.drop(columns=["YrSold"])

    fe = FeatureEngineer()
    result = fe.fit_transform(df_no_yrsold)

    # Mal by použiť default 2010
    assert "HouseAge" in result.columns
    assert result["HouseAge"].min() >= 0  # Age nemôže byť záporný


# ============================================================================
# Test 6: build_feature_list obsahuje všetky engineered features
# ============================================================================

def test_build_feature_list():
    """Test že build_feature_list vracia správne features."""
    features = build_feature_list()

    # Musí obsahovať base features
    for feat in NUMERIC_FEATURES:
        assert feat in features

    # Musí obsahovať engineered features
    assert "TotalSF" in features
    assert "HouseAge" in features
    assert "WasRemodeled" in features
    assert "TotalBaths" in features


# ============================================================================
# Test 7: build_preprocessing_pipeline vracia Pipeline
# ============================================================================

def test_build_preprocessing_pipeline():
    """Test že build_preprocessing_pipeline vracia sklearn Pipeline."""
    pipeline = build_preprocessing_pipeline()

    assert isinstance(pipeline, Pipeline)
    assert len(pipeline.steps) == 3

    # Skontroluj že obsahuje správne transformers
    step_names = [name for name, _ in pipeline.steps]
    assert "feature_engineering" in step_names
    assert "imputer" in step_names
    assert "scaler" in step_names


# ============================================================================
# Test 8: Pipeline fit_transform funguje end-to-end
# ============================================================================

def test_pipeline_fit_transform(sample_df):
    """Test že pipeline dokáže fit_transform data."""
    pipeline = build_preprocessing_pipeline()

    X = sample_df[NUMERIC_FEATURES]
    X_transformed = pipeline.fit_transform(X)

    # Výstup musí byť numpy array
    assert isinstance(X_transformed, np.ndarray)

    # Shape musí byť (n_samples, n_features)
    assert X_transformed.shape[0] == len(sample_df)
    assert X_transformed.shape[1] > 0

    # Po StandardScaler by mali byť dáta ~ normalizované (mean ≈ 0, std ≈ 1)
    # (nie exaktne kvôli malému sample size, ale close enough)
    assert abs(X_transformed.mean()) < 2.0


# ============================================================================
# Test 9: load_data z CSV súboru
# ============================================================================

def test_load_data_single_file(sample_csv):
    """Test že load_data správne načíta train CSV."""
    X, y = load_data(sample_csv)

    # X musí byť DataFrame s NUMERIC_FEATURES
    assert isinstance(X, pd.DataFrame)
    assert list(X.columns) == NUMERIC_FEATURES
    assert len(X) == 3

    # y musí byť log-transformovaný
    assert isinstance(y, pd.Series)
    assert len(y) == 3

    # y musí byť log(SalePrice + 1)
    expected_y = np.log1p(pd.Series([208500, 181500, 223500]))
    pd.testing.assert_series_equal(y, expected_y, check_names=False)


# ============================================================================
# Test 10: load_data s train a test súbormi
# ============================================================================

def test_load_data_train_test(sample_csv, sample_df):
    """Test že load_data dokáže načítať train aj test súbory."""
    # Vytvor test CSV (bez TARGET_COLUMN)
    test_df = sample_df.drop(columns=[TARGET_COLUMN])
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        test_df.to_csv(f.name, index=False)
        test_csv = f.name

    try:
        X_train, y_train, X_test = load_data(sample_csv, test_csv)

        # Train data
        assert isinstance(X_train, pd.DataFrame)
        assert len(X_train) == 3
        assert isinstance(y_train, pd.Series)
        assert len(y_train) == 3

        # Test data
        assert isinstance(X_test, pd.DataFrame)
        assert len(X_test) == 3
        assert list(X_test.columns) == NUMERIC_FEATURES

    finally:
        os.unlink(test_csv)


# ============================================================================
# Bonus test: Pipeline handling missing values
# ============================================================================

def test_pipeline_handles_missing_values():
    """Test že pipeline správne nahrádza chýbajúce hodnoty."""
    df_with_na = pd.DataFrame({
        "LotArea": [8450, np.nan, 11250],
        "OverallQual": [7, 6, np.nan],
        "OverallCond": [5, 8, 5],
        "YearBuilt": [2003, 1976, 2001],
        "YearRemodAdd": [2003, 1976, 2002],
        "TotalBsmtSF": [856, 1262, 920],
        "1stFlrSF": [856, 1262, 920],
        "2ndFlrSF": [854, 0, 866],
        "GrLivArea": [1710, 1262, 1786],
        "FullBath": [2, 2, 2],
        "HalfBath": [1, 0, 1],
        "BedroomAbvGr": [3, 3, 3],
        "TotRmsAbvGrd": [8, 6, 6],
        "GarageCars": [2, 2, 2],
        "GarageArea": [548, 460, 608],
        "WoodDeckSF": [0, 298, 0],
        "OpenPorchSF": [61, 0, 42],
    })

    pipeline = build_preprocessing_pipeline()
    X_transformed = pipeline.fit_transform(df_with_na)

    # Výstup nesmie obsahovať NaN
    assert not np.isnan(X_transformed).any()


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
