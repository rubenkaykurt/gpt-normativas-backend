# Imagen base ligera con Python 3.11
FROM python:3.11-slim

# Evita prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar Tesseract y dependencias necesarias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar todos los archivos del proyecto al contenedor
COPY . /app

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Exponer el puerto por defecto (Render usará este)
EXPOSE 5000

# Comando para iniciar la aplicación Flask
CMD ["python", "main.py"]
