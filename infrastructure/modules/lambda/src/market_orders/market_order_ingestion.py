import json
import urllib3
import boto3
import os
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def retrieve_by_region_and_id(region, type_id): 
    """Retrieve market orders for a specific region and type ID"""
    params = f'?datasource=tranquility&order_type=all&page=1&type_id={type_id}'
    url = f"https://esi.evetech.net/latest/markets/{region}/orders/{params}"
    
    http = urllib3.PoolManager()
    response = http.request("GET", url)

    if response.status != 200:
        logger.warning(f"API request failed with status code {response.status} for region {region}, type {type_id}")
        return None
    
    return json.loads(response.data)

def process_orders(orders_data, region_id, type_id):
    """Process and aggregate order data into buy/sell statistics"""
    if not orders_data or len(orders_data) == 0:
        logger.warning(f"No order data received for region {region_id}, type {type_id}")
        return None
    
    # Separate buy and sell orders
    buy_orders = [order.get('price', 0) for order in orders_data if order.get('is_buy_order', False)]
    sell_orders = [order.get('price', 0) for order in orders_data if not order.get('is_buy_order', False)]
    
    # Calculate stats for each order type
    result = []
    
    # Only add buy order stats if we have data
    if buy_orders:
        result.append({
            "typeId": type_id,
            "regionId": region_id,
            "isBuyOrder": True,
            "minPrice": min(buy_orders),
            "meanPrice": sum(buy_orders) / len(buy_orders),
            "maxPrice": max(buy_orders),
            "orderCount": len(buy_orders),
            "generated": datetime.utcnow().isoformat()
        })
    
    # Only add sell order stats if we have data
    if sell_orders:
        result.append({
            "typeId": type_id,
            "regionId": region_id,
            "isBuyOrder": False,
            "minPrice": min(sell_orders),
            "meanPrice": sum(sell_orders) / len(sell_orders),
            "maxPrice": max(sell_orders),
            "orderCount": len(sell_orders),
            "generated": datetime.utcnow().isoformat()
        })
    
    return result

def lambda_handler(event, context):
    try:
        # Get region IDs and type IDs from environment variables
        region_ids = [int(r) for r in os.environ.get('REGIONS', '10000002,10000032,10000043,10000030').split(',')]
        type_ids = [int(t) for t in os.environ.get('TYPE_IDS', '17357,230,222,9957').split(',')]
        
        # Get current timestamp for S3 path
        now = datetime.utcnow()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        hour = now.strftime('%H')
        
        # Collect all processed results
        all_results = []
        
        # Process each region and type combination
        for region_id in region_ids:
            logger.info(f"Processing region {region_id}")
            for type_id in type_ids:
                # Retrieve raw order data
                raw_data = retrieve_by_region_and_id(region_id, type_id)
                
                if raw_data:
                    # Process the order data
                    processed_data = process_orders(raw_data, region_id, type_id)
                    if processed_data:
                        all_results.extend(processed_data)
        
        if not all_results:
            raise Exception("No valid market order data was retrieved")
        
        # Define S3 path
        s3_path = f"raw/api-data/orders/year={year}/month={month}/day={day}/hour={hour}/"
        file_name = f"order_data_{timestamp}.json"
        full_path = s3_path + file_name
        
        # Initialize S3 client
        s3_client = boto3.client('s3')
        
        # Get bucket name from environment variable
        bucket_name = os.environ.get('S3_BUCKET_NAME')
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=full_path,
            Body=json.dumps(all_results),
            ContentType='application/json'
        )
        
        logger.info(f"Successfully saved {len(all_results)} market order records to s3://{bucket_name}/{full_path}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Market order data ingestion successful',
                'timestamp': timestamp,
                'region_count': len(region_ids),
                'type_count': len(type_ids),
                'records_processed': len(all_results),
                's3_path': f"s3://{bucket_name}/{full_path}"
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing market order data: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
