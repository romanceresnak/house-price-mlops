import pandas as pd
import numpy as np
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer


# Numerické featury ktoré použijeme
NUMERIC_FEATURES = [
    "LotArea",
    "OverallQual",
    "OverallCond",
    "YearBuilt",
    "YearRemodAdd",
    "TotalBsmtSF",
    "1stFlrSF",
    "2ndFlrSF",
    "GrLivArea",
    "FullBath",
    "HalfBath",
    "BedroomAbvGr",
    "TotRmsAbvGrd",
    "GarageCars",
    "GarageArea",
    "WoodDeckSF",
    "OpenPorchSF",
]

TARGET_COLUMN = "SalePrice"


class FeatureEngineer(BaseEstimator, TransformerMixin):
    """
    Vlastný transformer pre house price features.
    Pridáva odvodené featury pred štandardizáciou.
    """

    def fit(self, X, y=None):
        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        X = X.copy()

        # Celková plocha (basement + prízemie + poschodie)
        X["TotalSF"] = (
            X.get("TotalBsmtSF", 0)
            + X.get("1stFlrSF", 0)
            + X.get("2ndFlrSF", 0)
        )

        # Vek domu pri predaji (potrebujeme YrSold, ak chýba použijeme 2010)
        yr_sold = X.get("YrSold", pd.Series([2010] * len(X)))
        X["HouseAge"] = yr_sold - X.get("YearBuilt", yr_sold)
        X["HouseAge"] = X["HouseAge"].clip(lower=0)

        # Remodeling flag
        X["WasRemodeled"] = (
            X.get("YearRemodAdd", X.get("YearBuilt", 0))
            != X.get("YearBuilt", 0)
        ).astype(int)

        # Celkové kúpeľne
        X["TotalBaths"] = X.get("FullBath", 0) + 0.5 * X.get("HalfBath", 0)

        return X


def build_feature_list() -> list:
    """Vráti finálny zoznam features po feature engineeringu."""
    engineered = ["TotalSF", "HouseAge", "WasRemodeled", "TotalBaths"]
    # Niektoré base features môžu byť redundantné po FE, ale necháme všetky
    return NUMERIC_FEATURES + engineered


def build_preprocessing_pipeline() -> Pipeline:
    """
    Vytvorí sklearn pipeline pre preprocessing.
    
    Pipeline kroky:
      1. FeatureEngineer  - pridá odvodené featury
      2. SimpleImputer    - nahradí chýbajúce hodnoty mediánom
      3. StandardScaler   - škáluje na mean=0, std=1
    """
    pipeline = Pipeline([
        ("feature_engineering", FeatureEngineer()),
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])
    return pipeline


def load_data(train_path: str, test_path: str = None):
    """
    Načíta Kaggle House Prices CSV súbory.
    
    Returns:
        X_train, y_train, X_test (ak je test_path zadaný)
    """
    train_df = pd.read_csv(train_path)

    # Log-transform target (bežná prax pre ceny nehnuteľností)
    y_train = np.log1p(train_df[TARGET_COLUMN])
    X_train = train_df[NUMERIC_FEATURES]

    if test_path:
        test_df = pd.read_csv(test_path)
        X_test = test_df[NUMERIC_FEATURES]
        return X_train, y_train, X_test

    return X_train, y_train


def get_feature_names_after_pipeline() -> list:
    """Vráti názvy features v poradí akceptovanom pipeline-om."""
    return NUMERIC_FEATURES  # FeatureEngineer pridá nové stĺpce na koniec
