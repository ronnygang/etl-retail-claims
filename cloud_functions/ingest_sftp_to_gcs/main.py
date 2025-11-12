import functions_framework
import paramiko
import logging
from google.cloud import storage
from datetime import datetime
import json
from typing import Dict, Any
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SFTPToGCSIngestion:
    """Ingesta de archivos JSON desde SFTP a Google Cloud Storage"""
    
    def __init__(self, config: Dict[str, Any]):
        self.sftp_host = config.get('sftp_host')
        self.sftp_port = config.get('sftp_port', 22)
        self.sftp_username = config.get('sftp_username')
        self.sftp_password = config.get('sftp_password')
        self.sftp_remote_path = config.get('sftp_remote_path')
        
        self.gcs_bucket = config.get('gcs_bucket')
        self.gcs_prefix = config.get('gcs_prefix', 'bronze/retail-claims')
        
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.gcs_bucket)
    
    def connect_sftp(self) -> paramiko.SSHClient:
        """Establecer conexión SFTP con manejo de errores"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                self.sftp_host,
                port=self.sftp_port,
                username=self.sftp_username,
                password=self.sftp_password,
                timeout=30
            )
            logger.info(f"Conexión SFTP exitosa a {self.sftp_host}")
            return ssh
        except Exception as e:
            logger.error(f"Error conectando a SFTP: {str(e)}")
            raise
    
    def download_from_sftp(self, ssh: paramiko.SSHClient, remote_file: str) -> bytes:
        """Descargar archivo desde SFTP"""
        try:
            sftp = ssh.open_sftp()
            with sftp.file(f"{self.sftp_remote_path}/{remote_file}", 'r') as remote:
                data = remote.read()
            sftp.close()
            logger.info(f"Archivo descargado: {remote_file}")
            return data
        except Exception as e:
            logger.error(f"Error descargando {remote_file}: {str(e)}")
            raise
    
    def validate_json(self, data: bytes) -> bool:
        """Validar que el archivo es un JSON válido"""
        try:
            json.loads(data)
            logger.info("Validación JSON exitosa")
            return True
        except json.JSONDecodeError as e:
            logger.error(f"JSON inválido: {str(e)}")
            return False
    
    def upload_to_gcs(self, data: bytes, filename: str) -> str:
        """Cargar archivo a Google Cloud Storage"""
        try:
            timestamp = datetime.utcnow().strftime('%Y/%m/%d')
            gcs_path = f"{self.gcs_prefix}/{timestamp}/{filename}"
            
            blob = self.bucket.blob(gcs_path)
            blob.upload_from_string(
                data,
                content_type='application/json'
            )
            logger.info(f"Archivo cargado a GCS: gs://{self.gcs_bucket}/{gcs_path}")
            return gcs_path
        except Exception as e:
            logger.error(f"Error cargando a GCS: {str(e)}")
            raise
    
    def process(self, remote_filename: str) -> Dict[str, Any]:
        """Proceso principal de ingesta"""
        ssh = None
        try:
            ssh = self.connect_sftp()
            
            # Descargar archivo
            data = self.download_from_sftp(ssh, remote_filename)
            
            # Validar JSON
            if not self.validate_json(data):
                raise ValueError("Archivo JSON inválido")
            
            # Cargar a GCS
            gcs_path = self.upload_to_gcs(data, remote_filename)
            
            return {
                'status': 'success',
                'gcs_path': f"gs://{self.gcs_bucket}/{gcs_path}",
                'filename': remote_filename,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error en proceso de ingesta: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'filename': remote_filename
            }
        finally:
            if ssh:
                ssh.close()


@functions_framework.http
def ingest_sftp_to_gcs(request):
    """Cloud Function HTTP trigger"""
    try:
        # Leer configuración desde variables de entorno
        config = {
            'sftp_host': os.getenv('SFTP_HOST'),
            'sftp_port': int(os.getenv('SFTP_PORT', '22')),
            'sftp_username': os.getenv('SFTP_USERNAME'),
            'sftp_password': os.getenv('SFTP_PASSWORD'),
            'sftp_remote_path': os.getenv('SFTP_REMOTE_PATH', '/retail-claims'),
            'gcs_bucket': os.getenv('GCS_BUCKET'),
            'gcs_prefix': os.getenv('GCS_PREFIX', 'bronze/retail-claims')
        }
        
        request_json = request.get_json(silent=True) or {}
        remote_filename = request_json.get('filename', 'claims.json')
        
        ingestion = SFTPToGCSIngestion(config)
        result = ingestion.process(remote_filename)
        
        return {
            'statusCode': 200 if result['status'] == 'success' else 400,
            'body': json.dumps(result)
        }
        
    except Exception as e:
        logger.error(f"Error en Cloud Function: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
