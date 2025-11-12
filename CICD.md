# CI/CD - Cloud Build - Despliegue Continuo

## 🚀 Introducción

Este proyecto utiliza **Google Cloud Build** para implementar un pipeline de **Integración Continua y Despliegue Continuo (CI/CD)**.

El pipeline automatiza:
- ✅ Tests unitarios
- ✅ Validación de código
- ✅ Construcción de imágenes Docker
- ✅ Despliegue a Cloud Functions
- ✅ Actualización de BigQuery
- ✅ Despliegue de DAGs en Cloud Composer

---

## 📊 Arquitectura del Pipeline

```
GitHub Repository
     ↓
Commit/Push
     ↓
Cloud Build Trigger
     ↓
┌─────────────────────────────────────┐
│  Tests & Validación                 │
│  ├─ pytest                          │
│  ├─ coverage                        │
│  └─ lint                            │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│  Build & Push                       │
│  ├─ Docker Build                    │
│  ├─ Container Registry Push         │
└─────────────────────────────────────┘
     ↓
┌─────────────────────────────────────┐
│  Deploy                             │
│  ├─ Cloud Function                  │
│  ├─ BigQuery Tables                 │
│  ├─ Spark Jobs (GCS)                │
│  └─ Airflow DAGs                    │
└─────────────────────────────────────┘
     ↓
Notificación Pub/Sub
```

---

## 🔧 Configuración Inicial

### 1. Prerequisitos

```bash
# Tener:
- Repositorio en GitHub
- Proyecto GCP configurado
- Permisos de Cloud Build

# Instalar gcloud CLI
curl https://sdk.cloud.google.com | bash
gcloud init
gcloud auth login
```

### 2. Conectar GitHub a Cloud Build

```bash
# Autenticar con GitHub
gcloud builds connect --repository-name=YOUR_REPO \
  --repository-owner=YOUR_GITHUB_USER \
  --region=us-central1
```

### 3. Crear Triggers Automáticamente

```bash
# Ejecutar script de setup
bash scripts/setup_cloud_build.sh YOUR_PROJECT_ID YOUR_GITHUB_USER YOUR_REPO

# Ejemplo:
bash scripts/setup_cloud_build.sh my-project myusername myrepo
```

---

## 📁 Archivos de Configuración

### `cloudbuild.yaml` (STAGING)
```yaml
# Despliegue a STAGING (develop branch)
# - Ejecuta todos los tests
- Tests unitarios con coverage ≥ 70%
- Valida sintaxis SQL
- Construye imagen Docker
- Desplega a Cloud Functions
- Actualiza tablas BigQuery
- Desplega DAG en Composer
```

### `cloudbuild-dev.yaml` (DEV)
```yaml
# Despliegue a DEV (main branch)
# - Tests básicos
- Tests unitarios
- Construcción de imagen
- Despliegue a Cloud Functions (dev)
- Versión: dev-{SHORT_SHA}
```

### `cloudbuild-prod.yaml` (PRODUCCIÓN)
```yaml
# Despliegue a PRODUCCIÓN (tags)
# - Validación completa
- Todos los tests (coverage ≥ 80%)
- Escaneo de seguridad (Bandit)
- Construcción de imagen
- Despliegue a Cloud Functions (prod)
- Versionado con tag de release
```

---

## 🎯 Flujo de Despliegue

### Rama Development (`develop`)
```
Commit push
     ↓
Trigger: cloudbuild.yaml
     ↓
Deploy STAGING
```

### Rama Main (`main`)
```
Commit push
     ↓
Trigger: cloudbuild-dev.yaml
     ↓
Deploy DEV
```

### Release (Tag)
```
git tag v1.0.0
git push origin v1.0.0
     ↓
Trigger: cloudbuild-prod.yaml
     ↓
Deploy PROD
```

---

## 🔐 Configurar Secretos

### 1. Usar Secret Manager

```bash
# Crear secreto para SFTP credentials
echo -n "your-sftp-password" | gcloud secrets create sftp-password --data-file=-

# Crear secreto para SFTP host
echo -n "sftp.example.com" | gcloud secrets create sftp-host --data-file=-

# Ver secretos
gcloud secrets list
```

### 2. Usar Secret Manager en Cloud Build

En `cloudbuild.yaml`:
```yaml
steps:
  - name: 'gcr.io/cloud-builders/gke-deploy'
    secretEnv: ['SFTP_PASSWORD']
    env:
      - 'SFTP_HOST=sftp.example.com'
    args:
      - 'run'
      - 'gcloud'
      - 'functions'
      - 'deploy'
      - 'ingest-sftp-to-gcs'
      # ... más argumentos ...

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/sftp-password/versions/latest
      env: 'SFTP_PASSWORD'
```

### 3. Otorgar Permisos a Cloud Build

```bash
# Obtener cuenta de servicio de Cloud Build
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUD_BUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Permitir acceso a secretos
gcloud secrets add-iam-policy-binding sftp-password \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/secretmanager.secretAccessor
```

---

## 📝 Variables y Sustituciones

### Usar variables en cloud build

En `cloudbuild.yaml`:
```yaml
substitutions:
  _ENVIRONMENT: 'dev'
  _GCS_BUCKET: 'retail-claims-etl'
  _SFTP_HOST: ''  # Dejar vacío para usar Secret Manager
```

En la línea de comandos:
```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_ENVIRONMENT=staging,_GCS_BUCKET=retail-claims-etl-staging
```

---

## 🧪 Pruebas en Cloud Build

### Tests Unitarios

```yaml
- name: 'gcr.io/cloud-builders/python'
  args:
    - 'pytest'
    - 'tests/unit/'
    - '-v'
    - '--cov=.'
    - '--cov-fail-under=70'
```

### Validación de Código

```yaml
- name: 'gcr.io/cloud-builders/python'
  args:
    - 'bash'
    - '-c'
    - |
      pip install pylint
      pylint dataproc/jobs/*.py --disable=all --enable=E,F,W
```

### Escaneo de Seguridad

```yaml
- name: 'gcr.io/cloud-builders/python'
  args:
    - 'bash'
    - '-c'
    - |
      pip install bandit
      bandit -r cloud_functions/ dataproc/jobs/ dags/ -ll
```

---

## 🐳 Construcción de Imágenes Docker

### Dockerfile para Cloud Function

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 8080
CMD ["functions-framework", "--target=ingest_sftp_to_gcs"]
```

### Construir en Cloud Build

```yaml
- name: 'gcr.io/cloud-builders/docker'
  args:
    - 'build'
    - '-t'
    - 'gcr.io/$PROJECT_ID/ingest-sftp-to-gcs:$SHORT_SHA'
    - '-t'
    - 'gcr.io/$PROJECT_ID/ingest-sftp-to-gcs:latest'
    - '-f'
    - 'cloud_functions/ingest_sftp_to_gcs/Dockerfile'
    - 'cloud_functions/ingest_sftp_to_gcs/'
```

---

## ☁️ Despliegue a Servicios GCP

### Cloud Functions

```yaml
- name: 'gcr.io/cloud-builders/gke-deploy'
  args:
    - 'run'
    - 'gcloud'
    - 'functions'
    - 'deploy'
    - 'ingest-sftp-to-gcs'
    - '--runtime=python39'
    - '--trigger-http'
    - '--entry-point=ingest_sftp_to_gcs'
    - '--region=us-central1'
```

### BigQuery

```yaml
- name: 'gcr.io/cloud-builders/python'
  args:
    - 'bash'
    - '-c'
    - 'python scripts/deploy_bigquery.py --project=$PROJECT_ID'
```

### Cloud Composer (Airflow)

```yaml
- name: 'gcr.io/cloud-builders/gsutil'
  args:
    - 'cp'
    - 'dags/retail_claims_etl_dag.py'
    - 'gs://us-central1-${_COMPOSER_ENV}-bucket/dags/'
```

---

## 📊 Monitoreo y Logs

### Ver Logs de Cloud Build

```bash
# Ver últimas ejecuciones
gcloud builds log -r 10

# Ver log de una ejecución específica
gcloud builds log BUILD_ID

# Ver logs en tiempo real
gcloud builds log BUILD_ID --stream
```

### Ver en Cloud Console

```
https://console.cloud.google.com/cloud-build/builds?project=PROJECT_ID
```

### Notificaciones con Pub/Sub

```bash
# Ver mensajes de Pub/Sub
gcloud pubsub subscriptions pull etl-deployments-sub --auto-ack --limit=10
```

---

## 🔄 Workflow Completo

### 1. Desarrollo Local

```bash
# Crear rama feature
git checkout -b feature/nueva-feature

# Hacer cambios y tests
pytest tests/unit/ -v

# Commit
git add .
git commit -m "feat: nueva feature"
```

### 2. Push a DEV

```bash
# Push a main (dispara cloudbuild-dev.yaml)
git push origin feature/nueva-feature
git checkout main
git pull origin feature/nueva-feature
git push origin main
```

### 3. Deploy a STAGING

```bash
# Push a develop (dispara cloudbuild.yaml)
git checkout develop
git merge main
git push origin develop
```

### 4. Deploy a PRODUCCIÓN

```bash
# Crear tag (dispara cloudbuild-prod.yaml)
git tag v1.0.0
git push origin v1.0.0
```

---

## 🛠️ Troubleshooting

### Build falla por tests

```bash
# Ver error completo
gcloud builds log BUILD_ID

# Ejecutar tests localmente
pytest tests/unit/ -v --tb=short

# Verificar cobertura
pytest tests/unit/ --cov=. --cov-report=term
```

### Cloud Function no se despliega

```bash
# Verificar permisos
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.members)"

# Ver estado de Cloud Functions
gcloud functions list --region=us-central1
```

### BigQuery falla

```bash
# Verificar datasets
bq ls

# Verificar tablas
bq ls retail_claims_bronze

# Ver errores de queries
gcloud logging read "resource.type=bigquery_dml_statistics" --limit=5
```

---

## 📚 Recursos

- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [Cloud Build Pricing](https://cloud.google.com/build/pricing)
- [Best Practices](https://cloud.google.com/build/docs/best-practices)
- [Troubleshooting](https://cloud.google.com/build/docs/troubleshooting)

---

## 💡 Tips

1. **Parallelize pasos** - Cloud Build ejecuta pasos en paralelo si no tienen dependencias
2. **Cache Docker** - Usa `docker pull` para cachear capas
3. **Limita timeout** - Establece timeouts razonables para evitar costos
4. **Monitorea costos** - Cloud Build cobra por minutos de ejecución
5. **Usa substituciones** - Para reutilizar builds en múltiples ambientes

---

**Documentación generada**: 2025-11-12
