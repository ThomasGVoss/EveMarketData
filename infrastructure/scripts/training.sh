#!/bin/bash

export PYTHONUNBUFFERED=TRUE
export SAGEMAKER_PROJECT_NAME="abalone"
export SAGEMAKER_PROJECT_ID="dev"
export SAGEMAKER_PROJECT_NAME_ID="${SAGEMAKER_PROJECT_NAME}-${SAGEMAKER_PROJECT_ID}"
export AWS_REGION="eu-central-1"

echo "SageMaker Project Name ID: $SAGEMAKER_PROJECT_NAME_ID"

# jump to the dev env. directory
pushd infrastructure/environments/dev
# get the pipeline role arn from terraform output
export SAGEMAKER_PIPELINE_ROLE_ARN=$(terraform output -raw sagemaker_execution_role_arn)
#get the default bucket from terraform output
export BUCKET_NAME=$(terraform output -raw sagemaker_bucket)
popd

source .venv/Scripts/activate
# go the the src
pushd src
pip install virtualenv
#virtualenv .venv
pip install -e . "awscli>1.20.30"

# Add a check to verify the installation
python -c "import pipelines" || { echo "Pipelines package not installed correctly"; exit 1; }

run-pipeline --module-name pipelines.abalone.pipeline \
          --role-arn $SAGEMAKER_PIPELINE_ROLE_ARN \
          --tags "[{\"Key\":\"sagemaker:project-name\", \"Value\":\"${SAGEMAKER_PROJECT_NAME}\"}, {\"Key\":\"sagemaker:project-id\", \"Value\":\"${SAGEMAKER_PROJECT_ID}\"}]" \
          --kwargs "{\"region\":\"${AWS_REGION}\",\"sagemaker_project_arn\":\"${SAGEMAKER_PROJECT_ARN}\",\"role\":\"${SAGEMAKER_PIPELINE_ROLE_ARN}\",\"pipeline_bucket\":\"${BUCKET_NAME}\",\"pipeline_name\":\"${SAGEMAKER_PROJECT_NAME_ID}\",\"model_package_group_name\":\"${SAGEMAKER_PROJECT_NAME_ID}\",\"base_job_prefix\":\"${SAGEMAKER_PROJECT_NAME_ID}\"}"

popd

