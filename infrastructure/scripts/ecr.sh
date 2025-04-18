pushd infrastructure/environments/dev
# Get the ECR repository URL from Terraform output
ECR_REPO=$(terraform output -json application_outputs | jq -r '.streamlit_ecr_repository_url')
echo "$ECR_REPO"

# Login to ECR (AWS CLI must be configured)
aws ecr get-login-password --region eu-central-1 | podman login --username AWS --password-stdin $ECR_REPO
popd

# Navigate to Streamlit app directory
pushd src/frontend/streamlit
# Build the image
podman build -t eve-market-streamlit .

# Tag the image
podman tag eve-market-streamlit:latest $ECR_REPO:latest

# Push the image to ECR
podman push $ECR_REPO:latest
popd
