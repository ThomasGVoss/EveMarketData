# infrastructure/environments/dev/streamlit.tf

# ECR Repository for the Streamlit container
module "streamlit_ecr" {
  source = "../../modules/ecr"
  
  repository_name = "eve-market-streamlit"
}

# ALB for the Streamlit app
module "streamlit_alb" {
  source = "../../modules/alb"
  
  project_name   = "eve-market"
  environment    = "dev"
  vpc_id         = data.aws_vpc.existing_vpc.id
  
  # Use the newly created public subnets
  public_subnets = aws_subnet.public[*].id
  
  container_port = 8501
  # Certificate ARN should be added when you have one
  # certificate_arn = "arn:aws:acm:eu-central-1:your-account-id:certificate/cert-id"
}

# ECS for the Streamlit app
module "streamlit_ecs" {
  source = "../../modules/ecs"
  
  project_name    = "eve-market"
  environment     = "dev"
  aws_region      = "eu-central-1"
  
  container_name  = "streamlit-app"
  container_image = "${module.streamlit_ecr.repository_url}:latest"
  container_port  = 8501
  
  container_cpu    = 256
  container_memory = 512
  
  vpc_id          = data.aws_vpc.existing_vpc.id
  private_subnets = data.aws_subnets.private.ids
  
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
}
