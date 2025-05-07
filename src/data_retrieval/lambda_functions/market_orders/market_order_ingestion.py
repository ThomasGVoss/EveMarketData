import json
import urllib3
import boto3
import os
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize an HTTP connection pool
http = urllib3.PoolManager()

def retrieve_type_ids_by_region(region_ids): 
    type_ids_for_region = {}

    for region, region_id in region_ids.items():
        print(f"Region: {region} ({region_id})")
        
        all_type_ids = []
        base_api_path = f"https://esi.evetech.net/dev/markets/{region_id}/types/"
        params = {
            "datasource": "tranquility",
            "page": 1,
        }
        
        while True:
            # Build the URL with query parameters
            url = f"{base_api_path}?{urllib3.request.urlencode(params)}"

            # Make the GET request for the current page
            response = http.request("GET", url)
            
            if response.status == 200:
                data = json.loads(response.data.decode("utf-8"))
                all_type_ids.extend(data)
                params["page"] += 1  # Increment the page number
                
                if params["page"] == 2:  # Example condition to stop early
                    break        
            else:
                # logger.error(f"Failed to fetch data for region {region_id} on page {params["page"]}. Status code: {response.status}")
                break

        # Add the type_ids to the dictionary with the region name as the key
        type_ids_for_region[region_id] = all_type_ids

    return type_ids_for_region

def retrieve_market_orders(type_ids_for_region):
    params = {
        "datasource": "tranquility",
        "order_type": "all",
        "type_id": 2369, 
        "page": 1
    }

    all_orders = []
    count = 1
    for region_id, type_ids in type_ids_for_region.items():
        base_api_path = f"https://esi.evetech.net/dev/markets/{region_id}/orders/"
        
        for type_id in type_ids:
            print(f"Retrieving items for Type ID: {type_id}, which is {count} out of {len(type_ids)}")
            params["type_id"] = type_id  # Update the type_id parameter for the request
            params["page"] = 1  # Reset the page number for each new type_id

            while True:
                # Build the URL with query parameters
                url = f"{base_api_path}?{urllib3.request.urlencode(params)}"

                # Make the GET request for the current page
                response = http.request("GET", url)
                
                if response.status == 200:
                    data = json.loads(response.data.decode("utf-8"))
                    if not data:  # If the response is empty, break the loop
                        break
                    all_orders.extend(data)  # Append the data to the list
                    params["page"] += 1  # Increment the page number
                else:
                    logger.warning(f"Failed to fetch data at page {params['page']}. Status code for parameters {params}: {response.status}")
                    break
            
            count += 1  # Increment the count for the next type_id

    return all_orders

def lambda_handler(event, context):
    try:
        # Check if region_name and region_id are provided in the event
        region_name = event.get('region_name')
        region_id = event.get('region_id')

        # If no parameters are passed, use default regions
        if not region_name or not region_id:
            logger.info("No region parameters provided. Using default regions.")
            region_ids = {
                "The Forge": 10000002,
                "Sinq Laison": 10000032,
                "Domain": 10000043,
                "Heimatar": 10000030
            }

            # Trigger the same Lambda for each region
            lambda_client = boto3.client('lambda')
            for region_name, region_id in region_ids.items():
                logger.info(f"Triggering Lambda for region: {region_name} (ID: {region_id})")
                lambda_client.invoke(
                    FunctionName=context.invoked_function_arn,  # Invoke the same Lambda
                    InvocationType='Event',  # Asynchronous invocation
                    Payload=json.dumps({
                        'region_name': region_name,
                        'region_id': region_id
                    })
                )
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': "Triggered Lambda for all default regions."
                })
            }

        # If parameters are provided, process the specific region
        logger.info(f"Processing region: {region_name} (ID: {region_id})")

        # Get current timestamp for S3 path
        now = datetime.utcnow()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        year = now.strftime('%Y')
        month = now.strftime('%m')
        day = now.strftime('%d')
        hour = now.strftime('%H')

        # Retrieve type IDs for the specified region
        type_ids_for_region = retrieve_type_ids_by_region({region_name: region_id})

        # Retrieve market orders for the specified region
        all_orders = retrieve_market_orders(type_ids_for_region)

        if not all_orders:
            raise Exception("No valid market order data was retrieved")

        # Define S3 path
        s3_path = f"raw/api-data/orders/year={year}/month={month}/day={day}/hour={hour}/"
        file_name = f"order_data_{timestamp}_{region_id}.json"
        full_path = s3_path + file_name

        # Initialize S3 client
        s3_client = boto3.client('s3')

        # Get bucket name from environment variable
        bucket_name = os.environ.get('S3_BUCKET_NAME')

        # Upload to S3
        s3_client.put_object(
            Bucket=bucket_name,
            Key=full_path,
            Body=json.dumps(all_orders),
            ContentType='application/json'
        )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Market order data ingestion successful for region: {region_name}",
                'timestamp': timestamp
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
