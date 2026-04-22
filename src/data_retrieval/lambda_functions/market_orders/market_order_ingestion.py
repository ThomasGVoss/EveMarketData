import json
import urllib3
import boto3
import os
from datetime import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Module-level clients are reused across warm Lambda invocations
http = urllib3.PoolManager()
s3_client = boto3.client('s3')


def retrieve_market_orders(region_id):
    """Fetch all orders for a region using the region-level orders endpoint.

    Uses the X-Pages response header to determine total page count so we
    make exactly the right number of requests with no wasted empty-page call.
    """
    base_url = f"https://esi.evetech.net/latest/markets/{region_id}/orders/"
    params = {
        "datasource": "tranquility",
        "order_type": "all",
        "page": 1,
    }

    all_orders = []

    # Fetch page 1 to discover X-Pages, then fetch remaining pages
    url = f"{base_url}?{urllib3.request.urlencode(params)}"
    response = http.request("GET", url)

    if response.status != 200:
        raise Exception(
            f"Failed to fetch orders for region {region_id} page 1. "
            f"Status: {response.status}"
        )

    all_orders.extend(json.loads(response.data.decode("utf-8")))
    total_pages = int(response.headers.get("X-Pages", 1))
    logger.info(f"Region {region_id}: {total_pages} page(s) of orders to fetch.")

    for page in range(2, total_pages + 1):
        params["page"] = page
        url = f"{base_url}?{urllib3.request.urlencode(params)}"
        response = http.request("GET", url)

        if response.status != 200:
            logger.warning(
                f"Failed to fetch orders for region {region_id} page {page}. "
                f"Status: {response.status} — skipping remaining pages."
            )
            break

        all_orders.extend(json.loads(response.data.decode("utf-8")))

    return all_orders


def lambda_handler(event, context):
    try:
        # Check if region_name and region_id are provided in the event
        region_name = event.get('region_name')
        region_id = event.get('region_id')

        # If no parameters are passed, fan out one invocation per default region
        if not region_name or not region_id:
            logger.info("No region parameters provided. Using default regions.")
            region_ids = {
                "The Forge": 10000002,
                "Sinq Laison": 10000032,
                "Domain": 10000043,
                "Heimatar": 10000030,
            }

            lambda_client = boto3.client('lambda')
            for region_name, region_id in region_ids.items():
                logger.info(f"Triggering Lambda for region: {region_name} (ID: {region_id})")
                lambda_client.invoke(
                    FunctionName=context.invoked_function_arn,
                    InvocationType='Event',
                    Payload=json.dumps({
                        'region_name': region_name,
                        'region_id': region_id,
                    })
                )
            return {
                'statusCode': 200,
                'body': json.dumps({'message': "Triggered Lambda for all default regions."})
            }

        # Process the specific region
        logger.info(f"Processing region: {region_name} (ID: {region_id})")

        all_orders = retrieve_market_orders(region_id)

        if not all_orders:
            raise Exception("No valid market order data was retrieved")

        logger.info(f"Retrieved {len(all_orders)} orders for region {region_name}.")

        # Build S3 path
        now = datetime.utcnow()
        timestamp = now.strftime('%Y%m%d_%H%M%S')
        s3_path = (
            f"raw/api-data/orders/"
            f"year={now.strftime('%Y')}/"
            f"month={now.strftime('%m')}/"
            f"day={now.strftime('%d')}/"
            f"hour={now.strftime('%H')}/"
        )
        full_path = s3_path + f"order_data_{timestamp}_{region_id}.json"

        bucket_name = os.environ.get('S3_BUCKET_NAME')
        s3_client.put_object(
            Bucket=bucket_name,
            Key=full_path,
            Body=json.dumps(all_orders),
            ContentType='application/json',
        )

        logger.info(f"Saved orders to s3://{bucket_name}/{full_path}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f"Market order data ingestion successful for region: {region_name}",
                'timestamp': timestamp,
                'order_count': len(all_orders),
            })
        }

    except Exception as e:
        logger.error(f"Error processing market order data: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
