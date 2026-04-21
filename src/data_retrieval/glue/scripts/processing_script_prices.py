import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
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
raw_prefix = "raw/api-data/prices/"
processed_data_path = f"s3://{bucket_name}/processed/market_prices/"

# Checkpoint tracks the last fully processed day (year/month/day)
checkpoint_path = "checkpoints/last_processed_partition.json"


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


def extract_date_from_path(path):
    """Extract year/month/day/hour from a hive-partitioned S3 folder path."""
    pattern = r'raw/api-data/prices/year=(\d{4})/month=(\d{2})/day=(\d{2})/hour=(\d{2})'
    match = re.search(pattern, path)
    if match:
        year, month, day, hour = match.groups()
        return {
            "timestamp": f"{year}-{month}-{day} {hour}:00:00",
            "year": year,
            "month": month,
            "day": day,
            "hour": hour,
        }
    logger.error(f"Could not extract date components from path: {path}")
    now = datetime.datetime.utcnow()
    return {
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
        "year": now.strftime('%Y'),
        "month": now.strftime('%m'),
        "day": now.strftime('%d'),
        "hour": now.strftime('%H'),
    }


## -------------------- DATA DISCOVERY --------------------

# Paginate through all objects in the raw prefix
paginator = s3_client.get_paginator('list_objects_v2')
s3_folders = set()
try:
    for page in paginator.paginate(Bucket=bucket_name, Prefix=raw_prefix):
        for item in page.get('Contents', []):
            folder_path = os.path.dirname(item['Key'])
            if 'hour=' in folder_path:
                s3_folders.add(folder_path)
except Exception as e:
    logger.error(f"Error listing S3 objects: {str(e)}")
    job.commit()
    sys.exit(1)

if not s3_folders:
    logger.info(f"No files found under s3://{bucket_name}/{raw_prefix}. Exiting.")
    job.commit()
    sys.exit(0)

logger.info(f"Found {len(s3_folders)} distinct hour-level folders.")

# Filter folders that are newer than the checkpoint (day-level)
last_partition = read_checkpoint(bucket_name, checkpoint_path)
if last_partition:
    checkpoint_day = (
        f"raw/api-data/prices/year={last_partition['year']}"
        f"/month={last_partition['month']}/day={last_partition['day']}"
    )
    logger.info(f"Skipping folders up to day: {checkpoint_day}")
    s3_folders = [f for f in s3_folders if f > checkpoint_day]

if not s3_folders:
    logger.info("No new folders to process since last checkpoint. Exiting.")
    job.commit()
    sys.exit(0)

## -------------------- DATA READING --------------------

dataframes = []
for folder_path in sorted(s3_folders):
    full_path = f"s3://{bucket_name}/{folder_path}"
    logger.info(f"Processing folder: {folder_path}")
    date_info = extract_date_from_path(folder_path)
    try:
        folder_df = spark.read.json(full_path)
        folder_df = folder_df.withColumn("processed_timestamp", F.lit(date_info["timestamp"]))
        folder_df = folder_df.withColumn("year",  F.lit(date_info["year"]))
        folder_df = folder_df.withColumn("month", F.lit(date_info["month"]))
        folder_df = folder_df.withColumn("day",   F.lit(date_info["day"]))
        folder_df = folder_df.withColumn("hour",  F.lit(date_info["hour"]))
        dataframes.append(folder_df)
    except Exception as e:
        logger.error(f"Error processing folder {folder_path}: {str(e)}")
        continue

if not dataframes:
    logger.error("No valid data found in any folder. Exiting.")
    job.commit()
    sys.exit(1)

# Union all hour-level dataframes
df = dataframes[0]
for additional_df in dataframes[1:]:
    df = df.unionByName(additional_df, allowMissingColumns=True)

# Expand nested arrays when the JSON file wraps records in an "items" key
if "items" in df.columns:
    df = df.select(
        "processed_timestamp", "year", "month", "day", "hour",
        F.explode(F.col("items")).alias("item")
    ).select("processed_timestamp", "year", "month", "day", "hour", "item.*")

## -------------------- CAST COLUMN TYPES --------------------

if "adjusted_price" in df.columns:
    if not str(df.schema["adjusted_price"].dataType).startswith("DoubleType"):
        df = df.withColumn("adjusted_price", F.col("adjusted_price").cast("double"))
if "average_price" in df.columns:
    if not str(df.schema["average_price"].dataType).startswith("DoubleType"):
        df = df.withColumn("average_price", F.col("average_price").cast("double"))
if "type_id" in df.columns:
    if not str(df.schema["type_id"].dataType).startswith("LongType"):
        df = df.withColumn("type_id", F.col("type_id").cast("long"))

## -------------------- WRITE ONE PARQUET FILE PER DAY --------------------
# Repartition so that each day lands in exactly one Parquet file, then
# write with Hive-style partitioning by year/month/day.

logger.info(f"Writing daily parquet files to {processed_data_path}")
(
    df
    .repartition(F.col("year"), F.col("month"), F.col("day"))
    .write
    .mode("overwrite")
    .partitionBy("year", "month", "day")
    .parquet(processed_data_path)
)
logger.info("Write complete.")

## -------------------- CHECKPOINT --------------------

last_processed_partition = {
    "year":  max(df.select("year").distinct().rdd.flatMap(lambda x: x).collect()),
    "month": max(df.select("month").distinct().rdd.flatMap(lambda x: x).collect()),
    "day":   max(df.select("day").distinct().rdd.flatMap(lambda x: x).collect()),
}
save_checkpoint(bucket_name, checkpoint_path, last_processed_partition)

job.commit()