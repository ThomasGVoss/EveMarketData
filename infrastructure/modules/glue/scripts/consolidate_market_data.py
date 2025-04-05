import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from awsglue.dynamicframe import DynamicFrame
from pyspark.sql import functions as F

# Argumente aus dem Job abrufen
args = getResolvedOptions(sys.argv, ['JOB_NAME', 'database_name', 'output_path'])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args['JOB_NAME'], args)

database_name = args['database_name']
output_path = args['output_path']

try:
    prices_data = glueContext.create_dynamic_frame.from_catalog(
        database=database_name,
        table_name="prices"  
    )
    
    prices_df = prices_data.toDF()
    prices_transformed = prices_df.select(
        F.col("type_id").alias("item_id"),
        F.lit(None).cast("int").alias("region_id"),
        F.current_timestamp().alias("timestamp"),
        F.lit(None).cast("boolean").alias("is_buy_order"),
        F.col("adjusted_price").alias("min_price"),
        F.col("average_price").alias("mean_price"),
        F.col("adjusted_price").alias("max_price"),
        F.lit(None).cast("int").alias("order_count"),
        F.lit(None).cast("int").alias("volume"),
        F.lit("prices").alias("source"),
        F.col("year"),
        F.col("month"),
        F.col("day"),
        F.col("hour")
    )
    
    has_prices = True
except Exception as e:
    print(f"Error: {str(e)}")
    has_prices = False


try:
    orders_data = glueContext.create_dynamic_frame.from_catalog(
        database=database_name,
        table_name="orders" 
    )
    
    orders_df = orders_data.toDF()
    orders_transformed = orders_df.select(
        F.col("typeId").alias("item_id"),
        F.col("regionId").alias("region_id"),
        F.col("generated").cast("timestamp").alias("timestamp"),
        F.col("isBuyOrder").alias("is_buy_order"),
        F.col("minPrice").alias("min_price"),
        F.col("meanPrice").alias("mean_price"),
        F.col("maxPrice").alias("max_price"),
        F.col("orderCount").alias("order_count"),
        F.lit(None).cast("int").alias("volume"),
        F.lit("orders").alias("source"),
        F.col("year"),
        F.col("month"),
        F.col("day"),
        F.col("hour")
    )
    
    has_orders = True
except Exception as e:
    print(f"Error: {str(e)}")
    has_orders = False

if has_prices and has_orders:
    consolidated_df = prices_transformed.unionByName(orders_transformed)
elif has_prices:
    consolidated_df = prices_transformed
elif has_orders:
    consolidated_df = orders_transformed
else:
    print("No data found. Job will be terminated.")
    job.commit()
    sys.exit(0)


consolidated_df = consolidated_df.dropDuplicates(["item_id", "region_id", "timestamp", "is_buy_order", "source"])
consolidated_df = consolidated_df.filter(F.col("min_price").isNotNull())

consolidated_dynamic_frame = DynamicFrame.fromDF(consolidated_df, glueContext, "consolidated_data")

glueContext.write_dynamic_frame.from_options(
    frame=consolidated_dynamic_frame,
    connection_type="s3",
    connection_options={
        "path": output_path,
        "partitionKeys": ["year", "month", "day"]
    },
    format="parquet",
    transformation_ctx="write_consolidated"
)

job.commit()
