"""Example workflow pipeline script for abalone pipeline.

                                               . -RegisterModel
                                              .
    Process-> Train -> Evaluate -> Condition .
                                              .
                                               . -(stop)

Implements a get_pipeline(**kwargs) method.
"""

import os
import uuid

import boto3
import logging
import sagemaker
import sagemaker.session
from datetime import datetime
from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.transformer import Transformer
from sagemaker.workflow.functions import Join
from sagemaker.workflow.steps import CacheConfig
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.steps import ProcessingStep

from sagemaker.inputs import TransformInput
from sagemaker.workflow.steps import TransformStep

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger(__name__)

def get_sagemaker_client(region):
     """Gets the sagemaker client.

        Args:
            region: the aws region to start the session
            default_bucket: the bucket to use for storing the artifacts

        Returns:
            `sagemaker.session.Session instance
        """
     boto_session = boto3.Session(region_name=region)
     sagemaker_client = boto_session.client("sagemaker")
     return sagemaker_client


def get_session(region, default_bucket):
    """Gets the sagemaker session based on the region.

    Args:
        region: the aws region to start the session
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        `sagemaker.session.Session instance
    """

    boto_session = boto3.Session(region_name=region)

    sagemaker_client = boto_session.client("sagemaker")
    runtime_client = boto_session.client("sagemaker-runtime")
    return sagemaker.session.Session(
        boto_session=boto_session,
        sagemaker_client=sagemaker_client,
        sagemaker_runtime_client=runtime_client,
        default_bucket=default_bucket,
    )

def get_pipeline_custom_tags(new_tags, region, sagemaker_project_arn=None):
    try:
        sm_client = get_sagemaker_client(region)
        response = sm_client.list_tags(
            ResourceArn=sagemaker_project_arn)
        project_tags = response["Tags"]
        for project_tag in project_tags:
            new_tags.append(project_tag)
    except Exception as e:
        print(f"Error getting project tags: {e}")
    return new_tags


def get_pipeline(
    region,
    sagemaker_project_arn=None,
    role=None,
    default_bucket=None,
    pipeline_bucket=None,
    model_package_group_name="AbalonePackageGroup",
    pipeline_name="AbalonePipeline",
    base_job_prefix="Abalone",
):
    """Gets a SageMaker ML Pipeline instance working with on abalone data.

    Args:
        region: AWS region to create and run the pipeline.
        role: IAM role to create and run steps and pipeline.
        default_bucket: the bucket to use for storing the artifacts

    Returns:
        an instance of a pipeline
    """
    sagemaker_session = get_session(region, default_bucket)
    if role is None:
        role = sagemaker.session.get_execution_role(sagemaker_session)

    now = datetime.now()
    day = now.strftime("%Y-%m-%d")
    date = now.strftime("%Y-%m-%d--%H-%M-%S")
    pipeline_run_id = str(uuid.uuid4())[:8]
    model_location = f"s3://{pipeline_bucket}/{pipeline_name}/{pipeline_name}--{date}--{pipeline_run_id}"
    
    logger.debug(f"Model location:  {model_location}")
    # logger.debug(f"Sagemaker version: {sagemaker.__version__}")
  
    # parameters for pipeline execution
    processing_instance_count = ParameterInteger(
        name="ProcessingInstanceCount", default_value=1)
    processing_instance_type = ParameterString(
        name="ProcessingInstanceType", default_value="ml.t3.xlarge")
    inference_instance_type = ParameterString(
        name="InferenceInstanceType", default_value="ml.m4.xlarge")
    model_approval_status = ParameterString(
        name="ModelApprovalStatus", default_value="Approved")

    cache_config = CacheConfig(enable_caching=True, expire_after="PT1H")

    # Upload the preprocessing script to S3
    preprocessing_code_prefix = "processing_code"
    preprocessing_code_s3_uri = sagemaker_session.upload_data(
        path="inference_pipelines/abalone/preprocess.py",
        bucket=pipeline_bucket,
        key_prefix=f"{pipeline_name}/{pipeline_name}--{date}--{pipeline_run_id}/{preprocessing_code_prefix}"
    )


    # processing step for feature engineering
    script_processor = ScriptProcessor(
        command = ["python3"],
        image_uri= "142571790518.dkr.ecr.eu-central-1.amazonaws.com/script-processor:latest",
        role=role,
        instance_type=processing_instance_type,
        instance_count=processing_instance_count,
    )

    step_process = ProcessingStep(
        name="PreprocessAbaloneData",
        processor=script_processor,
        inputs=[
            ProcessingInput(
                input_name='data',
                source=f's3://market-data-dev-142571790518/processed/order_volumes/',
                destination='/opt/ml/processing/input/data'),
            ProcessingInput(
                input_name='encoder',
                source=f's3://sagemaker-dev-142571790518/abalone-training-dev/abalone-training-dev--2025-07-06--14-44-28--82a699c0/encoder/',
                destination='/opt/ml/processing/encoder'),
            ],
        # TODO: We only need one set of outputs which we than can pass to the transform step
        outputs=[
            ProcessingOutput(output_name="transform_data", 
                             source="/opt/ml/processing/transform",
                             destination=Join(
                                 on="/",
                                 values=[
                                     model_location,
                                     "transform"])),
        ],
        code=preprocessing_code_s3_uri,
        cache_config=cache_config
    )

    # transform step 
    model_path = f"{model_location}/modelArtifacts"
    #TODO: We need the model name that we have registered in the training step
    transformer = Transformer(  
                        model_name= "pipelines-9ptlbyt0687d-MyModelCreationStep--B0fOybidU2", 
                        instance_count= 1,
                        instance_type= inference_instance_type,
                        output_path=f"{model_path}/transform",
                        sagemaker_session=PipelineSession(),
                        assemble_with="Line",
                        accept="text/csv",)

    step_transform = TransformStep(
        name="AbaloneTransform",
        step_args=transformer.transform(
                                data=step_process.properties.ProcessingOutputConfig.Outputs['transform_data'].S3Output.S3Uri,
                                join_source="Input",
                                content_type="text/csv",
                                split_type="Line",
                                input_filter="$[1,2,3,4,5,6,7,8,9,10,11]", # as we need to drop the first column
                                ),
    )
    ## pipeline definition ##

    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            processing_instance_type,
            processing_instance_count,
            inference_instance_type,
            model_location,
            model_approval_status,
            ],
        steps=[step_process, 
               step_transform
               ],
        sagemaker_session=sagemaker_session,
    )

    return pipeline
