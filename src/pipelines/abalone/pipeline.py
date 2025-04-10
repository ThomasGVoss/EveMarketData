"""Example workflow pipeline script for abalone pipeline.

                                               . -RegisterModel
                                              .
    Process-> Train -> Evaluate -> Condition .
                                              .
                                               . -(stop)

Implements a get_pipeline(**kwargs) method.
"""

import os

import boto3
import sagemaker
import sagemaker.session
from datetime import datetime
from sagemaker.estimator import Estimator
from sagemaker.inputs import TrainingInput
from sagemaker.model_metrics import MetricsSource, ModelMetrics
from sagemaker.processing import ProcessingInput, ProcessingOutput, ScriptProcessor
from sagemaker.sklearn.processing import SKLearnProcessor
from sagemaker.workflow.condition_step import ConditionStep
from sagemaker.workflow.conditions import ConditionLessThanOrEqualTo
from sagemaker.workflow.functions import JsonGet
from sagemaker.workflow.parameters import ParameterInteger, ParameterString
from sagemaker.workflow.pipeline import Pipeline
from sagemaker.workflow.properties import PropertyFile
from sagemaker.workflow.step_collections import RegisterModel
from sagemaker.workflow.steps import ProcessingStep, TrainingStep

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

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
    metadata_path = f"s3://{model_artifacts_bucket}/{branch_prefix}/metadata/{pipeline_name}/{pipeline_name}--{date}--{pipeline_run_id}"
    model_path = f"s3://{model_artifacts_bucket}/{branch_prefix}/models/{pipeline_name}"

    # output_inference_result_bucket = output_inference_result_bucket_arn.split(":::")[1]
    # output_training_result_path = f"s3://{output_inference_result_bucket}/training/{branch_prefix}/{pipeline_name}/{day}/{pipeline_name}--{date}--{pipeline_run_id}"

    # Versions
    sklearn_framework_version = "1.2-1"
    xgboost_framework_version = "1.7-1"
  
    logger.debug(f"Model name:  {model_name}")
    logger.debug(f"Output destination:  {output_destination}")
    logger.debug(f"Metadata path:  {metadata_path}")
    logger.debug(f"Output training:  {output_training_result_path}")
    logger.debug(f"Sagemaker version: {sagemaker.__version__}")
  
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
    input_data = ParameterString(
        name="InputDataUrl",
        default_value=f"s3://sagemaker-servicecatalog-seedcode-{region}/dataset/abalone-dataset.csv",
    )

    # Create timestamp for unique paths
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    # Upload the preprocessing script to S3
    preprocessing_code_prefix = f"{base_job_prefix}/{timestamp}/processing_code"
    preprocessing_code_s3_uri = sagemaker_session.upload_data(
        path="pipelines/abalone/preprocess.py",
        bucket=default_bucket,
        key_prefix=preprocessing_code_prefix
    )

    #Upload the evaluation script to S3
    evaluation_code_prefix = f"{base_job_prefix}/{timestamp}/evaluation_code"
    evaluation_code_s3_uri = sagemaker_session.upload_data(
        path="pipelines/abalone/evaluate.py",
        bucket=default_bucket,
        key_prefix=evaluation_code_prefix
    )

    # ---------- 1. Split Vessel Rotation Dataset  --------
    splitting_job_name = f"splitting--{date}"
    
    sklearn_preprocessing = FrameworkProcessor(
        role=role,
        estimator_cls=SKLearnClass,
        framework_version=sklearn_framework_version,
        instance_count=1,
        instance_type=splitting_instance_type,
        sagemaker_session=sagemaker_session,
        code_location=output_destination,
        env={
            "min_train_date": min_train_date,
            "train_val_split_date": train_val_split_date,
            "val_test_split_date": val_test_split_date,
            "max_test_date": max_test_date,
            "project_name": "combined",
        },
    )
    
    step_args = sklearn_preprocessing.run(
        job_name=splitting_job_name,
        code="combined_model/training/pipeline_scripts/splitting/main.py",
        source_dir="../../../src",
        inputs=[
            ProcessingInput(
                source=input_vessel_rotation,
                destination="/opt/ml/processing/input/data/",
                s3_data_type="S3Prefix",
                s3_input_mode="File",
            ),
        ],
        outputs=[
            ProcessingOutput(
                output_name="split",
                source="/opt/ml/processing/output/split",
                destination=Join(
                    on="/",
                    values=[
                        output_destination,
                        splitting_job_name,
                        "output",
                        "split",
                    ],
                ),
            )
        ],
    )
    
    step_split = ProcessingStep(
        name=f"{project_name}-splitting",
        step_args=step_args,
        cache_config=cache_config,
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
    # I dislike the ProcessingOutput destination. I think i'll have to find a way to pass the timestamp to the processing step.
    step_process = ProcessingStep(
        name="PreprocessAbaloneData",
        processor=sklearn_processor,
        outputs=[
            ProcessingOutput(output_name="train", 
                             source="/opt/ml/processing/train",
                             destination=f"{timestamp}/train"),
            ProcessingOutput(output_name="validation", 
                             source="/opt/ml/processing/validation",
                             destination=f"{timestamp}/validation"),
            ProcessingOutput(output_name="test", 
                             source="/opt/ml/processing/test",
                             destination=f"{timestamp}/test"),
        ],
        code=preprocessing_code_s3_uri,
        job_arguments=["--input-data", input_data],
    )

    # training step for generating model artifacts
    model_path = f"s3://{sagemaker_session.default_bucket()}/{base_job_prefix}/{timestamp}/AbaloneTrain"
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
        objective="reg:linear",
        num_round=50,
        max_depth=5,
        eta=0.2,
        gamma=4,
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
            ProcessingOutput(output_name="evaluation", source="/opt/ml/processing/evaluation", destination=f"{timestamp}/evaluation"),
        ],
        code=evaluation_code_s3_uri,
        property_files=[evaluation_report],
    )

    # # register model step that will be conditionally executed
    # model_metrics = ModelMetrics(
    #     model_statistics=MetricsSource(
    #         s3_uri="{}/evaluation.json".format(
    #             step_eval.arguments["ProcessingOutputConfig"]["Outputs"][0]["S3Output"]["S3Uri"]
    #         ),
    #         content_type="application/json"
    #     )
    # )
    # step_register = RegisterModel(
    #     name="RegisterAbaloneModel",
    #     estimator=xgb_train,
    #     model_data=step_train.properties.ModelArtifacts.S3ModelArtifacts,
    #     content_types=["text/csv"],
    #     response_types=["text/csv"],
    #     inference_instances=["ml.t2.medium", "ml.m5.large"],
    #     transform_instances=["ml.m5.large"],
    #     model_package_group_name=model_package_group_name,
    #     approval_status=model_approval_status,
    #     model_metrics=model_metrics,
    # )

    # # condition step for evaluating model quality and branching execution
    # cond_lte = ConditionLessThanOrEqualTo(
    #     left=JsonGet(
    #         step_name=step_eval.name,
    #         property_file=evaluation_report,
    #         json_path="regression_metrics.mse.value"
    #     ),
    #     right=6.0,
    # )
    # step_cond = ConditionStep(
    #     name="CheckMSEAbaloneEvaluation",
    #     conditions=[cond_lte],
    #     if_steps=[step_register],
    #     else_steps=[],
    # )

    # pipeline instance
    pipeline = Pipeline(
        name=pipeline_name,
        parameters=[
            processing_instance_type,
            processing_instance_count,
            training_instance_type,
            model_approval_status,
            input_data,
        ],
        steps=[step_process, 
               step_train,
               step_eval],
        sagemaker_session=sagemaker_session,
    )
    return pipeline
