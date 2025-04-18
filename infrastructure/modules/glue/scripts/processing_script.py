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
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'database_name', 's3_bucket_name'])
job.init(args['JOB_NAME'], args)

# Set bucket and paths
bucket_name = args.get('s3_bucket_name')
database_name = args.get('database_name')

# Log the job parameters
logger.info(f"Job parameters: bucket_name={bucket_name}, database_name={database_name}")

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
        
        # If df is empty or has no rows, continue to next folder
        if folder_df.count() == 0:
            logger.info(f"No data found in {folder_path}, skipping")
            continue
            
        # Add timestamp and partition columns based on folder path
        folder_df = folder_df.withColumn("processed_timestamp", F.lit(date_info["timestamp"]))
        folder_df = folder_df.withColumn("year", F.lit(date_info["year"]))
        folder_df = folder_df.withColumn("month", F.lit(date_info["month"]))
        folder_df = folder_df.withColumn("day", F.lit(date_info["day"]))
        folder_df = folder_df.withColumn("hour", F.lit(date_info["hour"]))
        folder_df = folder_df.withColumn("source_path", F.lit(folder_path))
        
        # Log info about this folder's data
        logger.info(f"Folder {folder_path}: {folder_df.count()} rows with timestamp {date_info['timestamp']}")
        
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

# Log the combined dataframe info
logger.info(f"Combined dataframe has {df.count()} rows")

# If df has nested arrays (common when reading directly from JSON files)
if "items" in df.columns:
    logger.info("Found 'items' column in data, exploding nested array")
    # Assume items is an array column containing the market data records
    nested_df = df.select(
        "processed_timestamp", "year", "month", "day", "hour", "source_path",
        F.explode(F.col("items")).alias("item")
    )
    df = nested_df.select("processed_timestamp", "year", "month", "day", "hour", "source_path", "item.*")
    # Recount after explosion
    count = df.count()
    logger.info(f"After exploding arrays: {count} records")


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

logger.info(f"Processing complete. Data written to {processed_data_path}")

# -------------------- START OF AGGREGATION SECTION --------------------
logger.info("Starting aggregation across multiple days for plotting")

try:
    # Read all processed parquet files from the processed directory
    logger.info(f"Reading processed parquet files from {processed_data_path}")
    
    # Create dynamic frame from processed data path
    dynamic_frame = glueContext.create_dynamic_frame.from_options(
        connection_type="s3",
        connection_options={"paths": [processed_data_path], "recurse": True},
        format="parquet"
    )
    
    # Convert to Spark DataFrame for easier manipulation
    aggregation_df = dynamic_frame.toDF()
    
    # Check if the dataframe is empty
    if aggregation_df.count() == 0:
        logger.info("No data found for aggregation. Skipping aggregation step.")
    else:
        # Log the count and schema of the aggregation dataframe
        logger.info(f"Read {aggregation_df.count()} records for aggregation")
        logger.info(f"Aggregation DataFrame Schema: {aggregation_df.schema}")
        
        # Convert processed_timestamp to timestamp type if it's a string
        if "processed_timestamp" in aggregation_df.columns:
            aggregation_df = aggregation_df.withColumn(
                "processed_timestamp", 
                F.to_timestamp("processed_timestamp")
            )
        
        # Extract date from timestamp for daily aggregation
        aggregation_df = aggregation_df.withColumn(
            "date", 
            F.to_date("processed_timestamp")
        )
        
        # Aggregate by type_id and date
        # Assuming type_id identifies the product and we want daily price trends
        if "type_id" in aggregation_df.columns and "adjusted_price" in aggregation_df.columns:
            logger.info("Performing aggregation by type_id and date")
            
            # Daily aggregation
            daily_agg_df = aggregation_df.groupBy("type_id", "date").agg(
                F.avg("adjusted_price").alias("avg_daily_price"),
                F.min("adjusted_price").alias("min_daily_price"),
                F.max("adjusted_price").alias("max_daily_price"),
                F.count("*").alias("record_count")
            )
            
            # Log counts
            logger.info(f"Aggregated to {daily_agg_df.count()} daily records")
            
            # Combine original data with aggregated data
            logger.info("Combining original data with aggregated data")
            combined_df = aggregation_df.join(
                daily_agg_df,
                on=["type_id", "date"],
                how="left"
            )
            
            # Write the combined data to a new location
            logger.info(f"Writing combined data to {aggregated_data_path}")
            
            # Convert to dynamic frame for writing
            combined_dynamic_frame = DynamicFrame.fromDF(combined_df, glueContext, "combined_dynamic_frame")
            
            # Write to S3
            glueContext.write_dynamic_frame.from_options(
                frame=combined_dynamic_frame,
                connection_type="s3",
                connection_options={"path": aggregated_data_path, "partitionKeys": []},
                format="parquet"
            )
            
            logger.info(f"Aggregation complete. Combined data written to {aggregated_data_path}")
        else:
            logger.warning("Required columns (type_id or adjusted_price) not found. Skipping aggregation.")
            
except Exception as e:
    logger.error(f"Error during aggregation process: {str(e)}")
    # Continue with job instead of exiting, so the primary functionality is not affected
    logger.info("Continuing with job despite aggregation error")


# End the job
job.commit()