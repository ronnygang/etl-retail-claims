# MONITORING.md - Monitoreo y Alertas

## 📊 Objetivo

Configurar monitoreo integral para la pipeline ETL con alertas para detectar problemas en tiempo real.

---

## 🎯 Métricas Clave

### Cloud Function (Ingestion)

| Métrica | Umbral Alerta | Acción |
|---------|---------------|--------|
| Error Rate | > 5% | Revisar logs, validar SFTP |
| Latency (p95) | > 30s | Aumentar memoria/timeout |
| Execution Count | 0 en 1h | Verificar trigger |
| Memory Usage | > 90% | Escalar resources |

### Dataproc (Transformation)

| Métrica | Umbral Alerta | Acción |
|---------|---------------|--------|
| Job Failure Rate | > 1 fallo | Revisar datos, schema |
| Job Duration | > 2x promedio | Optimizar Spark job |
| HDFS Disk Usage | > 80% | Aumentar nodes |
| CPU Utilization | > 85% | Escalar cluster |

### BigQuery (Data Warehouse)

| Métrica | Umbral Alerta | Acción |
|---------|---------------|--------|
| Query Execution Time | > 5min | Optimizar query |
| Slot Utilization | > 80% | Comprar slots |
| Storage Growth | > 10GB/día | Revisar retención |
| Failed Queries | > 0 | Revisar SQL syntax |

### Cloud Composer (Orchestration)

| Métrica | Umbral Alerta | Acción |
|---------|---------------|--------|
| DAG Run Duration | > 2x SLA | Investigar tarea |
| Task Failure | > 0 | Revisar logs |
| Environment Health | Unhealthy | Reiniciar ambiente |
| Database Connections | > 80% | Escalar DB |

---

## 🔧 1. Configurar Cloud Monitoring

### 1.1 Crear Workspace

```bash
# Crear workspace de monitoring
gcloud alpha monitoring workspaces create \
  --display-name="ETL Pipeline Monitoring" \
  --project=$(gcloud config get-value project)

# Ver workspaces
gcloud alpha monitoring workspaces list
```

### 1.2 Habilitar APIs

```bash
# Habilitar Cloud Monitoring API
gcloud services enable monitoring.googleapis.com

# Habilitar Cloud Logging API
gcloud services enable logging.googleapis.com

# Habilitar Cloud Trace API
gcloud services enable cloudtrace.googleapis.com
```

---

## 📈 2. Crear Dashboards

### 2.1 Dashboard Principal

```bash
cat > monitoring/dashboard_main.json << 'EOF'
{
  "displayName": "ETL Pipeline - Main Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Cloud Function - Execution Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_function\" AND metric.type=\"cloudfunctions.googleapis.com/function/execution_count\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Cloud Function - Error Rate",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_function\" AND metric.type=\"cloudfunctions.googleapis.com/function/execution_count\" AND metric.response_type=\"error\""
                }
              }
            }]
          }
        }
      },
      {
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Dataproc - Job Status",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"dataproc_cluster\" AND metric.type=\"dataproc.googleapis.com/cluster/job/status\""
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "yPos": 4,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "BigQuery - Slot Usage",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"bigquery_resource\" AND metric.type=\"bigquery.googleapis.com/slots/total_allocated\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF

# Crear dashboard
gcloud monitoring dashboards create --config-from-file=monitoring/dashboard_main.json
```

### 2.2 Crear Dashboard en Console

1. Ve a: `https://console.cloud.google.com/monitoring/dashboards`
2. Click "Create Dashboard"
3. Agrega widgets para cada métrica

---

## 🚨 3. Configurar Alertas

### 3.1 Alerta: Cloud Function Errors

```bash
PROJECT_ID=$(gcloud config get-value project)

# Crear policy de alertas
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Cloud Function - High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-filter='resource.type="cloud_function" AND metric.type="cloudfunctions.googleapis.com/function/execution_count" AND metric.response_type="error"' \
  --condition-threshold-value=5 \
  --condition-threshold-duration=60s
```

### 3.2 Alerta: Dataproc Job Failure

```bash
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Dataproc - Job Failure" \
  --condition-display-name="Job failed" \
  --condition-threshold-filter='resource.type="dataproc_cluster" AND metric.type="dataproc.googleapis.com/cluster/job/failed_jobs"' \
  --condition-threshold-value=1 \
  --condition-threshold-duration=60s
```

### 3.3 Alerta: BigQuery Query Timeout

```bash
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="BigQuery - Query Timeout" \
  --condition-display-name="Execution time > 5 minutes" \
  --condition-threshold-filter='resource.type="bigquery_resource" AND metric.type="bigquery.googleapis.com/job/num_in_flight_jobs"' \
  --condition-threshold-value=10 \
  --condition-threshold-duration=300s
```

### 3.4 Alerta: Cloud Composer DAG Failure

```bash
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Cloud Composer - DAG Failure" \
  --condition-display-name="DAG failed" \
  --condition-threshold-filter='resource.type="cloud_composer_environment" AND metric.type="composer.googleapis.com/environment/dag_run/failed"' \
  --condition-threshold-value=1 \
  --condition-threshold-duration=60s
```

---

## 📧 4. Configurar Canales de Notificación

### 4.1 Email

```bash
PROJECT_ID=$(gcloud config get-value project)

# Crear canal de notificación por email
gcloud alpha monitoring channels create \
  --display-name="ETL Team Email" \
  --type=email \
  --channel-labels=email_address=etl-team@empresa.com \
  --enabled
```

### 4.2 Slack

```bash
# 1. Crear Webhook en Slack
# Ve a: https://api.slack.com/messaging/webhooks
# Copia la URL: https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# 2. Crear canal de notificación
gcloud alpha monitoring channels create \
  --display-name="ETL Slack Channel" \
  --type=slack \
  --channel-labels=channel_name="#etl-alerts" \
  --enabled
```

### 4.3 Pub/Sub

```bash
# Crear topic de Pub/Sub
gcloud pubsub topics create etl-alerts

# Crear suscripción
gcloud pubsub subscriptions create etl-alerts-sub \
  --topic=etl-alerts

# Crear canal de notificación
gcloud alpha monitoring channels create \
  --display-name="ETL Pub/Sub" \
  --type=pubsub \
  --channel-labels=topic_name=projects/$PROJECT_ID/topics/etl-alerts \
  --enabled
```

### 4.4 PagerDuty (On-Call)

```bash
# 1. Obtener integration key de PagerDuty
# Ve a: https://pagerduty.com/

# 2. Crear canal de notificación
gcloud alpha monitoring channels create \
  --display-name="ETL PagerDuty" \
  --type=pagerduty \
  --channel-labels=integration_key=YOUR_INTEGRATION_KEY \
  --enabled
```

---

## 📊 5. Crear Logs Personnalizados

### 5.1 Loguear eventos de pipeline

```python
# En tu código Python
import logging
from google.cloud import logging as cloud_logging

# Inicializar logging
logging_client = cloud_logging.Client()
logging_client.setup_logging()

logger = logging.getLogger(__name__)

# Loguear eventos
logger.info("Pipeline started", extra={
    "pipeline_name": "retail_claims_etl",
    "timestamp": datetime.now(),
    "status": "STARTED"
})

logger.warning("High memory usage", extra={
    "memory_percent": 85,
    "component": "dataproc"
})

logger.error("Data validation failed", extra={
    "invalid_records": 150,
    "total_records": 10000,
    "error_rate": 0.015
})
```

### 5.2 Crear Sink de Logs

```bash
# Exportar logs a BigQuery
gcloud logging sinks create etl-logs-sink \
  bigquery.googleapis.com/projects/PROJECT_ID/datasets/etl_logs \
  --log-filter='resource.type=cloud_function OR resource.type=dataproc_cluster OR resource.type=bigquery_resource'

# Exportar logs a Cloud Storage
gcloud logging sinks create etl-logs-gcs \
  storage.googleapis.com/etl-logs-bucket \
  --log-filter='resource.type=cloud_function OR resource.type=dataproc_cluster'

# Exportar logs a Pub/Sub
gcloud logging sinks create etl-logs-pubsub \
  pubsub.googleapis.com/projects/PROJECT_ID/topics/etl-logs \
  --log-filter='severity=ERROR'
```

---

## 🔍 6. Queries de Logging

### 6.1 Ver errores de Cloud Function

```bash
gcloud logging read \
  'resource.type=cloud_function 
   AND severity=ERROR' \
  --limit=50 \
  --format=json
```

### 6.2 Ver Dataproc job failures

```bash
gcloud logging read \
  'resource.type=dataproc_cluster 
   AND textPayload=~".*failed.*"' \
  --limit=50
```

### 6.3 Ver BigQuery query errors

```bash
gcloud logging read \
  'resource.type=bigquery_resource 
   AND severity=ERROR' \
  --limit=50
```

### 6.4 Ver Composer DAG runs

```bash
gcloud logging read \
  'resource.type=cloud_composer_environment 
   AND textPayload=~".*DAG run.*"' \
  --limit=100
```

---

## 📈 7. Crear Reportes Automáticos

### 7.1 Health Check Script

```bash
#!/bin/bash

PROJECT_ID=$(gcloud config get-value project)
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "=== ETL Pipeline Health Report ===" > report.txt
echo "Generated: $DATE" >> report.txt

echo -e "\n### Cloud Function Status ###" >> report.txt
gcloud functions describe ingest-sftp-to-gcs \
  --gen2 --region=us-central1 \
  --format='table(status, updateTime)' >> report.txt

echo -e "\n### Dataproc Cluster Status ###" >> report.txt
gcloud dataproc clusters list --region=us-central1 \
  --format='table(name, status, startTime)' >> report.txt

echo -e "\n### BigQuery Table Status ###" >> report.txt
bq ls retail_claims_silver --format=pretty >> report.txt

echo -e "\n### Recent Errors ###" >> report.txt
gcloud logging read 'severity=ERROR' --limit=5 >> report.txt

# Enviar reporte
mail -s "ETL Health Report - $DATE" etl-team@empresa.com < report.txt
```

### 7.2 Ejecutar Script Diariamente

```bash
# Crear Cloud Scheduler job
gcloud scheduler jobs create app-engine etl-health-check \
  --schedule="0 8 * * *" \
  --time-zone="America/Bogota" \
  --http-method=POST \
  --uri="https://YOUR_REGION-YOUR_PROJECT.cloudfunctions.net/health-check"
```

---

## 🎯 8. SLOs (Service Level Objectives)

### 8.1 Definir SLOs

| Componente | SLO | Umbral |
|-----------|-----|--------|
| Cloud Function Availability | 99.9% | Máx 0.09% downtime |
| Dataproc Job Success | 99% | Máx 1 fallo/100 |
| BigQuery Query Success | 99.5% | Máx 0.5% fallos |
| E2E Pipeline Success | 99% | Máx 1 fallo/100 |

### 8.2 Crear SLO Window

```bash
gcloud slo create etl-function-availability \
  --service-identifier=PROJECT_ID \
  --display-name="ETL Function Availability" \
  --goal=0.999 \
  --rolling-period=2592000s
```

---

## 📞 9. Escalación

### 9.1 Niveles de Escalación

**L1: Alerta Automática**
- Slack notification
- Email a equipo
- Log automático

**L2: Escalación (30 min sin respuesta)**
- SMS al on-call engineer
- PagerDuty incident
- Slack mention @etl-oncall

**L3: Escalación Crítica (1 hora)**
- Call al lead engineer
- Executive notification
- Run incident response playbook

### 9.2 Runbook de Escalación

```yaml
AlertSeverity:
  CRITICAL:
    Actions:
      - Immediately page on-call engineer
      - Create PagerDuty incident
      - Slack #etl-critical channel
    ResponseTime: 15 minutes
    
  HIGH:
    Actions:
      - Alert via Slack
      - Create ticket
    ResponseTime: 1 hour
    
  MEDIUM:
    Actions:
      - Log to monitoring
      - Email team
    ResponseTime: 4 hours
    
  LOW:
    Actions:
      - Log only
    ResponseTime: 1 day
```

---

## 🔄 10. Iteración Continua

### 10.1 Weekly Review

```
Every Monday 10:00 AM:
- Review alerts from past week
- Analyze false positives
- Adjust thresholds if needed
- Update SLOs if necessary
```

### 10.2 Monthly Analysis

```
Last Friday of month:
- Generate performance report
- Identify trends
- Plan improvements
- Update runbooks
```

### 10.3 Quarterly Planning

```
Every Q:
- Review year-to-date metrics
- Plan capacity upgrades
- Update monitoring strategy
- Refine alerting rules
```

---

## 📚 Archivos de Referencia

- `monitoring/dashboard_main.json` - Dashboard principal
- `scripts/health-check.sh` - Script de validación
- `DEPLOYMENT.md` - Guía de despliegue

---

**Generado**: 2025-11-12
