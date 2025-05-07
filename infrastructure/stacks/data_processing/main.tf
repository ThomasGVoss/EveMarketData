
# Lambda for market prices data ingestion
module "market_prices_lambda" {
  source = "../../modules/lambda"

  function_name       = "market-data-prices-ingestion"
  handler             = "market_price_ingestion.lambda_handler"
  source_dir          = "market_prices"
  environment         = var.environment
  s3_bucket_name      = var.market_data_bucket_id
  schedule_expression = "rate(12 hours)"

  tags = merge(var.tags, {
    Function = "Market Price Ingestion"
  })
}

# Lambda for market orders data ingestion
module "market_orders_lambda" {
  source = "../../modules/lambda"

  function_name       = "market-data-orders-ingestion"
  handler             = "market_order_ingestion.lambda_handler"
  source_dir          = "market_orders"
  environment         = var.environment
  s3_bucket_name      = var.market_data_bucket_id
  schedule_expression = "rate(12 hours)"

  tags = merge(var.tags, {
    Function = "Market Orders Ingestion"
  })
}

# Glue Resources for Market Data Analytics
module "market_data_glue" {
  source = "../../modules/glue"

  environment      = var.environment
  s3_bucket_name   = var.market_data_bucket_id
  crawler_schedule = "cron(0 0 */2 * ? *)"
  job_schedule     = "cron(0 0 */5 * ? *)"

  tags = var.tags
}
