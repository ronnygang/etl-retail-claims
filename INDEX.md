# 📑 Índice de Archivos - Proyecto ETL Retail Claims

## 📁 Estructura Completa del Proyecto

### 🏠 Raíz del Proyecto
```
etl-retail-claims/
├── .github/
│   └── instructions/
│       └── instructions.instructions.md     # Guía de desarrollo en español
├── .env.example                             # Variables de entorno de ejemplo
├── .gitignore                               # Archivos a ignorar en git
├── README.md                                # Documentación principal
├── QUICKSTART.md                            # Guía de inicio rápido
├── CONTRIBUTING.md                          # Guía de contribución
├── CICD.md                                  # Documentación de Cloud Build CI/CD
├── GITHUB_INTEGRATION.md                    # Integración con GitHub
├── DEPLOYMENT.md                            # Runbook de despliegue manual
├── MONITORING.md                            # Monitoreo y alertas
├── requirements.txt                         # Dependencias Python
└── sample_claims.jsonl                      # Datos de ejemplo
```

### ☁️ Google Cloud Platform

#### Cloud Functions (Ingesta SFTP)
```
cloud_functions/
└── ingest_sftp_to_gcs/
    ├── main.py                              # Código principal
    └── requirements.txt                     # Dependencias específicas
```
**Propósito**: Descargar JSON desde SFTP y cargar a GCS
**Entrada**: Archivos JSON desde servidor SFTP
**Salida**: Archivos JSON en `gs://bucket/bronze/retail-claims/`

#### Google Cloud Storage (GCS)
- **Estructura**: `gs://retail-claims-etl/bronze/retail-claims/{YYYY}/{MM}/{DD}/`
- **Datos**: Archivos JSON crudos (capa Bronze)
- **Formato**: NEWLINE_DELIMITED_JSON

#### BigQuery

##### Capa Bronze (Datos Raw)
```
bigquery/schemas/bronze_external_table.sql
```
- **Dataset**: `retail_claims_bronze`
- **Tabla**: `claims_external` (tabla externa referenciando GCS)
- **Propósito**: Fuente de datos para transformaciones

##### Capa Silver (Datos Estructurados)
```
bigquery/schemas/silver_schema.sql
```
- **Dataset**: `retail_claims_silver`
- **Tabla**: `claims_structured`
- **Transformaciones**: Limpieza, estandarización, validación de calidad
- **Particionamiento**: Por `processing_date`
- **Clustering**: Por `customer_id`, `store_id`

##### Capa Gold (Reglas de Negocio)
```
bigquery/schemas/gold_schema.sql
```
- **Dataset**: `retail_claims_gold`
- **Tabla**: `claims_business_rules`
- **Transformaciones**: Clasificación, escalación, score de riesgo
- **Particionamiento**: Por `processing_date`
- **Clustering**: Por `customer_id`, `claim_priority`, `requires_escalation`

##### Stored Procedures
```
bigquery/stored_procedures/silver_to_gold_business_rules.sql
```
- **Nombre**: `sp_silver_to_gold_transformation()`
- **Reglas**:
  - Clasificación por monto (LOW, MEDIUM, HIGH, CRITICAL)
  - Escalación automática (PENDING > 7 días o monto > $2000)
  - Score de riesgo (0.1 - 1.5)
  - Categorización por período

### 🔄 Dataproc (PySpark)

#### Jobs PySpark
```
dataproc/jobs/
└── bronze_to_silver_transform.py            # Transformación Bronze→Silver
```
**Propósito**: Procesar datos de Bronze, aplicar transformaciones, escribir en Silver
**Entrada**: Tabla externa `claims_external` (Bronze)
**Salida**: Tabla `claims_structured` (Silver)
**Transformaciones**:
1. Lectura desde BigQuery
2. Limpieza y estandarización
3. Agregación de columnas técnicas
4. Validación de calidad
5. Escritura en BigQuery

#### Configuración
```
dataproc/configs/
└── dataproc_cluster_config.yaml             # Config del cluster
```
**Especificaciones**:
- Master: `n1-standard-4` (1 instancia)
- Workers: `n1-standard-4` (2 instancias)
- Spark: 4 cores, 8GB RAM por executor

### 🎯 Orquestación (Cloud Composer / Airflow)

#### DAGs
```
dags/
└── retail_claims_etl_dag.py                 # DAG principal
```
**Nombre**: `retail_claims_etl_pipeline`
**Cronograma**: Diariamente a las 2:00 AM UTC
**Tareas**:
1. `log_pipeline_start` - Registrar inicio
2. `ingest_sftp_to_gcs` - Ejecutar Cloud Function
3. `validate_ingestion` - Validar ingesta exitosa
4. `create_dataproc_cluster` - Crear cluster Spark
5. `bronze_to_silver_transformation` - Ejecutar job PySpark
6. `delete_dataproc_cluster` - Eliminar cluster
7. `silver_to_gold_business_rules` - Ejecutar Stored Procedure
8. `log_pipeline_end` - Registrar finalización

### 🧪 Testing

#### Tests Unitarios
```
tests/unit/
├── __init__.py
└── test_transformations.py                  # Tests de lógica de negocio
```
**Cobertura**:
- Clasificación de prioridad (LOW, MEDIUM, HIGH, CRITICAL)
- Lógica de escalación
- Cálculo de score de riesgo

#### Tests de Integración
```
tests/integration/
└── __init__.py
```
(Espacio para pruebas end-to-end con GCP)

### ⚙️ Configuración

#### Variables de Entorno
```
.env.example                                 # Plantilla de variables
```
**Variables principales**:
- `GCP_PROJECT_ID` - ID del proyecto GCP
- `GCS_BUCKET_NAME` - Nombre del bucket
- `SFTP_HOST`, `SFTP_USERNAME`, `SFTP_PASSWORD` - Credenciales SFTP
- `BQ_DATASET_*` - Nombres de datasets BigQuery

#### Configuración de Desarrollo
```
config/
├── environment.yaml                         # Config general del proyecto
└── secrets_template.yaml                    # Plantilla de secretos
```

### 📚 Documentación

```
README.md                                    # Documentación completa
QUICKSTART.md                                # Guía de inicio rápido (5 min)
CONTRIBUTING.md                              # Guía de contribución y desarrollo
```

### 🛠️ Scripts

#### Despliegue Automatizado
```
scripts/
└── deploy_gcp.sh                            # Script de despliegue a GCP
```
**Funciones**:
- Crear buckets GCS
- Crear datasets BigQuery
- Ejecutar scripts DDL
- Desplegar Cloud Function
- Subir job Spark
- Crear entorno Composer
- Subir DAG

### 📊 Monitoreo

```
monitoring/                                  # (Directorio para alertas)
```

---

## 📋 Listado de Archivos Creados

### Python (`.py`)
- `cloud_functions/ingest_sftp_to_gcs/main.py` - Cloud Function
- `dataproc/jobs/bronze_to_silver_transform.py` - Job PySpark
- `dags/retail_claims_etl_dag.py` - DAG Airflow
- `tests/unit/test_transformations.py` - Tests unitarios
- `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py` - Paquetes Python

### SQL (`.sql`)
- `bigquery/schemas/bronze_external_table.sql` - Tabla externa Bronze
- `bigquery/schemas/silver_schema.sql` - Tabla Silver
- `bigquery/schemas/gold_schema.sql` - Tabla Gold
- `bigquery/stored_procedures/silver_to_gold_business_rules.sql` - Stored Procedure

### YAML (`.yaml`)
- `config/environment.yaml` - Configuración del proyecto
- `config/secrets_template.yaml` - Plantilla de secretos
- `dataproc/configs/dataproc_cluster_config.yaml` - Config de Dataproc

### Markdown (`.md`)
- `README.md` - Documentación principal
- `QUICKSTART.md` - Inicio rápido
- `CONTRIBUTING.md` - Guía de contribución
- `INDEX.md` - Este archivo

### Configuración
- `.env.example` - Variables de entorno
- `.gitignore` - Archivos a ignorar
- `requirements.txt` - Dependencias Python

### Datos
- `sample_claims.jsonl` - Datos de ejemplo en JSONL

### Shell (`.sh`)
- `scripts/deploy_gcp.sh` - Script de despliegue

---

## 🔗 Dependencias Entre Componentes

```
SFTP
  ↓
Cloud Function (main.py)
  ↓
GCS (Bronze)
  ↓
BigQuery External Table (bronze_external_table.sql)
  ↓
PySpark Job (bronze_to_silver_transform.py)
  ↓
BigQuery Silver Table (silver_schema.sql)
  ↓
Stored Procedure (silver_to_gold_business_rules.sql)
  ↓
BigQuery Gold Table (gold_schema.sql)
```

---

## 📈 Matriz de Datos

| Componente | Entrada | Salida | Formato | Partición |
|-----------|---------|--------|--------|-----------|
| Cloud Function | SFTP JSON | GCS | JSON | `YYYY/MM/DD/` |
| Bronze (External) | GCS | BigQuery Query | JSON | - |
| Dataproc Job | BigQuery Bronze | BigQuery Silver | Parquet | `processing_date` |
| Gold Procedure | BigQuery Silver | BigQuery Gold | Parquet | `processing_date` |

---

## ✅ Checklist de Verificación

- [x] Directorios creados
- [x] Cloud Function implementada
- [x] Esquemas BigQuery definidos
- [x] Job PySpark implementado
- [x] DAG Airflow configurado
- [x] Tests unitarios incluidos
- [x] Documentación completa
- [x] Scripts de despliegue
- [x] Ejemplos de datos
- [x] Configuración de secretos

---

## 🚀 Próximos Pasos

1. **Configurar credenciales GCP**
   ```bash
   gcloud auth application-default login
   ```

2. **Llenar archivo `.env`**
   ```bash
   cp .env.example .env
   vim .env
   ```

3. **Ejecutar tests locales**
   ```bash
   pytest tests/unit/ -v
   ```

4. **Desplegar en GCP**
   ```bash
   bash scripts/deploy_gcp.sh your-project-id
   ```

---

**Documento generado**: 2024-01-01
**Última actualización**: 2025-11-12
