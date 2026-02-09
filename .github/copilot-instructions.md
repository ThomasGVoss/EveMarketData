# EVE Market Data - AI Agent Instructions

## Project Overview
EVE Online market data analysis platform using AWS services, SageMaker ML pipelines, and serverless data ingestion. The project fetches market data from the EVE ESI API, processes it through AWS Glue/Lambda, trains ML models via SageMaker pipelines, and presents insights through a Streamlit frontend.

## Architecture

### Stack-Based Infrastructure (Terraform)
The infrastructure follows a **layered stack pattern** in `infrastructure/`:
- **network** → **storage** → **data_processing** → **analytics** → **application**
- Each stack (`infrastructure/stacks/`) is composed of reusable modules (`infrastructure/modules/`)
- Environment-specific configs live in `infrastructure/environments/dev/`

### Key AWS Services
- **Lambda**: Serverless ingestion from EVE ESI API (market orders/prices) every 12 hours
- **S3 Buckets**: `sagemaker-{env}-{account}`, `market-data-{env}-{account}`, `athena-results-{env}-{account}`
- **Glue**: Data cataloging via crawlers and ETL jobs
- **SageMaker**: ML training/inference pipelines with model versioning
- **ECS/ALB**: Streamlit frontend deployment (Docker-based)

### SageMaker Pipeline Pattern
Pipelines are defined in `src/training_pipelines/` and `src/inference_pipelines/`:
- Each pipeline module (e.g., `abalone/`) implements `get_pipeline(**kwargs)` returning a `sagemaker.workflow.pipeline.Pipeline`
- Console entry points: `run-training-pipeline`, `get-training-pipeline-definition` (see `setup.py`)
- Pipeline steps: `ProcessingStep` → `TuningStep` → `ConditionStep` → `RegisterModel`

## Critical Workflows

### Running SageMaker Pipelines
```bash
# From project root (uses .venv/Scripts/activate on Windows)
bash infrastructure/scripts/training.sh   # Training pipeline
bash infrastructure/scripts/inference.sh  # Inference pipeline
```

**Pattern**: Scripts extract Terraform outputs (role ARN, bucket names) from `infrastructure/environments/dev/` using `terraform output -json analytics_outputs | jq`

### Infrastructure Deployment
```bash
cd infrastructure/environments/dev
terraform init
terraform plan
terraform apply
```

**Dependencies**: Requires existing VPC (referenced via `data.aws_vpc.existing_vpc` in `dev/data.tf`)

### Lambda Deployment
Lambda source code automatically zipped from `src/data_retrieval/lambda_functions/{source_dir}/` via Terraform's `archive_file` data source. Deploy via `terraform apply` in data_processing stack.

## Project-Specific Conventions

### EVE API Integration
- **Important regions** (hardcoded in README.md):
  - The Forge: `10000002` (primary trading hub - Jita)
  - Sinq Laison: `10000032`, Domain: `10000043`, Heimatar: `10000030`
- API base: `https://esi.evetech.net/dev/markets/{region_id}/`
- Static Data Export (SDE) files in `data/` (types, blueprints, materials, market groups)

### Python Package Structure
The `src/` directory is an **installable package** (`pipelines`):
- Install with: `pip install -e . "awscli>1.20.30"` (from `src/` dir)
- Version/metadata in `src/__version__.py`
- Requires Python ≥3.11

### Pipeline Configuration Pattern
Pipeline scripts expect these kwargs (passed as JSON string via `--kwargs`):
```python
region, sagemaker_project_arn, role, pipeline_bucket, 
pipeline_name, model_package_group_name, base_job_prefix
```
Example: `training_pipelines/abalone/pipeline.py::get_pipeline()`

### Terraform Module Patterns
- **S3 buckets**: Check for existing buckets via `data.aws_s3_bucket` before creating
- **Lambda**: Source from `../../../src/data_retrieval/lambda_functions/` relative paths
- **Naming convention**: `{resource}-{environment}-{account_id}` or `{function_name}-{environment}`

### SageMaker-Specific Patterns
- **Code upload**: Scripts uploaded to S3 before pipeline execution (see `sagemaker_session.upload_data()` in pipeline.py)
- **Output paths**: `s3://{bucket}/{pipeline_name}/{pipeline_name}--{timestamp}--{run_id}/`
- **Cache config**: 1-hour caching enabled for pipeline steps (`CacheConfig(enable_caching=True, expire_after="PT1H")`)
- **Model approval**: Defaults to "Approved" status for automatic deployment

## File Organization Anti-Patterns
- **Don't add code to `src/common/`** - currently empty, purpose unclear
- **Lambda requirements**: Each Lambda function has its own `requirements.txt` in its directory
- **Notebooks**: EDA/feature engineering notebooks in `notebooks/` - not part of production pipelines

## Data Flow
1. **Ingestion**: Lambda → S3 (`market-data-{env}`) as JSON
2. **Cataloging**: Glue crawler → Glue Data Catalog
3. **Processing**: Glue ETL jobs / SageMaker processing steps
4. **Training**: SageMaker pipelines → Model Registry
5. **Inference**: Registered models → Batch transform / endpoints
6. **Visualization**: Streamlit queries Athena / model endpoints

## Testing & Quality
Test structure in `tests/` mirrors `src/`:
- `tests/data_retrieval/lambda_functions/`
- `tests/pipelines/abalone/`
- Run tests with pytest (configured in `setup.py` extras)

## Key Files Reference
- [src/setup.py](src/setup.py) - Package config, console entry points, dependencies
- [infrastructure/environments/dev/main.tf](infrastructure/environments/dev/main.tf) - Stack orchestration
- [infrastructure/scripts/training.sh](infrastructure/scripts/training.sh) - Training workflow example
- [src/training_pipelines/abalone/pipeline.py](src/training_pipelines/abalone/pipeline.py) - Reference pipeline implementation
- [README.md](README.md) - EVE API endpoints and region IDs
