# infrastructure/modules/glue/main.tf
###########################
# Glue Database
###########################
resource "aws_glue_catalog_database" "market_data_database" {
  name        = "market_data_${var.environment}"
  description = "Database for EVE Online market data analysis"
}

###########################
# Glue Crawlers
###########################

# Crawler for Market Prices
resource "aws_glue_crawler" "market_prices_crawler" {
  name          = "market-prices-crawler-${var.environment}"
  database_name = aws_glue_catalog_database.market_data_database.name
  role          = aws_iam_role.glue_role.arn
  schedule      = var.crawler_schedule

  s3_target {
    path = "s3://${var.s3_bucket_name}/raw/api-data/prices/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
    Grouping = { TableGroupingPolicy = "CombineCompatibleSchemas" }
  })

  tags = var.tags
}

# Crawler for Market Orders
resource "aws_glue_crawler" "market_orders_crawler" {
  name          = "market-orders-crawler-${var.environment}"
  database_name = aws_glue_catalog_database.market_data_database.name
  role          = aws_iam_role.glue_role.arn
  schedule      = var.crawler_schedule

  s3_target {
    path = "s3://${var.s3_bucket_name}/raw/api-data/orders/"
  }

  schema_change_policy {
    delete_behavior = "LOG"
    update_behavior = "UPDATE_IN_DATABASE"
  }

  configuration = jsonencode({
    Version = 1.0
    CrawlerOutput = {
      Partitions = { AddOrUpdateBehavior = "InheritFromTable" }
    }
    Grouping = { TableGroupingPolicy = "CombineCompatibleSchemas" }
  })

  tags = var.tags
}

###########################
# Glue Scripts
###########################

# Upload Glue processing script to S3
resource "aws_s3_object" "processing_script_prices" {
  bucket = var.s3_bucket_name
  key    = "scripts/processing_script_prices.py"
  source = "../../../src/data_retrieval/glue/scripts/processing_script_prices.py"
  etag   = filemd5("../../../src/data_retrieval/glue/scripts/processing_script_prices.py")
}

# Upload Glue processing script for volumes to S3
resource "aws_s3_object" "processing_script_volumes" {
  bucket = var.s3_bucket_name
  key    = "scripts/processing_script_volumes.py"
  source = "../../../src/data_retrieval/glue/scripts/processing_script_volumes.py"
  etag   = filemd5("../../../src/data_retrieval/glue/scripts/processing_script_volumes.py")
}

###########################
# Glue Jobs
###########################

resource "aws_glue_job" "market_prices_processing" {
  name     = "market-prices-processing-${var.environment}"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.s3_bucket_name}/scripts/processing_script_prices.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--database_name"                    = aws_glue_catalog_database.market_data_database.name
    "--s3_bucket_name"                   = var.s3_bucket_name
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"
    "--job-bookmark-option"              = "job-bookmark-enable"
    "--enable-metrics"                   = ""
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-auto-scaling"              = "true"
    "--find_latest_partition"            = "true"
    "--use_specific_partition"           = "false"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  # Use Flex execution type with auto-scaling
  glue_version      = "4.0"
  worker_type       = "G.1X" # Flex type starting at 2 DPU
  number_of_workers = 2

  # Auto-scaling configuration
  execution_class = "FLEX"

  timeout = 60

  tags = var.tags

  # Ensure the script is uploaded before creating the job
  depends_on = [aws_s3_object.processing_script_prices]
}

resource "aws_glue_job" "order_volumes_processing" {
  name     = "order-volumes-processing-${var.environment}"
  role_arn = aws_iam_role.glue_role.arn

  command {
    name            = "glueetl"
    script_location = "s3://${var.s3_bucket_name}/scripts/processing_script_volumes.py"
    python_version  = "3"
  }

  default_arguments = {
    "--job-language"                     = "python"
    "--s3_bucket_name"                   = var.s3_bucket_name
    "--TempDir"                          = "s3://${var.s3_bucket_name}/temp/"
    "--enable-metrics"                   = ""
    "--enable-continuous-cloudwatch-log" = "true"
    "--enable-auto-scaling"              = "true"
  }

  execution_property {
    max_concurrent_runs = 1
  }

  # Use Flex execution type with auto-scaling
  glue_version      = "4.0"
  worker_type       = "G.1X" # Flex type starting at 2 DPU
  number_of_workers = 2

  # Auto-scaling configuration
  execution_class = "FLEX"

  timeout = 60

  tags = var.tags

  # Ensure the script is uploaded before creating the job
  depends_on = [aws_s3_object.processing_script_volumes]
}

###########################
# IAM Role for Glue
###########################

resource "aws_iam_role" "glue_role" {
  name = "glue-market-data-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "glue.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# Attach AWS managed Glue Service policy
resource "aws_iam_role_policy_attachment" "glue_service" {
  role       = aws_iam_role.glue_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSGlueServiceRole"
}

# Additional policy for S3 bucket access
resource "aws_iam_policy" "glue_s3_access" {
  name        = "glue-s3-access-policy-${var.environment}"
  description = "Policy for Glue to access S3 bucket for market data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.s3_bucket_name}",
          "arn:aws:s3:::${var.s3_bucket_name}/*"
        ]
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "glue_s3_access" {
  role       = aws_iam_role.glue_role.name
  policy_arn = aws_iam_policy.glue_s3_access.arn
}

# Glue Trigger to run job every 5 days
resource "aws_glue_trigger" "market_prices_processing_trigger" {
  name     = "market-prices-processing-trigger-${var.environment}"
  type     = "SCHEDULED"
  schedule = var.job_schedule

  actions {
    job_name = aws_glue_job.market_prices_processing.name
  }

  tags = var.tags
}

###########################
# Glue Trigger for Order Volumes Job
###########################

resource "aws_glue_trigger" "order_volumes_processing_trigger" {
  name     = "order-volumes-processing-trigger-${var.environment}"
  type     = "SCHEDULED"
  schedule = var.job_schedule

  actions {
    job_name = aws_glue_job.order_volumes_processing.name
  }

  tags = var.tags
}