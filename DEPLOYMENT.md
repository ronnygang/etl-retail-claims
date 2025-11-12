# DEPLOYMENT.md - Runbook de Despliegue Manual

## 📋 Objetivo

Guía paso a paso para desplegar manualmente el pipeline ETL en caso de que Cloud Build falle o requieras intervención manual.

---

## ✅ Pre-requisitos

```bash
# Verificar que tengas:
- gcloud CLI instalado y autenticado
- git configurado
- Python 3.9+
- Acceso a GCP project

# Configurar proyecto
PROJECT_ID="tu-proyecto-gcp"
REGION="us-central1"
ZONE="us-central1-a"
gcloud config set project $PROJECT_ID
gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
```

---

## 🚀 1. Despliegue de BigQuery (Schemas y Stored Procedures)

### 1.1 Pre-requisitos BigQuery

```bash
# Variables
PROJECT_ID=$(gcloud config get-value project)
DATASET_BRONZE="retail_claims_bronze"
DATASET_SILVER="retail_claims_silver"
DATASET_GOLD="retail_claims_gold"

# Verificar que los datasets existan
bq ls
```

### 1.2 Crear Datasets (si no existen)

```bash
# Bronze Dataset
bq mk --dataset \
  --location=us-central1 \
  --description="Bronze layer - Raw claims data" \
  $DATASET_BRONZE

# Silver Dataset
bq mk --dataset \
  --location=us-central1 \
  --description="Silver layer - Cleaned and validated data" \
  $DATASET_SILVER

# Gold Dataset
bq mk --dataset \
  --location=us-central1 \
  --description="Gold layer - Business rules applied" \
  $DATASET_GOLD
```

### 1.3 Desplegar Schemas

```bash
# Ejecutar script de despliegue
python scripts/deploy_bigquery.py --project=$PROJECT_ID

# O manualmente:

# Bronze External Table
bq mk --table \
  --external_table_definition=bigquery/schemas/bronze_external_table.sql \
  $DATASET_BRONZE.retail_claims_raw

# Silver Table
bq mk --table \
  bigquery/schemas/silver_schema.sql \
  $DATASET_SILVER.retail_claims_cleaned

# Gold Table
bq mk --table \
  bigquery/schemas/gold_schema.sql \
  $DATASET_GOLD.retail_claims_processed
```

### 1.4 Desplegar Stored Procedure

```bash
# Crear Stored Procedure
bq query --use_legacy_sql=false \
  --parameter_types=target_date:DATE < \
  bigquery/stored_procedures/silver_to_gold_business_rules.sql
```

### 1.5 Verificar Despliegue

```bash
# Ver datasets
bq ls

# Ver tablas en cada dataset
bq ls $DATASET_BRONZE
bq ls $DATASET_SILVER
bq ls $DATASET_GOLD

# Ver stored procedures
bq ls --routines $DATASET_GOLD
```

---

## 🐳 2. Despliegue de Cloud Function (SFTP Ingestion)

### 2.1 Pre-requisitos

```bash
# Variables
FUNCTION_NAME="ingest-sftp-to-gcs"
REGION="us-central1"
RUNTIME="python39"
ENTRY_POINT="ingest_sftp_to_gcs"

# Verificar archivos
ls -la cloud_functions/ingest_sftp_to_gcs/
# Debe tener: main.py, requirements.txt, Dockerfile
```

### 2.2 Opción A: Despliegue Directo (recomendado)

```bash
PROJECT_ID=$(gcloud config get-value project)

# Desplegar Cloud Function
gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=$RUNTIME \
  --region=$REGION \
  --source=cloud_functions/ingest_sftp_to_gcs \
  --entry-point=$ENTRY_POINT \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --timeout=540 \
  --max-instances=10 \
  --set-env-vars \
    GCS_BUCKET=retail-claims-etl,\
    SFTP_HOST=sftp.ejemplo.com,\
    DATASET_ID=retail_claims_bronze,\
    TABLE_ID=retail_claims_raw
```

### 2.3 Opción B: Despliegue con Variables de Entorno

```bash
# Crear archivo .env
cat > .env << EOF
GCS_BUCKET=retail-claims-etl
SFTP_HOST=sftp.ejemplo.com
SFTP_PORT=22
DATASET_ID=retail_claims_bronze
TABLE_ID=retail_claims_raw
EOF

# Desplegar
gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=$RUNTIME \
  --region=$REGION \
  --source=cloud_functions/ingest_sftp_to_gcs \
  --entry-point=$ENTRY_POINT \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --env-vars-file=.env
```

### 2.4 Opción C: Usar Secret Manager

```bash
# Crear secreto
echo -n "tu-password" | gcloud secrets create sftp-password --data-file=-

# Desplegar con secreto
gcloud functions deploy $FUNCTION_NAME \
  --gen2 \
  --runtime=$RUNTIME \
  --region=$REGION \
  --source=cloud_functions/ingest_sftp_to_gcs \
  --entry-point=$ENTRY_POINT \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --secret=sftp-password=/run/cloud/secret/sftp-password
```

### 2.5 Verificar Despliegue

```bash
# Ver Cloud Functions
gcloud functions list --gen2 --region=$REGION

# Ver detalles
gcloud functions describe $FUNCTION_NAME --gen2 --region=$REGION

# Ver logs
gcloud functions logs read $FUNCTION_NAME --gen2 --region=$REGION --limit=50
```

### 2.6 Probar Cloud Function

```bash
# Obtener la URL
FUNCTION_URL=$(gcloud functions describe $FUNCTION_NAME \
  --gen2 --region=$REGION --format='value(serviceConfig.uri)')

# Hacer request
curl -X POST $FUNCTION_URL \
  -H "Content-Type: application/json" \
  -d '{}'

# Ver respuesta (revisarás logs)
gcloud functions logs read $FUNCTION_NAME --gen2 --region=$REGION --limit=5
```

---

## 🔧 3. Despliegue de Dataproc Job (PySpark Transformation)

### 3.1 Pre-requisitos

```bash
# Variables
DATAPROC_CLUSTER="retail-claims-cluster"
DATAPROC_ZONE="us-central1-a"
SPARK_JOB_FILE="dataproc/jobs/bronze_to_silver_transform.py"
GCS_BUCKET="retail-claims-etl"

# Verificar archivos
ls -la $SPARK_JOB_FILE
```

### 3.2 Crear Cluster Dataproc (si no existe)

```bash
gcloud dataproc clusters create $DATAPROC_CLUSTER \
  --region=us-central1 \
  --zone=$DATAPROC_ZONE \
  --master-machine-type=n1-standard-4 \
  --worker-machine-type=n1-standard-4 \
  --num-workers=2 \
  --image-version=2.1-debian11 \
  --enable-component-gateway \
  --scopes=https://www.googleapis.com/auth/cloud-platform
```

### 3.3 Subir Job a GCS

```bash
gsutil cp $SPARK_JOB_FILE gs://$GCS_BUCKET/spark-jobs/

# Verificar
gsutil ls gs://$GCS_BUCKET/spark-jobs/
```

### 3.4 Ejecutar Job

```bash
gcloud dataproc jobs submit pyspark \
  gs://$GCS_BUCKET/spark-jobs/bronze_to_silver_transform.py \
  --cluster=$DATAPROC_CLUSTER \
  --region=us-central1 \
  --jars=gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar \
  -- \
  --input_table=retail_claims_bronze.retail_claims_raw \
  --output_table=retail_claims_silver.retail_claims_cleaned \
  --project_id=$(gcloud config get-value project)
```

### 3.5 Monitorear Job

```bash
# Ver jobs en cluster
gcloud dataproc jobs list --cluster=$DATAPROC_CLUSTER --region=us-central1

# Ver logs del job
JOB_ID="tu-job-id"
gcloud dataproc jobs wait $JOB_ID --region=us-central1

# Ver logs en driver
gcloud logging read \
  "resource.type=dataproc_cluster AND labels.cluster_name=$DATAPROC_CLUSTER" \
  --limit=50
```

### 3.6 Limpiar Cluster (opcional)

```bash
# Eliminar cluster cuando no lo uses
gcloud dataproc clusters delete $DATAPROC_CLUSTER \
  --region=us-central1 \
  --quiet
```

---

## 📅 4. Despliegue de Cloud Composer (Airflow)

### 4.1 Pre-requisitos

```bash
# Variables
COMPOSER_ENV="retail-claims-composer"
COMPOSER_REGION="us-central1"
COMPOSER_ZONE="us-central1-a"
DAG_FILE="dags/retail_claims_etl_dag.py"

# Verificar
ls -la $DAG_FILE
```

### 4.2 Crear Ambiente Composer (si no existe)

```bash
gcloud composer environments create $COMPOSER_ENV \
  --location=$COMPOSER_REGION \
  --node-count=3 \
  --machine-type=n1-standard-4 \
  --python-version=3 \
  --env-variables=GCS_BUCKET=retail-claims-etl,DATASET_ID=retail_claims_bronze
```

### 4.3 Desplegar DAG

```bash
# Obtener bucket de Composer
BUCKET=$(gcloud composer environments describe $COMPOSER_ENV \
  --location=$COMPOSER_REGION \
  --format='value(config.dagGcsPrefix)' | sed 's|/dags||')

# Copiar DAG
gsutil cp $DAG_FILE gs://$BUCKET/dags/

# Verificar
gsutil ls gs://$BUCKET/dags/
```

### 4.4 Verificar DAG en Airflow

```bash
# Acceder a Airflow UI
gcloud composer environments run $COMPOSER_ENV \
  --location=$COMPOSER_REGION \
  dags list

# Ver detalles del DAG
gcloud composer environments run $COMPOSER_ENV \
  --location=$COMPOSER_REGION \
  dags info retail_claims_etl_pipeline
```

### 4.5 Triggear Ejecución Manual

```bash
# Ejecutar DAG manualmente
gcloud composer environments run $COMPOSER_ENV \
  --location=$COMPOSER_REGION \
  dags test retail_claims_etl_pipeline 2025-11-12

# Ver logs
gcloud logging read \
  "resource.type=cloud_composer_environment AND resource.labels.environment_name=$COMPOSER_ENV" \
  --limit=50
```

---

## 📊 5. Verificación Post-Despliegue

### 5.1 Verificar Todos los Componentes

```bash
#!/bin/bash
echo "=== Verificando Cloud Function ==="
gcloud functions describe ingest-sftp-to-gcs --gen2 --region=us-central1

echo -e "\n=== Verificando BigQuery Datasets ==="
bq ls

echo -e "\n=== Verificando Dataproc Cluster ==="
gcloud dataproc clusters list --region=us-central1

echo -e "\n=== Verificando Cloud Composer ==="
gcloud composer environments list --locations=us-central1

echo -e "\n=== Verificando GCS Buckets ==="
gsutil ls | grep retail-claims
```

### 5.2 Test End-to-End

```bash
# 1. Verificar que GCS bucket existe
gsutil ls gs://retail-claims-etl/

# 2. Copiar archivo de prueba a SFTP
# (Esto depende de tu servidor SFTP)

# 3. Triggerear Cloud Function
FUNCTION_URL=$(gcloud functions describe ingest-sftp-to-gcs \
  --gen2 --region=us-central1 --format='value(serviceConfig.uri)')

curl -X POST $FUNCTION_URL -H "Content-Type: application/json" -d '{}'

# 4. Verificar que el archivo llegó a GCS
gsutil ls gs://retail-claims-etl/bronze/

# 5. Ejecutar Dataproc job manualmente
# (Ver sección 3 arriba)

# 6. Verificar que los datos llegaron a Silver
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM retail_claims_silver.retail_claims_cleaned'

# 7. Ejecutar Stored Procedure
bq query --use_legacy_sql=false \
  'CALL retail_claims_gold.sp_silver_to_gold_transformation(CURRENT_DATE())'

# 8. Verificar Gold layer
bq query --use_legacy_sql=false \
  'SELECT COUNT(*) FROM retail_claims_gold.retail_claims_processed'
```

---

## 🚨 6. Rollback (Revertir Cambios)

### 6.1 Rollback de Cloud Function

```bash
# Ver versiones disponibles
gcloud functions list --gen2

# Revertir a versión anterior
gcloud functions deploy ingest-sftp-to-gcs \
  --gen2 \
  --runtime=python39 \
  --region=us-central1 \
  --source=cloud_functions/ingest_sftp_to_gcs \
  --entry-point=ingest_sftp_to_gcs \
  --trigger-http \
  --allow-unauthenticated
```

### 6.2 Rollback de BigQuery

```bash
# Las tablas de BigQuery se pueden restaurar desde backups
# Opción 1: Usar snapshot de tabla
bq cp \
  retail_claims_silver.retail_claims_cleaned@-3600000 \
  retail_claims_silver.retail_claims_cleaned_backup

# Opción 2: Reejecutar Stored Procedure con fecha anterior
bq query --use_legacy_sql=false \
  'CALL retail_claims_gold.sp_silver_to_gold_transformation(DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY))'
```

### 6.3 Rollback de DAG

```bash
# Pausar DAG en Airflow
gcloud composer environments run $COMPOSER_ENV \
  --location=us-central1 \
  dags pause retail_claims_etl_pipeline

# Reemplazar DAG con versión anterior
gsutil cp gs://backup-dags/retail_claims_etl_dag.py.v1 \
  gs://$COMPOSER_BUCKET/dags/retail_claims_etl_dag.py

# Reanudar DAG
gcloud composer environments run $COMPOSER_ENV \
  --location=us-central1 \
  dags unpause retail_claims_etl_pipeline
```

---

## 🔍 7. Troubleshooting

### Problema: Cloud Function no se ejecuta

```bash
# Ver logs
gcloud functions logs read ingest-sftp-to-gcs --gen2 --region=us-central1 --limit=50

# Verificar permisos
gcloud functions describe ingest-sftp-to-gcs --gen2 --region=us-central1

# Probar manualmente
python cloud_functions/ingest_sftp_to_gcs/main.py
```

### Problema: Dataproc job falla

```bash
# Ver logs detallados
gcloud dataproc jobs describe JOB_ID --region=us-central1

# Ver logs en driver
gsutil cat gs://dataproc-staging-BUCKET/google-cloud-dataproc-metainfo/JOB_ID/jobs/JOB_ID/google.cloudresourcemanager.Job

# Reejecutar job
gcloud dataproc jobs submit pyspark ...
```

### Problema: BigQuery query falla

```bash
# Ver error
bq query --use_legacy_sql=false \
  'SELECT * FROM retail_claims_bronze.retail_claims_raw LIMIT 1'

# Verificar schema
bq show --schema retail_claims_bronze.retail_claims_raw

# Reparar tabla
bq repair table retail_claims_bronze.retail_claims_raw
```

### Problema: DAG no aparece en Airflow

```bash
# Verificar que el DAG está en el bucket
gsutil ls gs://$COMPOSER_BUCKET/dags/ | grep retail_claims

# Refrescar UI
gcloud composer environments run $COMPOSER_ENV \
  --location=us-central1 \
  dags refresh

# Ver logs
gcloud logging read \
  "resource.type=cloud_composer_environment" \
  --limit=20
```

---

## 📈 8. Monitoreo Post-Despliegue

### Crear Alertas en Cloud Monitoring

```bash
# Alerta para Cloud Function timeouts
gcloud monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Cloud Function Timeouts" \
  --condition-display-name="Function timeout" \
  --condition-threshold-value=1 \
  --condition-threshold-duration=300s
```

### Ver Métricas

```bash
# Cloud Function
gcloud monitoring time-series list \
  --filter='resource.type=cloud_function AND metric.type=cloudfunctions.googleapis.com/function/execution_count'

# Dataproc
gcloud monitoring time-series list \
  --filter='resource.type=dataproc_cluster'

# BigQuery
bq query --use_legacy_sql=false \
  'SELECT * FROM region-us-central1.INFORMATION_SCHEMA.JOBS_BY_PROJECT WHERE project_id="'"$(gcloud config get-value project)"'"'
```

---

## ✅ Checklist de Despliegue

- [ ] Datasets BigQuery creados
- [ ] Schemas BigQuery desplegados
- [ ] Stored Procedures BigQuery desplegadas
- [ ] Cloud Function desplegada y probada
- [ ] Dataproc cluster creado
- [ ] Spark job subido a GCS
- [ ] Cloud Composer ambiente creado
- [ ] DAG desplegado en Composer
- [ ] Test end-to-end pasado
- [ ] Alertas configuradas
- [ ] Documentación actualizada

---

**Generado**: 2025-11-12

## 📞 Soporte

Si encuentras problemas:
1. Revisa los logs: `gcloud logging read ...`
2. Consulta la sección de Troubleshooting
3. Revisa la documentación en la carpeta docs/
4. Abre un issue en GitHub
