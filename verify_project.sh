#!/bin/bash

# Script de verificación del proyecto ETL
# Verifica que todos los archivos fueron creados correctamente

echo "═══════════════════════════════════════════════════════════════"
echo "  ✅ VERIFICACIÓN DE PROYECTO ETL - RETAIL CLAIMS"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Contadores
total_files=0
missing_files=0

# Arrays de archivos requeridos
declare -a py_files=(
    "cloud_functions/ingest_sftp_to_gcs/main.py"
    "dataproc/jobs/bronze_to_silver_transform.py"
    "dags/retail_claims_etl_dag.py"
    "tests/unit/test_transformations.py"
)

declare -a sql_files=(
    "bigquery/schemas/bronze_external_table.sql"
    "bigquery/schemas/silver_schema.sql"
    "bigquery/schemas/gold_schema.sql"
    "bigquery/stored_procedures/silver_to_gold_business_rules.sql"
)

declare -a config_files=(
    "config/environment.yaml"
    "config/secrets_template.yaml"
    "dataproc/configs/dataproc_cluster_config.yaml"
)

declare -a doc_files=(
    "README.md"
    "QUICKSTART.md"
    "CONTRIBUTING.md"
    "INDEX.md"
    ".env.example"
    ".gitignore"
    "requirements.txt"
)

# Función para verificar archivos
check_files() {
    local file_type=$1
    shift
    local files=("$@")
    
    echo "📁 $file_type:"
    for file in "${files[@]}"; do
        total_files=$((total_files + 1))
        if [ -f "$file" ]; then
            size=$(wc -c < "$file" | tr -d ' ')
            echo "   ✅ $file ($size bytes)"
        else
            echo "   ❌ FALTA: $file"
            missing_files=$((missing_files + 1))
        fi
    done
    echo ""
}

# Verificar archivos Python
check_files "Python Files" "${py_files[@]}"

# Verificar archivos SQL
check_files "SQL Files" "${sql_files[@]}"

# Verificar archivos de configuración
check_files "Config Files" "${config_files[@]}"

# Verificar documentación
check_files "Documentation" "${doc_files[@]}"

# Verificar directorios
echo "📂 Directorios:"
directories=(
    "cloud_functions/ingest_sftp_to_gcs"
    "dataproc/jobs"
    "dataproc/configs"
    "bigquery/schemas"
    "bigquery/stored_procedures"
    "bigquery/ddl"
    "config"
    "dags"
    "tests/unit"
    "tests/integration"
    "monitoring"
    "scripts"
)

for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        echo "   ✅ $dir/"
    else
        echo "   ❌ FALTA: $dir/"
    fi
done
echo ""

# Resumen
echo "═══════════════════════════════════════════════════════════════"
echo "  📊 RESUMEN"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "  Total de archivos esperados: $total_files"
echo "  Archivos encontrados: $((total_files - missing_files))"
echo "  Archivos faltantes: $missing_files"
echo ""

if [ $missing_files -eq 0 ]; then
    echo "  ✅ PROYECTO COMPLETADO EXITOSAMENTE"
    echo ""
    echo "  🚀 Próximos pasos:"
    echo "     1. Configurar variables en .env:"
    echo "        cp .env.example .env"
    echo "        vim .env"
    echo ""
    echo "     2. Instalar dependencias:"
    echo "        pip install -r requirements.txt"
    echo ""
    echo "     3. Ejecutar tests:"
    echo "        pytest tests/unit/ -v"
    echo ""
    echo "     4. Desplegar en GCP:"
    echo "        bash scripts/deploy_gcp.sh your-project-id"
    echo ""
    echo "  📚 Documentación:"
    echo "     - README.md: Documentación completa"
    echo "     - QUICKSTART.md: Inicio rápido (5 minutos)"
    echo "     - INDEX.md: Índice de archivos"
    echo "     - CONTRIBUTING.md: Guía de desarrollo"
    echo ""
else
    echo "  ⚠️  Hay archivos faltantes. Revisa la lista arriba."
fi

echo "═══════════════════════════════════════════════════════════════"
