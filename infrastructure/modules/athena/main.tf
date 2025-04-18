###########################
# Athena Workgroup
###########################
resource "aws_athena_workgroup" "market_data_workgroup" {
  name        = "market-data-workgroup-${var.environment}"
  description = "Workgroup for EVE Online market data analysis"

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true

    result_configuration {
      output_location = "s3://${var.athena_results_bucket_name}/athena-results/"

      encryption_configuration {
        encryption_option = "SSE_S3"
      }
    }

    engine_version {
      selected_engine_version = "Athena engine version 3"
    }
  }

  tags = var.tags
}


###########################
# IAM Permissions
###########################

# Add Athena permissions to the existing Glue role if needed
resource "aws_iam_policy" "athena_permissions" {
  name        = "athena-access-policy-${var.environment}"
  description = "Policy for Athena access to query market data"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetWorkGroup",
          "athena:StopQueryExecution",
          "athena:ListQueryExecutions"
        ]
        Resource = [
          "arn:aws:athena:*:*:workgroup/${aws_athena_workgroup.market_data_workgroup.name}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.athena_results_bucket_name}/*",
          "arn:aws:s3:::${var.athena_results_bucket_name}"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "glue:GetTable",
          "glue:GetPartitions",
          "glue:GetDatabase"
        ]
        Resource = [
          "arn:aws:glue:*:*:catalog",
          "arn:aws:glue:*:*:database/${var.glue_database_name}",
          "arn:aws:glue:*:*:table/${var.glue_database_name}/*"
        ]
      }
    ]
  })
}
