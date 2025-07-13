# Usamos una imagen oficial de Python 3.9 como base
FROM python:3.9-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Solo necesitamos instalar Poppler para manejar los PDFs
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

# Copiamos el archivo de dependencias
COPY requirements.txt .

# Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de los archivos
COPY . .

# Comando de inicio
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "main:app"]