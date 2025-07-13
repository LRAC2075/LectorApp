# Usamos una imagen oficial de Python 3.9 como base, que es muy estable
FROM python:3.9-slim

# Establecemos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Actualizamos los paquetes de Linux e instalamos las herramientas necesarias:
# tesseract-ocr: El motor de OCR.
# tesseract-ocr-spa/eng/por: Los paquetes de idioma para Tesseract.
# poppler-utils: La herramienta para manejar PDFs que necesita la librería pdf2image.
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-eng \
    tesseract-ocr-por \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copiamos el archivo de dependencias de Python
COPY requirements.txt .

# Instalamos las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto de los archivos de nuestra aplicación al contenedor
COPY . .

# Exponemos el puerto que usará el servidor Gunicorn
EXPOSE 8000

# El comando que se ejecutará cuando el contenedor inicie
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--timeout", "120", "main:app"]