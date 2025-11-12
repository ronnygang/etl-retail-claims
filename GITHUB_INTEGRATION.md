# GitHub Integration Guide - Integración con Cloud Build

## 🎯 Objetivo

Conectar tu repositorio de GitHub con Google Cloud Build para ejecutar automáticamente el pipeline CI/CD en cada push/tag.

---

## 📋 Pre-requisitos

1. **Proyecto GCP existente** con Cloud Build habilitado
2. **Repositorio en GitHub** (público o privado)
3. **gcloud CLI** instalado y autenticado
4. **Acceso de administrador** al repositorio GitHub

---

## 🔗 Paso 1: Autenticar Cloud Build con GitHub

### Opción A: Usando gcloud CLI (Recomendado)

```bash
# Configurar proyecto GCP
PROJECT_ID="tu-proyecto-gcp"
gcloud config set project $PROJECT_ID

# Conectar con GitHub
gcloud builds connect --repository-name=YOUR_REPO \
  --repository-owner=YOUR_GITHUB_USER \
  --region=us-central1
```

**Esto abrirá un navegador donde deberás**:
1. Autorizar Google Cloud Build
2. Instalar la aplicación "Google Cloud Build" en tu cuenta GitHub
3. Seleccionar los repositorios que deseas conectar

### Opción B: Manual en Cloud Console

1. Ve a: `https://console.cloud.google.com/cloud-build/repositories`
2. Click en "CONNECT REPOSITORY"
3. Selecciona "GitHub"
4. Autoriza con tu cuenta GitHub
5. Selecciona el repositorio
6. Click en "Connect"

---

## 🚀 Paso 2: Crear Triggers Automáticamente

### Opción A: Script Automatizado (Recomendado)

```bash
# Editar variables
PROJECT_ID="tu-proyecto-gcp"
GITHUB_USER="tu-usuario-github"
GITHUB_REPO="tu-repositorio"

# Ejecutar script
bash scripts/setup_cloud_build.sh $PROJECT_ID $GITHUB_USER $GITHUB_REPO
```

**El script crea**:
- ✅ Trigger para rama `main` → DEV
- ✅ Trigger para rama `develop` → STAGING
- ✅ Trigger para tags `v*` → PROD
- ✅ Topics de Pub/Sub para notificaciones

### Opción B: Crear Triggers Manualmente

```bash
PROJECT_ID="tu-proyecto-gcp"
GITHUB_OWNER="tu-usuario-github"
GITHUB_REPO="tu-repositorio"

# Trigger para rama MAIN (DEV)
gcloud builds triggers create github \
  --name="dev-deploy" \
  --repository-name=$GITHUB_REPO \
  --repository-owner=$GITHUB_OWNER \
  --branch-pattern="^main$" \
  --build-config="cloudbuild-dev.yaml"

# Trigger para rama DEVELOP (STAGING)
gcloud builds triggers create github \
  --name="staging-deploy" \
  --repository-name=$GITHUB_REPO \
  --repository-owner=$GITHUB_OWNER \
  --branch-pattern="^develop$" \
  --build-config="cloudbuild.yaml"

# Trigger para TAGS (PROD)
gcloud builds triggers create github \
  --name="prod-deploy" \
  --repository-name=$GITHUB_REPO \
  --repository-owner=$GITHUB_OWNER \
  --tag-pattern="^v.*" \
  --build-config="cloudbuild-prod.yaml"
```

---

## 🔐 Paso 3: Configurar Secretos

### Crear Secretos en Secret Manager

```bash
PROJECT_ID="tu-proyecto-gcp"
gcloud config set project $PROJECT_ID

# Secreto: SFTP Password
echo -n "tu-sftp-password" | \
  gcloud secrets create sftp-password --data-file=-

# Secreto: SFTP Username
echo -n "tu-usuario-sftp" | \
  gcloud secrets create sftp-username --data-file=-

# Secreto: SFTP Host
echo -n "sftp.ejemplo.com" | \
  gcloud secrets create sftp-host --data-file=-

# Ver todos los secretos
gcloud secrets list
```

### Dar Permisos a Cloud Build

```bash
PROJECT_ID="tu-proyecto-gcp"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUD_BUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Otorgar acceso a secretos
gcloud secrets add-iam-policy-binding sftp-password \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding sftp-username \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/secretmanager.secretAccessor

gcloud secrets add-iam-policy-binding sftp-host \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/secretmanager.secretAccessor
```

### Usar Secretos en Cloud Build

En tu `cloudbuild.yaml`:

```yaml
steps:
  # Usar un secreto
  - name: 'gcr.io/cloud-builders/python'
    secretEnv: ['SFTP_PASSWORD', 'SFTP_USERNAME']
    args:
      - 'python'
      - 'scripts/ingest.py'
    env:
      - 'SFTP_HOST=sftp.ejemplo.com'

availableSecrets:
  secretManager:
    - versionName: projects/$PROJECT_ID/secrets/sftp-password/versions/latest
      env: 'SFTP_PASSWORD'
    - versionName: projects/$PROJECT_ID/secrets/sftp-username/versions/latest
      env: 'SFTP_USERNAME'
```

---

## 📝 Paso 4: Configurar Substituciones

### Usar Variables en Cloud Build

En `cloudbuild.yaml`:

```yaml
substitutions:
  _GCS_BUCKET: 'retail-claims-etl'
  _COMPOSER_ENV: 'retail-claims-composer'
  _DATAPROC_CLUSTER: 'retail-claims-cluster'
  _PUBSUB_TOPIC: 'etl-deployments'
```

### Sobrescribir en CLI

```bash
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=_GCS_BUCKET=retail-claims-etl-staging
```

---

## ✅ Paso 5: Verificar la Integración

### Ver Triggers Creados

```bash
gcloud builds triggers list
```

### Hacer un Commit de Prueba

```bash
# Crear rama de prueba
git checkout -b test/cloud-build-integration

# Hacer un cambio trivial
echo "# Testing Cloud Build" >> README.md

# Commit
git add README.md
git commit -m "test: trigger cloud build"

# Push
git push origin test/cloud-build-integration
```

### Ver Build en Consola

1. Ve a: `https://console.cloud.google.com/cloud-build/builds`
2. Deberías ver un build "In progress"
3. Click para ver los logs

### Monitorear en Terminal

```bash
# Ver últimos builds
gcloud builds log -r 1

# Ver build específico
BUILD_ID="abc123"
gcloud builds log $BUILD_ID --stream
```

---

## 📊 Workflow Completo Post-Integración

### 1️⃣ Desarrollo

```bash
# Crear rama feature
git checkout -b feature/mi-feature

# Hacer cambios
# ...

# Commit
git add .
git commit -m "feat: nueva funcionalidad"

# Push (no dispara trigger aún)
git push origin feature/mi-feature
```

### 2️⃣ Test en DEV

```bash
# Merge a main (dispara cloudbuild-dev.yaml)
git checkout main
git pull origin main
git merge feature/mi-feature
git push origin main

# Ver build en Cloud Console
gcloud builds log -r 1
```

### 3️⃣ Test en STAGING

```bash
# Merge a develop (dispara cloudbuild.yaml)
git checkout develop
git pull origin develop
git merge main
git push origin develop

# Esperar a que cloud build termine
```

### 4️⃣ Deploy a PRODUCCIÓN

```bash
# Crear tag (dispara cloudbuild-prod.yaml)
git tag v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0

# Monitorear
gcloud builds log -r 1 --stream
```

---

## 🔔 Paso 6: Configurar Notificaciones

### Opción A: Pub/Sub a Email

```bash
# Crear suscripción con push a webhook
gcloud pubsub subscriptions create etl-email-sub \
  --topic=etl-deployments \
  --push-endpoint=https://tuservicio.com/webhook

# O crear suscripción pull
gcloud pubsub subscriptions create etl-pull-sub \
  --topic=etl-deployments
```

### Opción B: Slack Webhook

1. Ve a: https://api.slack.com/apps
2. Crea una nueva app
3. Enable "Incoming Webhooks"
4. Copia la Webhook URL
5. Agrega a `cloudbuild.yaml`:

```yaml
onFailure:
  - name: 'gcr.io/cloud-builders/gke-deploy'
    env:
      - 'SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK/URL'
    args:
      - 'run'
      - 'curl'
      - '-X'
      - 'POST'
      - '-H'
      - 'Content-type: application/json'
      - '--data'
      - '{"text":"Build failed: $BUILD_ID"}'
      - '$$SLACK_WEBHOOK'
```

### Opción C: Google Cloud Monitoring

1. Ve a: `https://console.cloud.google.com/monitoring/alerting`
2. Crea una policy para "Cloud Build"
3. Configura notificación a email

---

## 🐛 Troubleshooting

### Build no se dispara automáticamente

**Problema**: Push a GitHub pero no hay build

**Solución**:
```bash
# Verificar que el trigger existe
gcloud builds triggers list --filter="name=tu-trigger"

# Verificar branch pattern
gcloud builds triggers describe dev-deploy

# Verificar que el archivo cloudbuild.yaml existe en el branch
git ls-remote origin refs/heads/main
```

### Permiso denegado a Cloud Build

**Problema**: Build falla con "Permission denied"

**Solución**:
```bash
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUD_BUILD_SA="$PROJECT_NUMBER@cloudbuild.gserviceaccount.com"

# Otorgar roles necesarios
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/cloudfunctions.developer

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/bigquery.admin

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/iam.securityAdmin
```

### Secret no se encuentra

**Problema**: Build falla con "secret not found"

**Solución**:
```bash
# Verificar que el secreto existe
gcloud secrets list | grep sftp

# Verificar que la suscripción puede acceder
gcloud secrets get-iam-policy sftp-password
```

### Build timeout

**Problema**: Build se cancela por timeout

**Solución**: Aumentar timeout en `cloudbuild.yaml`:
```yaml
timeout: '3600s'  # 1 hora
```

---

## 📚 Archivos de Referencia

- `cloudbuild.yaml` - Pipeline STAGING
- `cloudbuild-dev.yaml` - Pipeline DEV
- `cloudbuild-prod.yaml` - Pipeline PROD
- `scripts/setup_cloud_build.sh` - Automatización de triggers
- `scripts/deploy_bigquery.py` - Despliegue de BigQuery

---

## 🎯 Próximos Pasos

1. ✅ Autenticar Cloud Build con GitHub (este paso)
2. ✅ Crear triggers
3. ✅ Configurar secretos
4. ⏳ Hacer push de prueba
5. ⏳ Monitorear build
6. ⏳ Configurar notificaciones

---

**Generado**: 2025-11-12
