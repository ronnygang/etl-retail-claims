#!/bin/bash

# Script para configurar Cloud Build triggers automáticamente
# Uso: bash scripts/setup_cloud_build.sh PROJECT_ID GITHUB_OWNER GITHUB_REPO

set -e

if [ $# -lt 3 ]; then
    echo "❌ Uso: bash scripts/setup_cloud_build.sh PROJECT_ID GITHUB_OWNER GITHUB_REPO"
    echo ""
    echo "Ejemplos:"
    echo "  bash scripts/setup_cloud_build.sh my-project myusername myrepo"
    exit 1
fi

PROJECT_ID=$1
GITHUB_OWNER=$2
GITHUB_REPO=$3

echo "🔧 Configurando Cloud Build para $PROJECT_ID"
echo ""

# Configurar proyecto
gcloud config set project $PROJECT_ID

# Crear bucket para logs si no existe
BUCKET_NAME="${PROJECT_ID}-build-logs"
echo "📦 Creando bucket de logs..."
gsutil mb gs://$BUCKET_NAME || echo "⚠️  Bucket ya existe"

# Crear topic de Pub/Sub para notificaciones
echo "📢 Creando Pub/Sub topics..."
gcloud pubsub topics create etl-deployments --project=$PROJECT_ID || echo "⚠️  Topic ya existe"
gcloud pubsub topics create etl-deployments-prod --project=$PROJECT_ID || echo "⚠️  Topic ya existe"

# Crear subscription para notificaciones
echo "📧 Creando subscripciones..."
gcloud pubsub subscriptions create etl-deployments-sub \
    --topic=etl-deployments \
    --project=$PROJECT_ID || echo "⚠️  Subscripción ya existe"

# Crear trigger para DEV (push a main)
echo ""
echo "🚀 Creando trigger para DEV (main branch)..."
gcloud builds triggers create github \
    --repo-name=$GITHUB_REPO \
    --repo-owner=$GITHUB_OWNER \
    --branch-pattern='^main$' \
    --build-config=cloudbuild-dev.yaml \
    --name=etl-deploy-dev \
    --description="Deploy ETL a DEV en cada push a main" \
    --project=$PROJECT_ID || echo "⚠️  Trigger ya existe"

# Crear trigger para STAGING (push a develop)
echo "🚀 Creando trigger para STAGING (develop branch)..."
gcloud builds triggers create github \
    --repo-name=$GITHUB_REPO \
    --repo-owner=$GITHUB_OWNER \
    --branch-pattern='^develop$' \
    --build-config=cloudbuild.yaml \
    --name=etl-deploy-staging \
    --description="Deploy ETL a STAGING en cada push a develop" \
    --project=$PROJECT_ID || echo "⚠️  Trigger ya existe"

# Crear trigger para PROD (tags)
echo "🚀 Creando trigger para PROD (tags de release)..."
gcloud builds triggers create github \
    --repo-name=$GITHUB_REPO \
    --repo-owner=$GITHUB_OWNER \
    --tag-pattern='^v.*' \
    --build-config=cloudbuild-prod.yaml \
    --name=etl-deploy-prod \
    --description="Deploy ETL a PROD en cada tag de release" \
    --project=$PROJECT_ID || echo "⚠️  Trigger ya existe"

echo ""
echo "✅ Cloud Build triggers configurados exitosamente"
echo ""
echo "📋 Resumen de triggers:"
echo "   • DEV:     main branch → cloudbuild-dev.yaml"
echo "   • STAGING: develop branch → cloudbuild.yaml"
echo "   • PROD:    tags (v*) → cloudbuild-prod.yaml"
echo ""
echo "🔗 Ver triggers en:"
echo "   https://console.cloud.google.com/cloud-build/triggers?project=$PROJECT_ID"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Configurar variables secretas en Cloud Build"
echo "   2. Actualizar archivos cloudbuild*.yaml con tus valores"
echo "   3. Hacer push al repositorio para disparar builds"
