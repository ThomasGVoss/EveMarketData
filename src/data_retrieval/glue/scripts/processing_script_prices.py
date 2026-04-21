import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, LongType
import boto3
import os
import logging

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

logger.info(f"Job parameters: bucket_name={bucket_name}")

# Set Spark configuration for better performance
spark.conf.set("spark.sql.adaptive.enabled", "true")
spark.conf.set("spark.sql.adaptive.coalescePartitions.enabled", "true")
spark.conf.set("spark.sql.broadcastTimeout", "7200")

# S3 client for metadata operations
s3_client = boto3.client('s3')

# Paths — processed files are moved to archive/ so the raw/ prefix always
# contains only unprocessed data, removing the need for a checkpoint.
raw_prefix = "raw/api-data/prices/"
archive_prefix = "archive/api-data/prices/"
processed_data_path = f"s3://{bucket_name}/processed/market_prices/"


def archive_source_files(bucket_name, source_keys):
    """Copy each source key to the archive prefix then delete the original.

    If a copy succeeds but the subsequent delete fails the job raises so
    that it fails fast.  On the next run the raw file is still present and
    will be reprocessed safely (parquet write uses overwrite mode).
    """
    for key in source_keys:
        archive_key = key.replace(raw_prefix, archive_prefix, 1)
        try:
            s3_client.copy_object(
                Bucket=bucket_name,
                CopySource={"Bucket": bucket_name, "Key": key},
                Key=archive_key,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to copy {key} to archive: {str(e)}") from e
        try:
            s3_client.delete_object(Bucket=bucket_name, Key=key)
            logger.info(f"Archived: {key} -> {archive_key}")
        except Exception as e:
            raise RuntimeError(
                f"Copied {key} to archive but failed to delete original: {str(e)}"
            ) from e


## -------------------- DATA DISCOVERY --------------------

# Collect individual file keys and the distinct hour-level folder paths.
paginator = s3_client.get_paginator('list_objects_v2')
source_keys = []
s3_folders = set()
try:
    for page in paginator.paginate(Bucket=bucket_name, Prefix=raw_prefix):
        for item in page.get('Contents', []):
            key = item['Key']
            folder_path = os.path.dirname(key)
            if 'hour=' in folder_path:
                source_keys.append(key)
                s3_folders.add(folder_path)
except Exception as e:
    logger.error(f"Error listing S3 objects: {str(e)}")
    job.commit()
    sys.exit(1)

if not source_keys:
    logger.info(f"No files found under s3://{bucket_name}/{raw_prefix}. Exiting.")
    job.commit()
    sys.exit(0)

logger.info(f"Found {len(source_keys)} file(s) in {len(s3_folders)} hour-level folder(s).")

## -------------------- DATA READING --------------------
# Read all raw files in a single Spark call and derive partition columns
# from each record's source path via input_file_name().

s3_paths = [f"s3://{bucket_name}/{f}" for f in sorted(s3_folders)]
df = spark.read.json(s3_paths)

# Expand nested arrays when the JSON wraps records in an "items" key.
if "items" in df.columns:
    df = df.select(
        F.input_file_name().alias("_src_path"),
        F.explode(F.col("items")).alias("item"),
    ).select("_src_path", "item.*")
else:
    df = df.withColumn("_src_path", F.input_file_name())

# Extract year / month / day / hour from the embedded file path.
path_pattern = r'raw/api-data/prices/year=(\d{4})/month=(\d{2})/day=(\d{2})/hour=(\d{2})'
df = (
    df
    .withColumn("year",  F.regexp_extract(F.col("_src_path"), path_pattern, 1))
    .withColumn("month", F.regexp_extract(F.col("_src_path"), path_pattern, 2))
    .withColumn("day",   F.regexp_extract(F.col("_src_path"), path_pattern, 3))
    .withColumn("hour",  F.regexp_extract(F.col("_src_path"), path_pattern, 4))
    .withColumn(
        "processed_timestamp",
        F.concat_ws(" ",
            F.concat_ws("-", F.col("year"), F.col("month"), F.col("day")),
            F.concat_ws(":", F.col("hour"), F.lit("00"), F.lit("00")),
        ),
    )
    .drop("_src_path")
)

## -------------------- CAST COLUMN TYPES --------------------

if "adjusted_price" in df.columns:
    if not isinstance(df.schema["adjusted_price"].dataType, DoubleType):
        df = df.withColumn("adjusted_price", F.col("adjusted_price").cast("double"))
if "average_price" in df.columns:
    if not isinstance(df.schema["average_price"].dataType, DoubleType):
        df = df.withColumn("average_price", F.col("average_price").cast("double"))
if "type_id" in df.columns:
    if not isinstance(df.schema["type_id"].dataType, LongType):
        df = df.withColumn("type_id", F.col("type_id").cast("long"))

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

## -------------------- ARCHIVE SOURCE FILES --------------------
# Move raw files to archive/ so only unprocessed files remain in raw/.

logger.info(f"Archiving {len(source_keys)} source file(s).")
archive_source_files(bucket_name, source_keys)
logger.info("Archiving complete.")

job.commit()