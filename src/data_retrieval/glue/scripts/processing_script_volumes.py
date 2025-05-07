import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
import boto3
import logging
import json
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize Glue context
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)

# Get job parameters
args = getResolvedOptions(sys.argv, ['JOB_NAME', 's3_bucket_name'])
job.init(args['JOB_NAME'], args)

# Set bucket and paths
bucket_name = args.get('s3_bucket_name')


# Set Spark configuration for better performance
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.broadcastTimeout", "7200")

# Define paths
raw_data_path = f"s3://{bucket_name}/raw/api-data/orders/"
processed_data_path = f"s3://{bucket_name}/processed/order_volumes/"
aggregated_data_path = f"s3://{bucket_name}/aggregated/order_volumes/"

# S3 client for metadata operations
s3_client = boto3.client('s3')

# Function to save checkpoint
def save_checkpoint(bucket_name, checkpoint_path, last_partition):
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=checkpoint_path,
            Body=json.dumps(last_partition)
        )
        logger.info(f"Checkpoint saved: {last_partition}")
    except Exception as e:
        logger.error(f"Failed to save checkpoint: {str(e)}")

# Function to read checkpoint
def read_checkpoint(bucket_name, checkpoint_path):
    try:
        response = s3_client.get_object(Bucket=bucket_name, Key=checkpoint_path)
        checkpoint = json.loads(response['Body'].read().decode('utf-8'))
        logger.info(f"Checkpoint loaded: {checkpoint}")
        return checkpoint
    except s3_client.exceptions.NoSuchKey:
        logger.info("No checkpoint found. Starting from the beginning.")
        return None
    except Exception as e:
        logger.error(f"Failed to read checkpoint: {str(e)}")
        return None


# Read the checkpoint
last_partition = read_checkpoint(bucket_name, "checkpoints/order_volumes_checkpoint.json")

# Check if source data exists
try:
    response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix="raw/api-data/orders/")
    if 'Contents' not in response or len(response['Contents']) == 0:
        logger.info(f"No files found in {raw_data_path}. Exiting.")
        job.commit()
        sys.exit(1)
    logger.info(f"Found {len(response['Contents'])} files to process.")
except Exception as e:
    logger.error(f"Error checking for files: {str(e)}")
    job.commit()
    sys.exit(1)

# Read raw data
try:
    df = spark.read.json(raw_data_path)
    logger.info(f"Loaded raw data with {df.count()} rows.")

except Exception as e:
    logger.error(f"Error reading raw data: {str(e)}")
    job.commit()
    sys.exit(1)

# Write processed data
try:
    df.write.mode("overwrite").partitionBy("year", "month", "day", "hour").parquet(processed_data_path)
    logger.info(f"Processed data written to {processed_data_path}.")
except Exception as e:
    logger.error(f"Error writing processed data: {str(e)}")
    job.commit()
    sys.exit(1)

# Save checkpoint
last_processed_partition = {
    "year": max(df.select("year").distinct().rdd.flatMap(lambda x: x).collect()),
    "month": max(df.select("month").distinct().rdd.flatMap(lambda x: x).collect()),
    "day": max(df.select("day").distinct().rdd.flatMap(lambda x: x).collect()),
    "hour": max(df.select("hour").distinct().rdd.flatMap(lambda x: x).collect())
}
save_checkpoint(bucket_name, "checkpoints/order_volumes_checkpoint.json", last_processed_partition)

# Commit the job
job.commit()