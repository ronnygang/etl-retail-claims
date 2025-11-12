CREATE SCHEMA IF NOT EXISTS `{project_id}.retail_claims_silver`
  OPTIONS(
    description="Capa Silver - Datos estructurados y limpios",
    location="us-central1"
  );

CREATE OR REPLACE TABLE `{project_id}.retail_claims_silver.claims_structured` (
  claim_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  store_id STRING NOT NULL,
  claim_date DATE NOT NULL,
  claim_amount FLOAT64 NOT NULL,
  description STRING,
  status STRING NOT NULL,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  ingestion_timestamp TIMESTAMP NOT NULL,
  processing_date DATE NOT NULL,
  record_hash STRING,
  data_quality_score FLOAT64,
  _load_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY processing_date
CLUSTER BY customer_id, store_id
OPTIONS(
  description="Tabla estructurada de reclamos retail - Capa Silver",
  partition_expiration_ms=7776000000
);

CREATE INDEX idx_claim_date ON `{project_id}.retail_claims_silver.claims_structured`(claim_date);
CREATE INDEX idx_status ON `{project_id}.retail_claims_silver.claims_structured`(status);
