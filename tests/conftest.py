"""Test fixtures for SageMaker pipeline tests."""
import pytest
import boto3
import sagemaker
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