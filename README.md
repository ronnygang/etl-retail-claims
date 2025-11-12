# Proyecto ETL - Retail Claims 🚀

Pipeline de ingeniería de datos para procesamiento de reclamos retail en Google Cloud Platform.

## 📋 Arquitectura

```
SFTP → Cloud Function → GCS (Bronze)
                          ↓
                    External Table (BigQuery)
                          ↓
                    Dataproc (PySpark)
                          ↓
                    BigQuery (Silver - Estructurado)
                          ↓
                    Stored Procedure
                          ↓
                    BigQuery (Gold - Reglas de Negocio)
```

## 🏗️ Componentes

### 1. **Cloud Function** - Ingesta SFTP
- Lee archivos JSON desde servidor SFTP
- Valida formato JSON
- Carga a Google Cloud Storage (capa Bronze)

### 2. **Tabla Externa BigQuery** - Capa Bronze
- Referencia archivos JSON en GCS
- Base para transformaciones posteriores

### 3. **Job Dataproc (PySpark)** - Bronze a Silver
- Limpieza y estandarización de datos
- Agregación de columnas técnicas
- Validación de calidad de datos

### 4. **Stored Procedure BigQuery** - Silver a Gold
- Aplica reglas de negocio específicas
- Clasifica reclamos por prioridad
- Calcula score de riesgo
- Determina escalaciones

### 5. **DAG Cloud Composer** - Orquestación
- Orquestra todo el flujo diariamente
- Manejo automático de errores y reintentos
- Logs centralizados

## 📦 Instalación

### Requisitos
- Python 3.8+
- gcloud CLI configurada
- Credenciales GCP con permisos necesarios

### Setup Local

```bash
# 1. Clonar repositorio
git clone <repo-url>
cd etl-retail-claims

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Copiar archivo de secretos
cp config/secrets_template.yaml config/secrets.yaml
# Editar config/secrets.yaml con valores reales
```

## ⚙️ Configuración en GCP

### 1. Crear Bucket GCS

```bash
gsutil mb gs://retail-claims-etl
gsutil mb gs://retail-claims-etl-temp
```

### 2. Crear datasets BigQuery

```bash
bq mk --dataset --location=us-central1 retail_claims_bronze
bq mk --dataset --location=us-central1 retail_claims_silver
bq mk --dataset --location=us-central1 retail_claims_gold
```

### 3. Ejecutar scripts DDL

```bash
# Bronze
bq query --use_legacy_sql=false < bigquery/schemas/bronze_external_table.sql

# Silver
bq query --use_legacy_sql=false < bigquery/schemas/silver_schema.sql

# Gold
bq query --use_legacy_sql=false < bigquery/schemas/gold_schema.sql

# Stored Procedure
bq query --use_legacy_sql=false < bigquery/stored_procedures/silver_to_gold_business_rules.sql
```

### 4. Desplegar Cloud Function

```bash
gcloud functions deploy ingest-sftp-to-gcs \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point=ingest_sftp_to_gcs \
  --source=cloud_functions/ingest_sftp_to_gcs \
  --set-env-vars SFTP_HOST=$SFTP_HOST,SFTP_USERNAME=$SFTP_USER,GCS_BUCKET=retail-claims-etl
```

### 5. Subir job PySpark

```bash
gsutil cp dataproc/jobs/bronze_to_silver_transform.py gs://retail-claims-etl/jobs/
```

### 6. Desplegar DAG en Cloud Composer

```bash
export ENVIRONMENT_NAME=retail-etl
export LOCATION=us-central1

# Crear entorno (primera vez)
gcloud composer environments create $ENVIRONMENT_NAME \
  --location $LOCATION \
  --python-version 3

# Subir DAG
gsutil cp dags/retail_claims_etl_dag.py \
  gs://us-central1-$ENVIRONMENT_NAME-bucket/dags/
```

## 🧪 Testing

```bash
# Ejecutar tests unitarios
pytest tests/unit/ -v

# Ejecutar con coverage
pytest tests/unit/ --cov=. --cov-report=html

# Tests de integración (requiere GCP configurado)
pytest tests/integration/ -v
```

## 📊 Monitoreo

### Cloud Logging
```bash
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=ingest-sftp-to-gcs" \
  --limit 50 \
  --format json
```

### Cloud Composer
```bash
gcloud composer environments run $ENVIRONMENT_NAME \
  --location $LOCATION \
  dags list

gcloud composer environments run $ENVIRONMENT_NAME \
  --location $LOCATION \
  dags test retail_claims_etl_pipeline 2024-01-01
```

### BigQuery
```bash
# Ver historial de cargas
bq ls -j

# Inspeccionar tabla
bq show -j <job_id>

# Verificar datos en Gold
bq query --use_legacy_sql=false '
SELECT claim_priority, COUNT(*) as count 
FROM `project.retail_claims_gold.claims_business_rules`
WHERE processing_date = CURRENT_DATE()
GROUP BY claim_priority
'
```

## 📈 Reglas de Negocio (Capa Gold)

### Clasificación por Monto
- **LOW**: ≤ $100
- **MEDIUM**: $100 - $500
- **HIGH**: $500 - $2000
- **CRITICAL**: > $2000

### Escalación Automática
- Reclamos PENDING con más de 7 días
- Montos mayores a $2000

### Score de Riesgo
Basado en:
- Estado del reclamo (REJECTED=0.8, PENDING=0.6, APPROVED=0.2, CLOSED=0.1)
- Monto (multiplicador: >5000=1.5x, >1000=1.2x, otro=1.0x)

## 🔐 Seguridad

- Credenciales en `config/secrets.yaml` (no commitear)
- Usar Secret Manager para producción
- Encriptación en tránsito (SFTP/HTTPS)
- Encriptación en reposo (GCS/BigQuery)
- Audit logging habilitado

## 🚀 Próximos Pasos

- [ ] Implementar alertas en Cloud Monitoring
- [ ] Agregar validaciones de datos más complejas
- [ ] Automatizar reporte de métricas
- [ ] Integrar con sistemas de BI
- [ ] Implementar versionado de datos

## 📞 Contacto

Data Engineering Team - data-alerts@company.com

## 📝 Licencia

Propietario - Retail Company 2024
