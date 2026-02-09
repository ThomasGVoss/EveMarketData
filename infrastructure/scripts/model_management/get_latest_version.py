import boto3

def get_latest_model_package(model_package_group_name, sagemaker_client=None):
    if sagemaker_client is None:
        sagemaker_client = boto3.client("sagemaker")

    response = sagemaker_client.list_model_packages(
        ModelPackageGroupName=model_package_group_name,
        SortBy="CreationTime",
        SortOrder="Descending",
        MaxResults=1
    )
    
    packages = response.get("ModelPackageSummaryList", [])
    if not packages:
        print("No model packages found.")
        return None, None
    latest_package = packages[0]
    arn = latest_package["ModelPackageArn"]
    return arn


NAME_CONTAINS = "abalone-training-dev"
latest_arn = get_latest_model_package(NAME_CONTAINS)

print(f"Latest model ARN: {latest_arn}")