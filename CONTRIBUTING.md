# Guía de Contribución - ETL Retail Claims

## 🎯 Objetivos del Proyecto

Este proyecto implementa un pipeline ETL completo para procesamiento de reclamos retail usando Google Cloud Platform.

## 📝 Estructura del Proyecto

```
etl-retail-claims/
├── dags/                          # DAGs de Airflow
├── cloud_functions/               # Cloud Functions (ingesta)
├── dataproc/                      # Jobs de Spark
│   ├── jobs/                      # Scripts PySpark
│   └── configs/                   # Configuraciones
├── bigquery/                      # Esquemas y procedimientos
│   ├── schemas/                   # DDL de tablas
│   └── stored_procedures/         # Stored procedures
├── config/                        # Configuraciones del proyecto
├── tests/                         # Tests unitarios e integración
├── scripts/                       # Scripts de utilidad
└── monitoring/                    # Configuración de alertas
```

## 🛠️ Configuración del Ambiente

### 1. Prerequisites
```bash
# Instalar Python 3.8+
python --version

# Instalar Google Cloud SDK
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Configurar credenciales
gcloud auth application-default login
```

### 2. Setup Local
```bash
# Clonar repositorio
git clone <repo-url>
cd etl-retail-claims

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar configuración
cp config/secrets_template.yaml config/secrets.yaml
cp .env.example .env
```

## 🚀 Desarrollo

### Crear una Nueva Feature

```bash
# 1. Crear rama
git checkout -b feature/tu-feature

# 2. Realizar cambios
# 3. Ejecutar tests
pytest tests/ -v

# 4. Commitear cambios
git add .
git commit -m "feat: descripción de cambios"

# 5. Push y crear Pull Request
git push origin feature/tu-feature
```

### Patrones de Código

#### Cloud Functions
- Usar clases para lógica reutilizable
- Incluir logging en todos los métodos
- Manejo robusto de excepciones
- Retornar JSON con status y mensajes claros

#### PySpark Jobs
- Usar funciones de pyspark.sql para optimización
- Loguear paso a paso la transformación
- Incluir validación de datos
- Regresar reportes de calidad

#### SQL Procedures
- Usar MERGE para inserciones/actualizaciones
- Crear tablas temporales para lógica compleja
- Incluir comentarios en reglas de negocio
- Optimizar con índices

#### DAGs Airflow
- Usar operadores específicos del provider (no BashOperator)
- Incluir PythonOperator para validaciones
- Manejar XCom para pasar datos entre tareas
- Usar trigger_rule apropiadamente

## 🧪 Testing

### Ejecutar Tests
```bash
# Tests unitarios
pytest tests/unit/ -v

# Con coverage
pytest tests/unit/ --cov=. --cov-report=html

# Tests de integración (requiere GCP)
pytest tests/integration/ -v
```

### Escribir Tests
```python
import unittest

class TestMyFeature(unittest.TestCase):
    def test_something(self):
        # Arrange
        input_data = {"key": "value"}
        
        # Act
        result = my_function(input_data)
        
        # Assert
        self.assertEqual(result, expected_value)
```

## 📊 Despliegue

### A Staging
```bash
# Revisar cambios
git diff main

# Ejecutar tests en CI
# (Los tests corren automáticamente en GitHub Actions)

# Desplegar a staging (si pruebas pasan)
bash scripts/deploy_gcp.sh your-staging-project-id
```

### A Producción
```bash
# Crear release
git tag -a v1.0.0 -m "Release 1.0.0"
git push origin v1.0.0

# Desplegar a producción
bash scripts/deploy_gcp.sh your-production-project-id
```

## 📋 Checklist de Desarrollo

- [ ] Código sigue PEP8
- [ ] Tests incluidos y pasando
- [ ] Docstrings en funciones
- [ ] Logging en puntos clave
- [ ] Manejo de errores
- [ ] Actualizado README si es necesario
- [ ] Commits con mensajes claros

## 🐛 Reportar Bugs

1. Verificar que el bug no esté reportado
2. Crear issue con:
   - Título descriptivo
   - Pasos para reproducir
   - Comportamiento esperado
   - Comportamiento actual
   - Logs/screenshots

## 💡 Proponer Features

1. Crear discussion primero
2. Describir:
   - Objetivo de la feature
   - Casos de uso
   - Impacto en el pipeline
   - Requerimientos técnicos

## 📚 Recursos

- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Apache Airflow](https://airflow.apache.org/)
- [PySpark SQL](https://spark.apache.org/docs/latest/sql-programming-guide.html)
- [BigQuery Documentation](https://cloud.google.com/bigquery/docs)

## ✉️ Contacto

Data Engineering Team - data-alerts@company.com

---

¡Gracias por contribuir al proyecto! 🎉
