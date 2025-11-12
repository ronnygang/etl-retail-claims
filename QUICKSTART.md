# Quick Start Guide - ETL Retail Claims

## 🚀 Comenzar en 5 minutos

### 1. Setup Local
```bash
# Clonar y configurar
git clone <repo-url> && cd etl-retail-claims
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && vim .env
```

### 2. Ejecutar Tests Locales
```bash
pytest tests/unit/ -v
```

### 3. Desplegar en GCP
```bash
bash scripts/deploy_gcp.sh your-project-id
```

---

## 📁 Archivos Importantes

| Archivo | Propósito |
|---------|-----------|
| `dags/retail_claims_etl_dag.py` | DAG principal de Airflow |
| `cloud_functions/ingest_sftp_to_gcs/main.py` | Función de ingesta |
| `dataproc/jobs/bronze_to_silver_transform.py` | Job de transformación Spark |
| `bigquery/stored_procedures/silver_to_gold_business_rules.sql` | Reglas de negocio |
| `config/environment.yaml` | Configuración general |
| `requirements.txt` | Dependencias Python |

---

## 🔄 Flujo del Pipeline

```
┌─────────────┐
│    SFTP     │ (archivo claims.json)
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────┐
│  Cloud Function                 │ (valida y sube)
│  ingest_sftp_to_gcs            │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  GCS - Bronze                   │ (gs://bucket/bronze/...)
│  (datos raw)                    │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  BigQuery                       │
│  Tabla Externa (Bronze)         │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  Dataproc - PySpark             │
│  bronze_to_silver_transform.py  │
│  (limpia y estructura)          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  BigQuery                       │
│  Tabla Silver                   │
│  (datos estructurados)          │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  BigQuery Stored Procedure      │
│  sp_silver_to_gold_transformation│
│  (reglas de negocio)            │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  BigQuery                       │
│  Tabla Gold                     │
│  (dados con reglas aplicadas)   │
└─────────────────────────────────┘
```

---

## 📊 Configuración de Datos

### Estructura de Entrada (JSON)
```json
{
  "claim_id": "CLM001",
  "customer_id": "CUST001",
  "store_id": "STORE001",
  "claim_date": "2024-01-15",
  "claim_amount": 150.50,
  "description": "Producto defectuoso",
  "status": "PENDING",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Columnas en Gold
- `claim_priority`: LOW, MEDIUM, HIGH, CRITICAL (basado en monto)
- `requires_escalation`: true/false (si es crítico o viejo)
- `risk_score`: 0.1 - 1.5 (basado en estado y monto)
- `period_category`: REGULAR, WEEKEND, HOLIDAY_SEASON, POST_HOLIDAY

---

## 🔧 Operaciones Comunes

### Ver Logs de Cloud Function
```bash
gcloud functions describe ingest-sftp-to-gcs --gen2 --region us-central1
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=ingest-sftp-to-gcs" --limit 50
```

### Ver DAG en Airflow
```bash
gcloud composer environments run retail-etl --location us-central1 dags list
gcloud composer environments run retail-etl --location us-central1 \
  dags test retail_claims_etl_pipeline 2024-01-01
```

### Consultar Datos en BigQuery
```bash
# Ver tablas
bq ls retail_claims_gold

# Ver datos recientes
bq query --use_legacy_sql=false '
SELECT * FROM `project.retail_claims_gold.claims_business_rules`
WHERE processing_date = CURRENT_DATE()
LIMIT 10
'

# Verificar calidad
bq query --use_legacy_sql=false '
SELECT 
  claim_priority,
  requires_escalation,
  COUNT(*) as count,
  AVG(risk_score) as avg_risk
FROM `project.retail_claims_gold.claims_business_rules`
WHERE processing_date = CURRENT_DATE()
GROUP BY claim_priority, requires_escalation
'
```

### Descargar Datos
```bash
# Exportar a CSV
bq extract retail_claims_gold.claims_business_rules \
  gs://bucket/export/claims_*.csv

# Descargar del bucket
gsutil cp gs://bucket/export/claims_*.csv ./data/
```

---

## 🚨 Troubleshooting

### Cloud Function no carga datos
1. Verificar credenciales SFTP
   ```bash
   gcloud functions describe ingest-sftp-to-gcs --gen2 --region us-central1
   ```

2. Ver logs
   ```bash
   gcloud logging read "resource.type=cloud_function" --limit 50 --format json
   ```

### Job Spark falla
1. Revisar tabla Bronze existe
   ```bash
   bq show retail_claims_bronze.claims_external
   ```

2. Ver logs de Dataproc
   ```bash
   gcloud dataproc jobs describe <job-id> --region us-central1
   ```

### DAG no ejecuta
1. Verificar variables en Composer
   ```bash
   gcloud composer environments describe retail-etl --location us-central1
   ```

2. Ver logs
   ```bash
   gcloud logging read "resource.type=cloud_composer_environment" --limit 50
   ```

---

## 📞 Soporte

¿Dudas? Revisa:
- [README.md](README.md) - Documentación completa
- [CONTRIBUTING.md](CONTRIBUTING.md) - Guía de desarrollo
- [Logs](#troubleshooting) - Troubleshooting

---

**Última actualización**: 2024-01-01
