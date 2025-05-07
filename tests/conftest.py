"""Test fixtures for SageMaker pipeline tests."""
import pytest
import boto3
import sagemaker
import pandas as pd
from unittest.mock import MagicMock

@pytest.fixture
def aws_region():
    """Provide default AWS region for tests."""
    return "eu-central-1"

@pytest.fixture
def aws_role():
    """Provide default AWS role for tests."""
    return "arn:aws:iam::123456789012:role/SageMakerRole"

@pytest.fixture
def mock_boto_session():
    """Provide a mocked boto3 session."""
    session = MagicMock()
    session.region_name = "eu-central-1"
    return session

@pytest.fixture
def mock_sagemaker_session(mock_boto_session):
    """Provide a mocked SageMaker session."""
    sagemaker_session = MagicMock()
    sagemaker_session.boto_session = mock_boto_session
    sagemaker_session.default_bucket.return_value = "sagemaker-test-bucket"
    return sagemaker_session

@pytest.fixture
def test_data():
    """Provide test data for preprocessing."""
    return {
        "sex": ["M", "F", "M", "F"],
        "length": [0.455, 0.35, 0.53, 0.44],
        "diameter": [0.365, 0.265, 0.42, 0.365],
        "height": [0.095, 0.09, 0.135, 0.125],
        "whole_weight": [0.514, 0.226, 0.677, 0.516],
        "shucked_weight": [0.2245, 0.0995, 0.2565, 0.2155],
        "viscera_weight": [0.101, 0.0485, 0.1415, 0.114],
        "shell_weight": [0.15, 0.07, 0.21, 0.155],
        "rings": [15, 7, 9, 10]
    }

@pytest.fixture
def load_preprocessing_data():

    mock_data = pd.DataFrame({
        "processed_timestamp": ["2025-04-19 12:00:00", "2025-04-19 13:00:00", "2025-04-19 14:00:00", "2025-04-19 15:00:00", "2025-04-19 16:00:00"],
        "source_path" : ["a/b/x","a/b/y","a/b/z","a/b/x","a/b/y"],
        "type_id": ["123", "123", "123", "123", "123"],
        "average_price": [100.0, 200.0, 200.0, 300.0, 400.0],
        "adjusted_price": [95.0, 190.0, 190.0, 285.0, 380.0],
    })

    input_url = "s3://market-data-dev-142571790518/aggregated/market_prices"
    mock_data = pd.read_parquet(input_url)

    return mock_data
