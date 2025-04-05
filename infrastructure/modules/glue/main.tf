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