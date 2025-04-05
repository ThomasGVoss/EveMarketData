output "glue_database_name" {
  description = "Name of the Glue catalog database"
  value       = aws_glue_catalog_database.market_data_database.name
}

output "glue_prices_crawler_name" {
  description = "Name of the market prices crawler"
  value       = aws_glue_crawler.market_prices_crawler.name
}

output "glue_orders_crawler_name" {
  description = "Name of the market orders crawler"
  value       = aws_glue_crawler.market_orders_crawler.name
}

output "glue_job_name" {
  description = "Name of the Glue job for data consolidation"
  value       = aws_glue_job.consolidate_market_data.name
}

output "glue_role_arn" {
  description = "ARN of the IAM role used for Glue"
  value       = aws_iam_role.glue_role.arn
}
