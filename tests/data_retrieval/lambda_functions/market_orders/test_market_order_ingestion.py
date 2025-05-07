import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

@patch('requests.get')
@patch('boto3.client')
def test_lambda_handler(mock_boto_client, mock_requests_get):

    # Mock type IDs response
    mock_requests_get.side_effect = [
        # Mock response for retrieve_type_ids_by_region
        MagicMock(status_code=200, json=lambda: [2369, 12345]),
        # Mock response for retrieve_market_orders (first type_id)
        MagicMock(status_code=200, json=lambda: [{"order_id": 1}, {"order_id": 2}]),
        MagicMock(status_code=200, json=lambda: []),  # End of pagination
        # Mock response for retrieve_market_orders (second type_id)
        MagicMock(status_code=200, json=lambda: [{"order_id": 3}]),
        MagicMock(status_code=200, json=lambda: []),  # End of pagination
    ]

    # Mock S3 client
    mock_s3 = MagicMock()
    mock_boto_client.return_value = mock_s3

    # Mock environment variable
    with patch.dict('os.environ', {'S3_BUCKET_NAME': 'test-bucket'}):
        from data_retrieval.lambda_functions.market_orders.market_order_ingestion import lambda_handler
        # Call the lambda_handler
        event = {}
        context = {}
        response = lambda_handler(event, context)
