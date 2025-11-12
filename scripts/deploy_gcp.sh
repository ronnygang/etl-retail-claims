#!/bin/bash

# Script de despliegue para proyecto ETL Retail Claims en GCP
# Este script automatiza la creación de recursos en Google Cloud

set -e

echo "🚀 Iniciando despliegue del proyecto ETL Retail Claims..."

# Variables de configuración
PROJECT_ID="${1:-your-gcp-project-id}"
REGION="us-central1"
ZONE="us-central1-a"
GCS_BUCKET="retail-claims-etl"
DATAPROC_CLUSTER="retail-claims-cluster"
COMPOSER_ENV="retail-etl"

echo "📋 Configuración:"
echo "  - PROJECT_ID: $PROJECT_ID"
echo "  - REGION: $REGION"
echo "  - GCS_BUCKET: $GCS_BUCKET"

# 1. Validar que gcloud está configurado
echo "✓ Validando gcloud CLI..."
gcloud config set project $PROJECT_ID

# 2. Crear buckets GCS
echo "✓ Creando buckets GCS..."
gsutil mb -p $PROJECT_ID -l $REGION gs://$GCS_BUCKET || echo "  ⚠️  Bucket ya existe"
gsutil mb -p $PROJECT_ID -l $REGION gs://${GCS_BUCKET}-temp || echo "  ⚠️  Bucket temporal ya existe"

# 3. Crear datasets BigQuery
echo "✓ Creando datasets BigQuery..."
bq mk --dataset \
  --location=$REGION \
  --description="Capa Bronze - Datos raw" \
  retail_claims_bronze || echo "  ⚠️  Dataset Bronze ya existe"

bq mk --dataset \
  --location=$REGION \
  --description="Capa Silver - Datos estructurados" \
  retail_claims_silver || echo "  ⚠️  Dataset Silver ya existe"

bq mk --dataset \
  --location=$REGION \
  --description="Capa Gold - Reglas de negocio" \
  retail_claims_gold || echo "  ⚠️  Dataset Gold ya existe"

# 4. Ejecutar scripts DDL de BigQuery
echo "✓ Creando tablas en BigQuery..."

# Reemplazar placeholder de project_id en scripts
sed -i "s/{project_id}/$PROJECT_ID/g" bigquery/schemas/*.sql
sed -i "s/{gcs_bucket}/$GCS_BUCKET/g" bigquery/schemas/*.sql
sed -i "s/{project_id}/$PROJECT_ID/g" bigquery/stored_procedures/*.sql

# Ejecutar scripts
bq query --use_legacy_sql=false < bigquery/schemas/bronze_external_table.sql
bq query --use_legacy_sql=false < bigquery/schemas/silver_schema.sql
bq query --use_legacy_sql=false < bigquery/schemas/gold_schema.sql
bq query --use_legacy_sql=false < bigquery/stored_procedures/silver_to_gold_business_rules.sql

# 5. Subir job PySpark a GCS
echo "✓ Subiendo job PySpark..."
gsutil cp dataproc/jobs/bronze_to_silver_transform.py gs://$GCS_BUCKET/jobs/

# 6. Desplegar Cloud Function
echo "✓ Desplegando Cloud Function..."
gcloud functions deploy ingest-sftp-to-gcs \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point=ingest_sftp_to_gcs \
  --source=cloud_functions/ingest_sftp_to_gcs \
  --region=$REGION \
  --set-env-vars SFTP_HOST=localhost,SFTP_USERNAME=user,SFTP_PASSWORD=pass,GCS_BUCKET=$GCS_BUCKET

# 7. Crear entorno Cloud Composer
echo "✓ Creando entorno Cloud Composer..."
gcloud composer environments create $COMPOSER_ENV \
  --location $REGION \
  --python-version 3 || echo "  ⚠️  Entorno Composer ya existe"

# 8. Subir DAG
echo "✓ Subiendo DAG a Cloud Composer..."
gsutil cp dags/retail_claims_etl_dag.py gs://${REGION}-${COMPOSER_ENV}-bucket/dags/

echo ""
echo "✅ Despliegue completado exitosamente!"
echo ""
echo "📌 Próximos pasos:"
echo "1. Configurar variables de entorno en Cloud Composer:"
echo "   gcloud composer environments update $COMPOSER_ENV --location $REGION --update-env-variables GCP_PROJECT_ID=$PROJECT_ID,GCS_BUCKET_NAME=$GCS_BUCKET"
echo ""
echo "2. Verificar el DAG:"
echo "   gcloud composer environments run $COMPOSER_ENV --location $REGION dags list"
echo ""
echo "3. Configurar las credenciales SFTP en Cloud Function"
echo ""
echo "🎉 ¡Tu pipeline ETL está listo!"
