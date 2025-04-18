resource "aws_sagemaker_user_profile" "default_user" {
  count             = var.create_default_user_profile ? 1 : 0
  domain_id         = aws_sagemaker_domain.domain.id
  user_profile_name = var.default_user_profile_name

  user_settings {
    execution_role = aws_iam_role.sagemaker_execution_role.arn
  }

  tags = merge(
    var.tags,
    {
      Name = var.default_user_profile_name
    }
  )
} 