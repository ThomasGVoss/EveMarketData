"""Tests for the preprocessing script."""
import pytest
import pandas as pd
import numpy as np
from unittest import mock
from unittest.mock import patch, MagicMock
import tempfile
import os

@patch("pandas.read_parquet")
# @patch("joblib.dump")
@patch("pandas.DataFrame.to_csv")
def test_main(mock_to_csv, 
              # mock_joblib_dump, 
              mock_read_parquet, 
              load_preprocessing_data):
    # Mock input data
    mock_read_parquet.return_value = load_preprocessing_data
    base_dir = os.path.dirname(os.path.abspath(__file__))
    encoder_dir = os.path.join(base_dir, "encoder")
    os.makedirs(encoder_dir, exist_ok=True)
    
    # Run the main function
    with patch("argparse.ArgumentParser.parse_args"):
        from training_pipelines.abalone.preprocess import main as main_function
        main_function(base_dir=base_dir)

    # Verify that the data was split and written to CSV
    assert mock_to_csv.call_count == 3  # train, validation, test

    # Verify that the preprocessing pipeline was saved
    # mock_joblib_dump.assert_called_once()

    # Verify that the input data was read
    mock_read_parquet.assert_called_once_with(f"{base_dir}/input/data")       