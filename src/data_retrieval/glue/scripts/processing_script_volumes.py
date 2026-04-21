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

# Set Spark configuration for better performance
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.broadcastTimeout", "7200")

# Define paths
raw_prefix = "raw/api-data/orders/"
processed_data_path = f"s3://{bucket_name}/processed/order_volumes/"

# S3 client for metadata operations
s3_client = boto3.client('s3')

# Checkpoint tracks the last fully processed day (year/month/day).
# Using >= in the filter means the checkpoint day is always reprocessed,
# picking up any new hourly files that arrived since the last run.
checkpoint_path = "checkpoints/order_volumes_checkpoint.json"


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


## -------------------- DATA DISCOVERY --------------------

# Paginate through all objects in the raw prefix to find hour-level folders.
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

# Filter to folders on or after the checkpoint day so that partially-processed
# days (i.e. when a second hourly run lands) are always picked up.
last_partition = read_checkpoint(bucket_name, checkpoint_path)
if last_partition:
    checkpoint_day = (
        f"raw/api-data/orders/year={last_partition['year']}"
        f"/month={last_partition['month']}/day={last_partition['day']}"
    )
    logger.info(f"Including folders from checkpoint day onwards: {checkpoint_day}")
    s3_folders = [f for f in s3_folders if f >= checkpoint_day]

if not s3_folders:
    logger.info("No new folders to process since last checkpoint. Exiting.")
    job.commit()
    sys.exit(0)

## -------------------- DATA READING --------------------
# Read all qualifying folders in a single Spark call, then derive partition
# columns from the source file path using input_file_name().  This avoids
# building a deeply-nested union tree when many hour-level folders are present.

s3_paths = [f"s3://{bucket_name}/{f}" for f in sorted(s3_folders)]
logger.info(f"Reading {len(s3_paths)} folder(s) from S3.")

df = spark.read.json(s3_paths)

# Extract year / month / day / hour from the file path embedded in each record.
path_pattern = r'raw/api-data/orders/year=(\d{4})/month=(\d{2})/day=(\d{2})/hour=(\d{2})'
df = (
    df
    .withColumn("_src_path", F.input_file_name())
    .withColumn("year",  F.regexp_extract(F.col("_src_path"), path_pattern, 1))
    .withColumn("month", F.regexp_extract(F.col("_src_path"), path_pattern, 2))
    .withColumn("day",   F.regexp_extract(F.col("_src_path"), path_pattern, 3))
    .withColumn("hour",  F.regexp_extract(F.col("_src_path"), path_pattern, 4))
    .withColumn(
        "processed_timestamp",
        F.concat_ws(" ",
            F.concat_ws("-", F.col("year"), F.col("month"), F.col("day")),
            F.concat_ws(":", F.col("hour"), F.lit("00"), F.lit("00"))
        )
    )
    .drop("_src_path")
)

logger.info(f"Loaded {df.count()} rows from raw data.")

## -------------------- WRITE ONE PARQUET FILE PER DAY --------------------
# repartition() by the day-level columns ensures a single output file per day.

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