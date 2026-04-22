import sys
import argparse
import json
import re
import boto3
import os
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pyarrow.fs import S3FileSystem

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Parse job parameters
parser = argparse.ArgumentParser()
parser.add_argument('--s3_bucket_name', required=True)
args, _ = parser.parse_known_args()
bucket_name = args.s3_bucket_name

# S3 client for metadata operations
s3_client = boto3.client('s3')

# Paths — processed files are moved to archive/ so the raw/ prefix always
# contains only unprocessed data, removing the need for a checkpoint.
raw_prefix = "raw/api-data/orders/"
archive_prefix = "archive/api-data/orders/"
processed_data_path = f"s3://{bucket_name}/processed/order_volumes/"


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
    sys.exit(1)

if not source_keys:
    logger.info(f"No files found under s3://{bucket_name}/{raw_prefix}. Exiting.")
    sys.exit(0)

logger.info(f"Found {len(source_keys)} file(s) in {len(s3_folders)} hour-level folder(s).")

## -------------------- DATA READING --------------------
# Download each raw file via boto3 and load into pandas DataFrames.

path_pattern = re.compile(
    r'raw/api-data/orders/year=(\d{4})/month=(\d{2})/day=(\d{2})/hour=(\d{2})'
)

frames = []
for key in sorted(source_keys):
    match = path_pattern.search(key)
    if not match:
        logger.warning(f"Skipping key with unexpected path format: {key}")
        continue
    year, month, day, hour = match.groups()

    response = s3_client.get_object(Bucket=bucket_name, Key=key)
    payload = json.loads(response['Body'].read().decode('utf-8'))

    if isinstance(payload, list):
        records = payload
    elif "items" in payload:
        records = payload["items"]
    else:
        logger.warning(f"Unexpected payload structure for key {key}: dict without 'items'")
        records = [payload]
    frame = pd.json_normalize(records)
    frame["year"] = year
    frame["month"] = month
    frame["day"] = day
    frame["hour"] = hour
    frame["processed_timestamp"] = f"{year}-{month}-{day} {hour}:00:00"
    frames.append(frame)

df = pd.concat(frames, ignore_index=True)

## -------------------- WRITE ONE PARQUET FILE PER DAY --------------------
# pyarrow write_to_dataset writes Hive-style partitioned parquet directly to S3.

logger.info(f"Writing daily parquet files to {processed_data_path}")
table = pa.Table.from_pandas(df, preserve_index=False)
fs = S3FileSystem()
output_path = f"{bucket_name}/processed/order_volumes"
pq.write_to_dataset(
    table,
    root_path=output_path,
    partition_cols=["year", "month", "day"],
    existing_data_behavior="overwrite_or_ignore",
    filesystem=fs,
)
logger.info("Write complete.")

## -------------------- ARCHIVE SOURCE FILES --------------------
# Move raw files to archive/ so only unprocessed files remain in raw/.

logger.info(f"Archiving {len(source_keys)} source file(s).")
archive_source_files(bucket_name, source_keys)
logger.info("Archiving complete.")
