-- Crear dataset si no existe
CREATE SCHEMA IF NOT EXISTS `{project_id}.retail_claims_bronze`
  OPTIONS(
    description="Capa Bronze - Datos raw de reclamos retail",
    location="us-central1"
  );

-- Tabla externa desde archivos JSON en GCS
CREATE OR REPLACE EXTERNAL TABLE `{project_id}.retail_claims_bronze.claims_external`
OPTIONS (
  format = 'NEWLINE_DELIMITED_JSON',
  uris = ['gs://{gcs_bucket}/bronze/retail-claims/**/*.json'],
  allow_jagged_rows = true,
  allow_quoted_newlines = true,
  ignore_unknown_values = true
);
