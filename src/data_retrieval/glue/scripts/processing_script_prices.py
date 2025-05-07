import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, LongType, TimestampType
import datetime
import boto3
import os
import json
import logging
import re

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

# Log the job parameters
logger.info(f"Job parameters: bucket_name={bucket_name}")

# Set Spark configuration for better performance
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.broadcastTimeout", "7200")

# S3 client for metadata operations
s3_client = boto3.client('s3')

# Raw data path prefix and processed data path
raw_data_path = f"s3://{bucket_name}/raw/api-data/prices/"
processed_data_path = f"s3://{bucket_name}/processed/market_prices/"
# New path for aggregated data
aggregated_data_path = f"s3://{bucket_name}/aggregated/market_prices/"

# Define the checkpoint path in S3
checkpoint_path = "checkpoints/last_processed_partition.json"

# Save the last processed partition
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

# Read the last processed partition from the checkpoint
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

## -------------------- START OF DATA PROCESSING SECTION --------------------

# Check if source data exists
try:
    # List objects to verify there's data to process
    response = s3_client.list_objects_v2(
        Bucket=bucket_name,
        Prefix="raw/api-data/prices/"
    )
    
    if 'Contents' not in response or len(response['Contents']) == 0:
        logger.info(f"No files found in {raw_data_path}. Exiting.")
        job.commit()
        sys.exit(1)
        
    file_count = len(response['Contents'])
    logger.info(f"Found {file_count} files to process in the raw data path")
    
    # Extract all folder paths to analyze the structure
    s3_folders = set()
    for item in response['Contents']:
        key = item['Key']
        # Get the directory path up to the hour level
        folder_path = os.path.dirname(key)
        # Only add if it contains hour= to get the most specific path
        if 'hour=' in folder_path:
            s3_folders.add(folder_path)
    
    logger.info(f"Found {len(s3_folders)} distinct folder paths: {list(s3_folders)[:5]}...")
    
except Exception as e:
    logger.error(f"Error checking for files: {str(e)}")
    job.commit()
    sys.exit(1)

# Read the checkpoint
last_partition = read_checkpoint(bucket_name, checkpoint_path)

# Filter folders based on the checkpoint
if last_partition:
    logger.info(f"Filtering folders starting from partition: {last_partition}")
    s3_folders = [
        folder for folder in s3_folders
        if folder >= f"raw/api-data/prices/year={last_partition['year']}/month={last_partition['month']}/day={last_partition['day']}/hour={last_partition['hour']}"
    ]
else:
    logger.info("Processing all folders as no checkpoint exists.")

# Function to extract date from path with the specific format
def extract_date_from_path(path):
    # Expected format: raw/api-data/prices/year=YYYY/month=MM/day=DD/hour=HH/
    pattern = r'raw/api-data/prices/year=(\d{4})/month=(\d{2})/day=(\d{2})/hour=(\d{2})'
    match = re.search(pattern, path)
    
    if match:
        year = match.group(1)
        month = match.group(2)
        day = match.group(3)
        hour = match.group(4)
        
        # Create timestamp string
        timestamp_str = f"{year}-{month}-{day} {hour}:00:00"
        return {
            "timestamp": timestamp_str,
            "year": year,
            "month": month,
            "day": day,
            "hour": hour
        }
    else:
        # Log error if pattern doesn't match
        logger.error(f"Could not extract date components from path: {path}")
        # Default to current time
        now = datetime.datetime.utcnow()
        return {
            "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
            "year": now.strftime('%Y'),
            "month": now.strftime('%m'),
            "day": now.strftime('%d'),
            "hour": now.strftime('%H')
        }

# Read the files and track their source paths
logger.info(f"Reading files from S3 while preserving source paths")

# Create a list to store dataframes with their source information
dataframes = []

# Process each folder separately to extract timestamps
for folder_path in s3_folders:
    full_path = f"s3://{bucket_name}/{folder_path}"
    logger.info(f"Processing folder: {folder_path}")
    
    # Extract date components from path
    date_info = extract_date_from_path(folder_path)
    
    try:
        # Read data from this specific folder
        folder_df = spark.read.json(full_path)
                   
        # Add timestamp and partition columns based on folder path
        folder_df = folder_df.withColumn("processed_timestamp", F.lit(date_info["timestamp"]))
        folder_df = folder_df.withColumn("year", F.lit(date_info["year"]))
        folder_df = folder_df.withColumn("month", F.lit(date_info["month"]))
        folder_df = folder_df.withColumn("day", F.lit(date_info["day"]))
        folder_df = folder_df.withColumn("hour", F.lit(date_info["hour"]))
        folder_df = folder_df.withColumn("source_path", F.lit(folder_path))
        
        # Add this dataframe to our list
        dataframes.append(folder_df)
        
    except Exception as e:
        logger.error(f"Error processing folder {folder_path}: {str(e)}")
        continue

# If we have no valid dataframes, exit
if not dataframes:
    logger.error("No valid data found in any folders. Exiting.")
    job.commit()
    sys.exit(1)

# Union all the dataframes together
df = dataframes[0]
for additional_df in dataframes[1:]:
    df = df.unionByName(additional_df, allowMissingColumns=True)

# If df has nested arrays (common when reading directly from JSON files)
if "items" in df.columns:
    # Assume items is an array column containing the market data records
    nested_df = df.select(
        "processed_timestamp", "year", "month", "day", "hour", "source_path",
        F.explode(F.col("items")).alias("item")
    )
    df = nested_df.select("processed_timestamp", "year", "month", "day", "hour", "source_path", "item.*")

# Check data types for adjusted_price, average_price, and type_id
logger.info("Checking data types of critical columns:")
df_types = {field.name: field.dataType for field in df.schema.fields}
logger.info(f"Data types: {df_types}")

# Make sure columns are of correct type
if "adjusted_price" in df.columns:
    if not str(df.schema["adjusted_price"].dataType).startswith("DoubleType"):
        df = df.withColumn("adjusted_price", F.col("adjusted_price").cast("double"))
if "average_price" in df.columns:
    if not str(df.schema["average_price"].dataType).startswith("DoubleType"):
        df = df.withColumn("average_price", F.col("average_price").cast("double"))
if "type_id" in df.columns:
    if not str(df.schema["type_id"].dataType).startswith("LongType"):
        df = df.withColumn("type_id", F.col("type_id").cast("long"))

# Write to processed location with partitioning
logger.info(f"Writing processed data to {processed_data_path}")
df.write.mode("overwrite").partitionBy("year", "month", "day", "hour").parquet(processed_data_path)

# Determine the last processed partition
last_processed_partition = {
    "year": max(df.select("year").distinct().rdd.flatMap(lambda x: x).collect()),
    "month": max(df.select("month").distinct().rdd.flatMap(lambda x: x).collect()),
    "day": max(df.select("day").distinct().rdd.flatMap(lambda x: x).collect()),
    "hour": max(df.select("hour").distinct().rdd.flatMap(lambda x: x).collect())
}

# Save the checkpoint
save_checkpoint(bucket_name, checkpoint_path, last_processed_partition)

# End the job
job.commit()