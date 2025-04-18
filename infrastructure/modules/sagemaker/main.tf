resource "aws_sagemaker_domain" "domain" {
  domain_name             = var.domain_name
  auth_mode               = var.auth_mode
  vpc_id                  = var.vpc_id
  subnet_ids              = var.subnet_ids
  kms_key_id              = var.kms_key_id
  app_network_access_type = var.app_network_access_type

  default_user_settings {
    execution_role = aws_iam_role.sagemaker_execution_role.arn

    security_groups = concat(
      [aws_security_group.sagemaker_sg.id],
      var.additional_security_group_ids
    )

    # Storage configuration
    sharing_settings {
      notebook_output_option = "Allowed"
      s3_output_path         = var.s3_output_path
      s3_kms_key_id          = var.s3_kms_key_id
    }
  }

  # Add tags to the domain
  tags = merge(
    var.tags,
    {
      Name = var.domain_name
    }
  )
}

# Security group for SageMaker
resource "aws_security_group" "sagemaker_sg" {
  name        = "${var.domain_name}-sagemaker-sg"
  description = "Security group for SageMaker domain ${var.domain_name}"
  vpc_id      = var.vpc_id

  # By default, allow all outbound traffic
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.domain_name}-sagemaker-sg"
    }
  )
}

# SageMaker execution role
resource "aws_iam_role" "sagemaker_execution_role" {
  name = "${var.domain_name}-sagemaker-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "sagemaker.amazonaws.com"
        }
      }
    ]
  })

  tags = merge(
    var.tags,
    {
      Name = "${var.domain_name}-sagemaker-execution-role"
    }
  )
}

# Attach AmazonSageMakerFullAccess policy to the role
resource "aws_iam_role_policy_attachment" "sagemaker_full_access" {
  role       = aws_iam_role.sagemaker_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSageMakerFullAccess"
}

# Attach S3 access policy to the role
resource "aws_iam_role_policy" "s3_access" {
  name = "s3-access"
  role = aws_iam_role.sagemaker_execution_role.id

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
          "${var.s3_bucket_arn}",
          "${var.s3_bucket_arn}/*",
          "arn:aws:s3:::market-data-dev-${var.account_id}",
          "arn:aws:s3:::market-data-dev-${var.account_id}/*",
          "arn:aws:s3:::sagemaker-eu-central-1-${var.account_id}",
          "arn:aws:s3:::sagemaker-eu-central-1-${var.account_id}/*"
        ]
      }
    ]
  })
} 