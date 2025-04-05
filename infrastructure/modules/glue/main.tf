# infrastructure/modules/glue/main.tf
###########################
# Glue Database
###########################
resource "aws_glue_catalog_database" "market_data_database" {
  name = "market_data_${var.environment}"
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
# Glue ETL Job for Consolidation
###########################

# Upload Glue ETL Script to S3
resource "aws_s3_object" "consolidate_script" {
  bucket = var.s3_bucket_name
  key    = "scripts/consolidate_market_data.py"
  content = file("${path.module}/scripts/consolidate_market_data.py")
  etag    = filemd5("${path.module}/scripts/consolidate_market_data.py")
}

resource "aws_glue_job" "consolidate_market_data" {
  name     = "consolidate-market-data-${var.environment}"
  role_arn = aws_iam_role.glue_role.arn
  
  glue_version = "3.0"
  worker_type  = "Standard"
  number_of_workers = 1
  max_retries = 0
  timeout     = 60
  
  execution_property {
    max_concurrent_runs = 1
  }
  
  command {
    name            = "glueetl"
    script_location = "s3://${var.s3_bucket_name}/scripts/consolidate_market_data.py"
    python_version  = "3"
  }
  
  default_arguments = {
    "--enable-job-bookmarks" = "true"
    "--job-language" = "python"
    "--TempDir" = "s3://${var.s3_bucket_name}/temp/"
    "--job-bookmark-option" = "job-bookmark-enable"
    "--database_name" = aws_glue_catalog_database.market_data_database.name
    "--output_path" = "s3://${var.s3_bucket_name}/processed/consolidated/"
  }
  
  tags = var.tags
  
  depends_on = [aws_s3_object.consolidate_script]
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