# Dockerfile para Cloud Function - Ingesta SFTP
FROM python:3.9-slim

WORKDIR /app

# Copiar archivos de requisitos
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código de la función
COPY main.py .

# Exponer puerto (opcional)
EXPOSE 8080

# Comando por defecto
CMD ["functions-framework", "--target=ingest_sftp_to_gcs", "--debug"]
