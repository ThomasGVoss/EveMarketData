
# ECR Repository for the Streamlit container
module "streamlit_ecr" {
  source = "../../modules/ecr"

  repository_name = "${var.project_name}-streamlit"

  tags = var.tags
}

# ALB for the Streamlit app
module "streamlit_alb" {
  source = "../../modules/alb"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = var.vpc_id

  # Use the newly created public subnets
  public_subnets = var.public_subnet_ids

  container_port = 8501
  # Certificate ARN should be added when you have one
  # certificate_arn = "arn:aws:acm:${var.region}:your-account-id:certificate/cert-id"

  tags = var.tags
}

# ECS for the Streamlit app
module "streamlit_ecs" {
  source = "../../modules/ecs"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.region

  container_name  = "streamlit-app"
  container_image = "${module.streamlit_ecr.repository_url}:latest"
  container_port  = 8501

  container_cpu    = 256
  container_memory = 512

  vpc_id          = var.vpc_id
  private_subnets = var.private_subnet_ids

  target_group_arn      = module.streamlit_alb.target_group_arn
  alb_security_group_id = module.streamlit_alb.security_group_id
  alb_listener_arn      = module.streamlit_alb.http_listener_arn

  environment_variables = [
    {
      name  = "STREAMLIT_SERVER_PORT"
      value = "8501"
    },
    {
      name  = "STREAMLIT_SERVER_ADDRESS"
      value = "0.0.0.0"
    }
  ]

  tags = var.tags
}