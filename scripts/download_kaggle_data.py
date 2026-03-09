#!/usr/bin/env python
"""
Kaggle House Prices Dataset Download Script

Tento skript stiahne Kaggle House Prices dataset pomocou Kaggle API.

Použitie:
    python scripts/download_kaggle_data.py

Predpoklady:
    1. Kaggle API credentials nakonfigurované (~/.kaggle/kaggle.json)
    2. kaggle package nainštalovaný (pip install kaggle)

Setup Kaggle API:
    1. Vytvor Kaggle API token:
       - Choď na https://www.kaggle.com/settings
       - Klikni "Create New API Token"
       - Stiahne sa kaggle.json

    2. Umiestni kaggle.json:
       Linux/Mac: ~/.kaggle/kaggle.json
       Windows: C:\\Users\\<username>\\.kaggle\\kaggle.json

    3. Set permissions (Linux/Mac):
       chmod 600 ~/.kaggle/kaggle.json
"""
import os
import sys
import zipfile
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def check_kaggle_api():
    """Check if Kaggle API is installed and configured."""
    try:
        import kaggle
        logger.info("✅ Kaggle API package found")
        return True
    except ImportError:
        logger.error("❌ Kaggle package not found")
        logger.error("   Install with: pip install kaggle")
        return False


def check_kaggle_credentials():
    """Check if Kaggle API credentials are configured."""
    kaggle_json = Path.home() / ".kaggle" / "kaggle.json"

    if kaggle_json.exists():
        logger.info(f"✅ Kaggle credentials found at {kaggle_json}")
        return True
    else:
        logger.error(f"❌ Kaggle credentials not found at {kaggle_json}")
        logger.error("\nSetup instructions:")
        logger.error("  1. Go to https://www.kaggle.com/settings")
        logger.error("  2. Click 'Create New API Token'")
        logger.error("  3. Move kaggle.json to ~/.kaggle/")
        logger.error("  4. chmod 600 ~/.kaggle/kaggle.json")
        return False


def download_dataset(data_dir: str = "data"):
    """
    Download Kaggle House Prices dataset.

    Args:
        data_dir: Directory to save the dataset
    """
    from kaggle.api.kaggle_api_extended import KaggleApi

    # Create data directory
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading dataset to {data_path}...")

    # Initialize Kaggle API
    api = KaggleApi()
    api.authenticate()

    # Competition name
    competition = "house-prices-advanced-regression-techniques"

    try:
        # Download files
        logger.info(f"Downloading {competition}...")
        api.competition_download_files(
            competition,
            path=data_path,
            quiet=False
        )

        # Unzip
        zip_file = data_path / f"{competition}.zip"
        if zip_file.exists():
            logger.info(f"Unzipping {zip_file}...")
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall(data_path)

            # Remove zip file
            zip_file.unlink()
            logger.info("✅ Zip file removed")

        # Check downloaded files
        files = list(data_path.glob("*.csv"))
        logger.info(f"\n✅ Downloaded {len(files)} files:")
        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            logger.info(f"   - {f.name} ({size_mb:.2f} MB)")

        # Verify expected files
        expected_files = ["train.csv", "test.csv"]
        for expected in expected_files:
            if not (data_path / expected).exists():
                logger.warning(f"⚠️  Expected file not found: {expected}")

        return True

    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        return False


def main():
    """Main function."""
    logger.info("=" * 60)
    logger.info("Kaggle House Prices Dataset Downloader")
    logger.info("=" * 60)

    # Check prerequisites
    if not check_kaggle_api():
        sys.exit(1)

    if not check_kaggle_credentials():
        sys.exit(1)

    # Download dataset
    success = download_dataset()

    if success:
        logger.info("\n" + "=" * 60)
        logger.info("✅ Download completed successfully!")
        logger.info("=" * 60)
        logger.info("\nNext steps:")
        logger.info("  1. Explore data: jupyter lab notebooks/01_eda.ipynb")
        logger.info("  2. Feature engineering: notebooks/02_feature_engineering.ipynb")
        logger.info("  3. Model training: notebooks/03_model_training.ipynb")
    else:
        logger.error("\n❌ Download failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
