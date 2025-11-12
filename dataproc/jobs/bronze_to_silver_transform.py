import logging
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, to_date, to_timestamp, trim, upper, 
    when, coalesce, current_timestamp, md5, concat_ws
)
from pyspark.sql.types import StructType, StructField, StringType, FloatType, TimestampType
from datetime import datetime
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BronzeToSilverTransformer:
    """Transformación de datos de capa Bronze a Silver usando PySpark"""
    
    def __init__(self, project_id: str, dataset_id: str, gcs_temp_path: str):
        self.project_id = project_id
        self.dataset_id = dataset_id
        self.gcs_temp_path = gcs_temp_path
        
        self.spark = SparkSession.builder \
            .appName("BronzeToSilverTransform") \
            .config("spark.sql.parquet.compression.codec", "snappy") \
            .config("spark.sql.adaptive.enabled", "true") \
            .getOrCreate()
        
        logger.info("SparkSession inicializada")
    
    def read_bronze_data(self) -> 'pyspark.sql.DataFrame':
        """Leer datos de la tabla externa Bronze"""
        try:
            df = self.spark.read.format("bigquery") \
                .option("table", f"{self.project_id}.retail_claims_bronze.claims_external") \
                .load()
            
            logger.info(f"Datos Bronze leídos: {df.count()} registros")
            return df
        except Exception as e:
            logger.error(f"Error leyendo datos Bronze: {str(e)}")
            raise
    
    def clean_and_standardize(self, df: 'pyspark.sql.DataFrame') -> 'pyspark.sql.DataFrame':
        """Limpiar y estandarizar datos"""
        try:
            df = df \
                .withColumn("claim_id", trim(col("claim_id"))) \
                .withColumn("customer_id", trim(col("customer_id"))) \
                .withColumn("store_id", trim(col("store_id"))) \
                .withColumn("description", trim(col("description"))) \
                .withColumn("status", upper(trim(col("status")))) \
                .withColumn("claim_amount", col("claim_amount").cast(FloatType())) \
                .withColumn("claim_date", to_date(col("claim_date"), "yyyy-MM-dd"))
            
            logger.info("Limpieza y estandarización completadas")
            return df
        except Exception as e:
            logger.error(f"Error en limpieza: {str(e)}")
            raise
    
    def add_technical_columns(self, df: 'pyspark.sql.DataFrame') -> 'pyspark.sql.DataFrame':
        """Agregar columnas técnicas"""
        try:
            df = df \
                .withColumn("ingestion_timestamp", current_timestamp()) \
                .withColumn("processing_date", to_date(current_timestamp())) \
                .withColumn("record_hash", md5(
                    concat_ws("|", 
                        col("claim_id"), 
                        col("customer_id"), 
                        col("claim_amount")
                    )
                )) \
                .withColumn("data_quality_score", 
                    when(col("claim_id").isNotNull() & 
                         col("customer_id").isNotNull() & 
                         col("claim_amount") > 0, 1.0).otherwise(0.5)
                )
            
            logger.info("Columnas técnicas agregadas")
            return df
        except Exception as e:
            logger.error(f"Error agregando columnas técnicas: {str(e)}")
            raise
    
    def validate_data_quality(self, df: 'pyspark.sql.DataFrame') -> dict:
        """Validar calidad de datos"""
        try:
            total_records = df.count()
            null_claim_ids = df.filter(col("claim_id").isNull()).count()
            null_amounts = df.filter(col("claim_amount").isNull()).count()
            negative_amounts = df.filter(col("claim_amount") < 0).count()
            
            quality_report = {
                'total_records': total_records,
                'null_claim_ids': null_claim_ids,
                'null_amounts': null_amounts,
                'negative_amounts': negative_amounts,
                'quality_percentage': round(
                    ((total_records - null_claim_ids - null_amounts - negative_amounts) / total_records * 100), 2
                ) if total_records > 0 else 0
            }
            
            logger.info(f"Reporte de calidad: {quality_report}")
            return quality_report
        except Exception as e:
            logger.error(f"Error validando calidad: {str(e)}")
            raise
    
    def write_to_silver(self, df: 'pyspark.sql.DataFrame'):
        """Escribir datos a capa Silver en BigQuery"""
        try:
            df.write \
                .format("bigquery") \
                .mode("append") \
                .option("table", f"{self.project_id}.retail_claims_silver.claims_structured") \
                .option("temporaryGcsBucket", self.gcs_temp_path) \
                .save()
            
            logger.info("Datos escritos a capa Silver")
        except Exception as e:
            logger.error(f"Error escribiendo a Silver: {str(e)}")
            raise
    
    def transform(self):
        """Ejecutar transformación completa"""
        try:
            logger.info("Iniciando transformación Bronze -> Silver")
            
            # Leer datos
            df = self.read_bronze_data()
            
            # Transformar
            df = self.clean_and_standardize(df)
            df = self.add_technical_columns(df)
            
            # Validar calidad
            quality = self.validate_data_quality(df)
            
            # Escribir
            self.write_to_silver(df)
            
            logger.info("Transformación completada exitosamente")
            return {
                'status': 'success',
                'quality_report': quality,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error en transformación: {str(e)}")
            raise


if __name__ == "__main__":
    project_id = sys.argv[1]
    gcs_bucket = sys.argv[2]
    
    transformer = BronzeToSilverTransformer(
        project_id=project_id,
        dataset_id="retail_claims_silver",
        gcs_temp_path=f"{gcs_bucket}/temp"
    )
    
    result = transformer.transform()
    print(result)
