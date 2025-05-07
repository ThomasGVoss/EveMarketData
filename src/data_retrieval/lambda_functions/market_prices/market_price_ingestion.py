import json
import urllib3
import boto3
import os
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_market_prices():
    """Retrieve market prices from EVE ESI API"""
    url = "https://esi.evetech.net/latest/markets/prices/"
    http = urllib3.PoolManager()
    response = http.request("GET", url)
    
    if response.status != 200:
        raise Exception(f"API request failed with status code {response.status}")
    
    return json.loads(response.data)

def lambda_handler(event, context):
    try:
        # Get market data
        market_data = get_market_prices()
        
        # Get current timestamp
        now = datetime.utcnow()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        hour = now.strftime('%H')
        
        # Define S3 path
        s3_path = f"raw/api-data/prices/year={year}/month={month}/day={day}/hour={hour}/"
        file_name = f"price_data_{timestamp}.json"
        full_path = s3_path + file_name
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Get bucket name from environment variable
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=full_path,
            Body=json.dumps(market_data),
            ContentType='application/json'
        )
        
        logger.info(f"Successfully saved market data to s3://{bucket_name}/{full_path}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Market data ingestion successful',
                'timestamp': timestamp,
                's3_path': f"s3://{bucket_name}/{full_path}"
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing market data: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 