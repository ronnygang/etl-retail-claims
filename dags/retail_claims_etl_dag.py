from datetime import datetime, timedelta
from airflow import DAG
from airflow.providers.google.cloud.operators.functions import CloudFunctionsInvokeFunctionOperator
from airflow.providers.google.cloud.operators.dataproc import (
    DataprocSubmitJobOperator,
    DataprocCreateClusterOperator,
    DataprocDeleteClusterOperator
)
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from airflow.exceptions import AirflowException
import logging

logger = logging.getLogger(__name__)

# Configuración
PROJECT_ID = Variable.get("GCP_PROJECT_ID", "your-project-id")
GCS_BUCKET = Variable.get("GCS_BUCKET_NAME", "retail-claims-etl")
GCS_TEMP_PATH = f"{GCS_BUCKET}/temp"
DATAPROC_CLUSTER_NAME = "retail-claims-cluster"
DATAPROC_ZONE = "us-central1-a"
CLOUD_FUNCTION_NAME = "ingest-sftp-to-gcs"
REGION = "us-central1"

# Argumentos por defecto
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['data-alerts@company.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

# Definición del DAG
dag = DAG(
    'retail_claims_etl_pipeline',
    default_args=default_args,
    description='ETL Pipeline: SFTP -> GCS -> BigQuery Bronze -> PySpark Silver -> BQ Procedure Gold',
    schedule_interval='0 2 * * *',
    catchup=False,
    tags=['retail', 'etl', 'daily'],
    max_active_runs=1
)


def log_pipeline_start(**context):
    """Registrar inicio del pipeline"""
    execution_date = context['execution_date']
    logger.info(f"🚀 Iniciando pipeline de ETL para: {execution_date}")


def validate_ingestion_result(**context):
    """Validar resultado de ingesta"""
    task_instance = context['task_instance']
    result = task_instance.xcom_pull(task_ids='ingest_sftp_to_gcs')
    
    if result and isinstance(result, dict) and result.get('status') != 'success':
        raise AirflowException(f"❌ Ingesta falló: {result.get('error', 'Error desconocido')}")
    
    logger.info(f"✅ Ingesta exitosa")


def log_pipeline_end(**context):
    """Registrar fin del pipeline"""
    logger.info("✅ Pipeline de ETL completado exitosamente")


# Tareas

# 1. Inicio
log_start = PythonOperator(
    task_id='log_pipeline_start',
    python_callable=log_pipeline_start,
    dag=dag
)

# 2. Cloud Function: Ingestar SFTP a GCS
ingest_sftp = CloudFunctionsInvokeFunctionOperator(
    task_id='ingest_sftp_to_gcs',
    function_name=CLOUD_FUNCTION_NAME,
    input_data={
        'filename': 'claims_{{ ds }}.json'
    },
    location=REGION,
    dag=dag
)

# 3. Validar ingesta
validate_ingestion = PythonOperator(
    task_id='validate_ingestion',
    python_callable=validate_ingestion_result,
    dag=dag
)

# 4. Crear cluster Dataproc
create_cluster = DataprocCreateClusterOperator(
    task_id='create_dataproc_cluster',
    cluster_name=DATAPROC_CLUSTER_NAME,
    project_id=PROJECT_ID,
    region=REGION,
    cluster_config={
        'master_config': {
            'num_instances': 1,
            'machine_type_uri': 'n1-standard-4'
        },
        'worker_config': {
            'num_instances': 2,
            'machine_type_uri': 'n1-standard-4'
        },
        'software_config': {
            'image_version': '2.1-debian11'
        }
    },
    dag=dag
)

# 5. Job PySpark
submit_pyspark_job = DataprocSubmitJobOperator(
    task_id='bronze_to_silver_transformation',
    job={
        'reference': {
            'project_id': PROJECT_ID
        },
        'placement': {
            'cluster_name': DATAPROC_CLUSTER_NAME
        },
        'pyspark_job': {
            'main_python_file_uri': f'gs://{GCS_BUCKET}/jobs/bronze_to_silver_transform.py',
            'args': [PROJECT_ID, GCS_BUCKET],
            'properties': {
                'spark.executor.cores': '4',
                'spark.driver.cores': '4',
                'spark.executor.memory': '8g',
                'spark.driver.memory': '8g'
            }
        }
    },
    region=REGION,
    project_id=PROJECT_ID,
    dag=dag
)

# 6. Eliminar cluster
delete_cluster = DataprocDeleteClusterOperator(
    task_id='delete_dataproc_cluster',
    cluster_name=DATAPROC_CLUSTER_NAME,
    project_id=PROJECT_ID,
    region=REGION,
    trigger_rule='all_done',
    dag=dag
)

# 7. Stored Procedure
execute_stored_procedure = BigQueryInsertJobOperator(
    task_id='silver_to_gold_business_rules',
    configuration={
        'query': {
            'query': f'CALL `{PROJECT_ID}.retail_claims_gold.sp_silver_to_gold_transformation`()',
            'useLegacySql': False
        }
    },
    location=REGION,
    dag=dag
)

# 8. Fin
log_end = PythonOperator(
    task_id='log_pipeline_end',
    python_callable=log_pipeline_end,
    dag=dag
)

# Dependencias
log_start >> ingest_sftp >> validate_ingestion >> create_cluster >> \
    submit_pyspark_job >> delete_cluster >> execute_stored_procedure >> log_end
