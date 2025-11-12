CREATE OR REPLACE PROCEDURE `{project_id}.retail_claims_gold.sp_silver_to_gold_transformation`()
BEGIN
  DECLARE execution_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP();
  
  -- Tabla temporal para validaciones
  CREATE TEMP TABLE temp_processed_claims AS
  SELECT
    claim_id,
    customer_id,
    store_id,
    claim_date,
    claim_amount,
    description,
    status,
    created_at,
    updated_at,
    -- Regla 1: Clasificación de reclamos por monto
    CASE 
      WHEN claim_amount <= 100 THEN 'LOW'
      WHEN claim_amount <= 500 THEN 'MEDIUM'
      WHEN claim_amount <= 2000 THEN 'HIGH'
      ELSE 'CRITICAL'
    END AS claim_priority,
    
    -- Regla 2: Validar edad del reclamo
    DATE_DIFF(CURRENT_DATE(), DATE(created_at), DAY) AS days_since_claim,
    
    -- Regla 3: Determinar si requiere escalado
    CASE 
      WHEN status = 'PENDING' AND DATE_DIFF(CURRENT_DATE(), DATE(created_at), DAY) > 7 THEN true
      WHEN claim_amount > 2000 THEN true
      ELSE false
    END AS requires_escalation,
    
    -- Regla 4: Categorizar por período
    CASE 
      WHEN EXTRACT(MONTH FROM claim_date) IN (11, 12) THEN 'HOLIDAY_SEASON'
      WHEN EXTRACT(MONTH FROM claim_date) IN (1) THEN 'POST_HOLIDAY'
      WHEN EXTRACT(DAYOFWEEK FROM claim_date) IN (6, 7) THEN 'WEEKEND'
      ELSE 'REGULAR'
    END AS period_category,
    
    -- Regla 5: Score de riesgo
    CASE 
      WHEN status = 'REJECTED' THEN 0.8
      WHEN status = 'PENDING' THEN 0.6
      WHEN status = 'APPROVED' THEN 0.2
      WHEN status = 'CLOSED' THEN 0.1
      ELSE 0.5
    END * (CASE 
      WHEN claim_amount > 5000 THEN 1.5
      WHEN claim_amount > 1000 THEN 1.2
      ELSE 1.0
    END) AS risk_score,
    
    execution_timestamp AS processing_timestamp,
    CURRENT_DATE() AS processing_date,
    row_number() OVER (PARTITION BY customer_id ORDER BY created_at DESC) AS recency_rank
    
  FROM `{project_id}.retail_claims_silver.claims_structured`
  WHERE processing_date = CURRENT_DATE()
    AND data_quality_score >= 0.7;
  
  -- Insertar en tabla Gold con deduplicación
  MERGE INTO `{project_id}.retail_claims_gold.claims_business_rules` T
  USING temp_processed_claims S
  ON T.claim_id = S.claim_id
  WHEN MATCHED AND S.recency_rank = 1 THEN
    UPDATE SET 
      status = S.status,
      claim_priority = S.claim_priority,
      days_since_claim = S.days_since_claim,
      requires_escalation = S.requires_escalation,
      period_category = S.period_category,
      risk_score = S.risk_score,
      updated_at = CURRENT_TIMESTAMP()
  WHEN NOT MATCHED THEN
    INSERT (
      claim_id, customer_id, store_id, claim_date, claim_amount,
      description, status, claim_priority, days_since_claim,
      requires_escalation, period_category, risk_score,
      processing_timestamp, processing_date
    )
    VALUES (
      S.claim_id, S.customer_id, S.store_id, S.claim_date, S.claim_amount,
      S.description, S.status, S.claim_priority, S.days_since_claim,
      S.requires_escalation, S.period_category, S.risk_score,
      S.processing_timestamp, S.processing_date
    );

END;
