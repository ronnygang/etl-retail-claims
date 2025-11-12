CREATE SCHEMA IF NOT EXISTS `{project_id}.retail_claims_gold`
  OPTIONS(
    description="Capa Gold - Datos conformados con reglas de negocio",
    location="us-central1"
  );

CREATE OR REPLACE TABLE `{project_id}.retail_claims_gold.claims_business_rules` (
  claim_id STRING NOT NULL,
  customer_id STRING NOT NULL,
  store_id STRING NOT NULL,
  claim_date DATE NOT NULL,
  claim_amount FLOAT64 NOT NULL,
  description STRING,
  status STRING NOT NULL,
  claim_priority STRING,
  days_since_claim INT64,
  requires_escalation BOOL,
  period_category STRING,
  risk_score FLOAT64,
  processing_timestamp TIMESTAMP,
  processing_date DATE NOT NULL,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
)
PARTITION BY processing_date
CLUSTER BY customer_id, claim_priority, requires_escalation
OPTIONS(
  description="Tabla con reglas de negocio aplicadas - Capa Gold"
);

CREATE INDEX idx_priority ON `{project_id}.retail_claims_gold.claims_business_rules`(claim_priority);
CREATE INDEX idx_escalation ON `{project_id}.retail_claims_gold.claims_business_rules`(requires_escalation);
