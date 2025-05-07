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
from sagemaker import PipelineModel
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.model import Model
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor, FrameworkProcessor
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionLessThanOrEqualTo, ConditionGreaterThanOrEqualTo
from sagemaker.workflow.functions import JsonGet, Join
from sagemaker.workflow.steps import CacheConfig
from sagemaker.workflow.model_step import ModelStep
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.pipeline_context import PipelineSession
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

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
    output_destination = f"s3://{pipeline_bucket}/{pipeline_name}/{pipeline_name}--{date}--{pipeline_run_id}"
    
    logger.debug(f"Output destination:  {output_destination}")
    # logger.debug(f"Sagemaker version: {sagemaker.__version__}")
  
    # parameters for pipeline execution
    processing_instance_count = ParameterInteger(name="ProcessingInstanceCount", default_value=1)
    processing_instance_type = ParameterString(
        name="ProcessingInstanceType", default_value="ml.c4.xlarge"
    )
    training_instance_type = ParameterString(
        name="TrainingInstanceType", default_value="ml.c4.xlarge"
    )
    model_approval_status = ParameterString(
        name="ModelApprovalStatus", default_value="Approved"
    )

    # Create timestamp for unique paths
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    cache_config = CacheConfig(enable_caching=True, expire_after="PT1H")

    # Upload the preprocessing script to S3
    preprocessing_code_prefix = "processing_code"
    preprocessing_code_s3_uri = sagemaker_session.upload_data(
        path="pipelines/abalone/preprocess.py",
        bucket=pipeline_bucket,
        key_prefix=f"{pipeline_name}/{pipeline_name}--{date}--{pipeline_run_id}/{preprocessing_code_prefix}"
    )

    #Upload the evaluation script to S3
    evaluation_code_prefix = "evaluation_code"
    evaluation_code_s3_uri = sagemaker_session.upload_data(
        path="pipelines/abalone/evaluate.py",
        bucket=pipeline_bucket,
        key_prefix=f"{pipeline_name}/{pipeline_name}--{date}--{pipeline_run_id}/{evaluation_code_prefix}"
    )

    # processing step for feature engineering
    sklearn_processor = SKLearnProcessor(
        framework_version="0.23-1",
        instance_type=processing_instance_type,
        instance_count=processing_instance_count,
        base_job_name=f"{base_job_prefix}/sklearn-abalone-preprocess",
        sagemaker_session=sagemaker_session,
        role=role,
    )
    step_process = ProcessingStep(
        name="PreprocessAbaloneData",
        processor=sklearn_processor,
        inputs=[
        ProcessingInput(
            input_name='data',
            source=f's3://market-data-dev-142571790518/processed/market_prices/',
            destination='/opt/ml/processing/input/data')
        ],
        outputs=[
            ProcessingOutput(output_name="train", 
                             source="/opt/ml/processing/train",
                             destination=Join(
                                 on="/",
                                 values=[
                                     output_destination,
                                     "train"])),
            ProcessingOutput(output_name="validation", 
                             source="/opt/ml/processing/validation",
                             destination=Join(
                                 on="/",
                                 values=[
                                     output_destination,
                                     "validation"])),
            ProcessingOutput(output_name="test", 
                             source="/opt/ml/processing/test",
                             destination=Join(
                                 on="/",
                                 values=[
                                     output_destination,
                                     "test"])),
            ProcessingOutput(output_name="encoder", 
                             source="/opt/ml/processing/encoder",
                             destination=Join(
                                 on="/",
                                 values=[
                                     output_destination,
                                     "encoder"])),
        ],
        code=preprocessing_code_s3_uri,
        cache_config=cache_config
    )

    # training step for generating model artifacts
    model_path = f"{output_destination}/modelArtifacts"
    image_uri = sagemaker.image_uris.retrieve(
        framework="xgboost",
        region=region,
        version="1.0-1",
        py_version="py3",
        instance_type=training_instance_type,
    )

    xgb_train = Estimator(
        image_uri=image_uri,
        instance_type=training_instance_type,
        instance_count=1,
        output_path=model_path,
        base_job_name=f"{base_job_prefix}/abalone-train",
        sagemaker_session=sagemaker_session,
        role=role,
        use_spot_instances=True,
        max_wait=7200,  # 2 hours
        max_run=3600,   # 1 hour
    )
    xgb_train.set_hyperparameters(
        objective="reg:squarederror",
        num_round=500,
        max_depth=10,
        eta=0.3,
        gamma=2,
        min_child_weight=6,
        subsample=0.7,
        silent=0,
    )
    step_train = TrainingStep(
        name="TrainAbaloneModel",
        estimator=xgb_train,
        inputs={
            "train": TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs[
                    "train"
                ].S3Output.S3Uri,
                content_type="text/csv",
            ),
            "validation": TrainingInput(
                s3_data=step_process.properties.ProcessingOutputConfig.Outputs[
                    "validation"
                ].S3Output.S3Uri,
                content_type="text/csv",
            ),
        },
        cache_config=cache_config
    )

    # processing step for evaluation
    script_eval = ScriptProcessor(
        image_uri=image_uri,
        command=["python3"],
        instance_type=processing_instance_type,
        instance_count=1,
        base_job_name=f"{base_job_prefix}/script-abalone-eval",
        sagemaker_session=sagemaker_session,
        role=role,
    )
    evaluation_report = PropertyFile(
        name="AbaloneEvaluationReport",
        output_name="evaluation",
        path="evaluation.json",
    )
    step_eval = ProcessingStep(
        name="EvaluateAbaloneModel",
        processor=script_eval,
        inputs=[
            ProcessingInput(
                source=step_train.properties.ModelArtifacts.S3ModelArtifacts,
                destination="/opt/ml/processing/model",
            ),
            ProcessingInput(
                source=step_process.properties.ProcessingOutputConfig.Outputs[
                    "test"
                ].S3Output.S3Uri,
                destination="/opt/ml/processing/test",
            ),
        ],
        outputs=[
            ProcessingOutput(output_name="evaluation", 
                    source="/opt/ml/processing/evaluation",
                    destination=Join(
                        on="/",
                        values=[
                            output_destination,
                            "evaluation"])),
        ],
        code=evaluation_code_s3_uri,
        property_files=[evaluation_report],
    )

    ## model registration step

    pipeline_session = PipelineSession()
    
    model = Model(
        image_uri=image_uri,
        model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
        sagemaker_session=pipeline_session,
        role=role)

    step_model_create = ModelStep(
        name="MyModelCreationStep",
        step_args=model.create(instance_type="ml.m5.xlarge"))
    
    cond_lte = ConditionGreaterThanOrEqualTo(
        left=JsonGet(
            step_name=step_eval.name,
            property_file=evaluation_report,
            json_path="regression_metrics.r2.value"
        ),
        right=0.90
    )

    step_cond = ConditionStep(
        name="AbaloneMAECond",
        conditions=[cond_lte],
        if_steps=[step_model_create],
        else_steps=[]
    )

    pipeline_model = PipelineModel(
        models=[model],
        role=role,
        sagemaker_session=pipeline_session)
    
    register_model_step_args = pipeline_model.register(
        # content_types=["application/json"],
        # response_types=["application/json"],
        # inference_instances=["ml.t2.medium", "ml.m5.xlarge"],
        # transform_instances=["ml.m5.xlarge"],
        content_types=["text/csv"],
        response_types=["text/csv"],
        inference_instances=["ml.t2.medium", "ml.m5.large"],
        transform_instances=["ml.m5.large"],
        model_package_group_name=model_package_group_name,
        approval_status=model_approval_status,
    )

    step_model_registration = ModelStep(
        name="AbaloneRegisterModel",
        step_args=register_model_step_args,
        depends_on=[step_model_create.name],)


    ## pipeline definition ##

    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            processing_instance_type,
            processing_instance_count,
            training_instance_type,
            model_approval_status,
        ],
        steps=[step_process, 
               step_train,
               step_eval,
               step_cond,
               step_model_registration
               ],
        sagemaker_session=sagemaker_session,
    )

    return pipeline
