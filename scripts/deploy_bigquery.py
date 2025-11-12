#!/usr/bin/env python3
"""
Script para desplegar esquemas y stored procedures a BigQuery
Ejecutado por Cloud Build como parte del pipeline CI/CD
"""

import argparse
import os
import sys
import logging
from pathlib import Path
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class BigQueryDeployer:
    """Clase para desplegar esquemas y procedimientos a BigQuery"""
    
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.client = bigquery.Client(project=project_id)
        logger.info(f"BigQuery Client inicializado para proyecto: {project_id}")
    
    def deploy_schemas(self, schemas_dir: str) -> bool:
        """Desplegar archivos SQL de esquemas"""
        try:
            schemas_path = Path(schemas_dir)
            if not schemas_path.exists():
                logger.error(f"Directorio de esquemas no encontrado: {schemas_dir}")
                return False
            
            schema_files = sorted(schemas_path.glob("*.sql"))
            logger.info(f"Encontrados {len(schema_files)} archivos de esquema")
            
            for schema_file in schema_files:
                logger.info(f"Desplegando esquema: {schema_file.name}")
                
                with open(schema_file, 'r') as f:
                    query = f.read()
                
                # Reemplazar placeholders de proyecto
                query = query.replace('{project_id}', self.project_id)
                query = query.replace('{gcs_bucket}', f'retail-claims-etl')
                
                try:
                    job = self.client.query(query)
                    job.result()  # Esperar a que se complete
                    logger.info(f"✓ Esquema desplegado: {schema_file.name}")
                except GoogleAPIError as e:
                    logger.warning(f"⚠️  Error desplegando {schema_file.name}: {str(e)}")
                    # Continuar con el siguiente archivo
            
            return True
        
        except Exception as e:
            logger.error(f"Error desplegando esquemas: {str(e)}")
            return False
    
    def deploy_stored_procedures(self, procedures_dir: str) -> bool:
        """Desplegar stored procedures"""
        try:
            procedures_path = Path(procedures_dir)
            if not procedures_path.exists():
                logger.error(f"Directorio de procedimientos no encontrado: {procedures_dir}")
                return False
            
            procedure_files = sorted(procedures_path.glob("*.sql"))
            logger.info(f"Encontrados {len(procedure_files)} archivos de procedimiento")
            
            for procedure_file in procedure_files:
                logger.info(f"Desplegando procedimiento: {procedure_file.name}")
                
                with open(procedure_file, 'r') as f:
                    query = f.read()
                
                # Reemplazar placeholders
                query = query.replace('{project_id}', self.project_id)
                
                try:
                    job = self.client.query(query)
                    job.result()  # Esperar a que se complete
                    logger.info(f"✓ Procedimiento desplegado: {procedure_file.name}")
                except GoogleAPIError as e:
                    logger.warning(f"⚠️  Error desplegando {procedure_file.name}: {str(e)}")
                    # Continuar con el siguiente archivo
            
            return True
        
        except Exception as e:
            logger.error(f"Error desplegando procedimientos: {str(e)}")
            return False
    
    def verify_deployment(self) -> bool:
        """Verificar que los esquemas y tablas fueron creados"""
        try:
            logger.info("Verificando despliegue...")
            
            # Verificar datasets
            datasets = ['retail_claims_bronze', 'retail_claims_silver', 'retail_claims_gold']
            for dataset_id in datasets:
                dataset = self.client.get_dataset(f"{self.project_id}.{dataset_id}")
                logger.info(f"✓ Dataset encontrado: {dataset_id}")
                
                # Listar tablas en el dataset
                tables = self.client.list_tables(dataset_id)
                table_count = sum(1 for _ in tables)
                logger.info(f"  └─ {table_count} tabla(s) en {dataset_id}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error verificando despliegue: {str(e)}")
            return False


def main():
    """Función principal"""
    parser = argparse.ArgumentParser(
        description='Desplegar esquemas y procedimientos a BigQuery'
    )
    parser.add_argument(
        '--project',
        required=True,
        help='ID del proyecto GCP'
    )
    parser.add_argument(
        '--schemas-dir',
        default='bigquery/schemas',
        help='Directorio con archivos de esquema SQL'
    )
    parser.add_argument(
        '--procedures-dir',
        default='bigquery/stored_procedures',
        help='Directorio con archivos de procedimientos SQL'
    )
    
    args = parser.parse_args()
    
    deployer = BigQueryDeployer(args.project)
    
    # Desplegar esquemas
    logger.info("\n=== Desplegando Esquemas ===")
    schemas_ok = deployer.deploy_schemas(args.schemas_dir)
    
    # Desplegar procedimientos
    logger.info("\n=== Desplegando Procedimientos ===")
    procedures_ok = deployer.deploy_stored_procedures(args.procedures_dir)
    
    # Verificar despliegue
    logger.info("\n=== Verificando Despliegue ===")
    verification_ok = deployer.verify_deployment()
    
    # Resumen final
    if schemas_ok and procedures_ok and verification_ok:
        logger.info("\n✅ Despliegue completado exitosamente")
        return 0
    else:
        logger.error("\n❌ Despliegue completado con errores")
        return 1


if __name__ == '__main__':
    sys.exit(main())
