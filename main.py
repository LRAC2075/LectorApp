import os
import io
from flask import Flask, request, render_template, jsonify
from PIL import Image
from pdf2image import convert_from_path
import google.generativeai as genai

# --- CONFIGURACIÓN INICIAL ---
# Ya no necesitamos las rutas a Tesseract o Poppler locales. Las eliminamos.

GOOGLE_API_KEY = 'TU_API_KEY_AQUÍ' 
if 'TU_API_KEY_AQUÍ' in GOOGLE_API_KEY:
    print("ALERTA: Por favor, reemplaza 'TU_API_KEY_AQUÍ' con tu clave real de la API de Gemini en main.py")
genai.configure(api_key=GOOGLE_API_KEY)

app = Flask(__name__, template_folder='static')
app.json.ensure_ascii = False
UPLOAD_FOLDER = '/tmp' # Usamos la carpeta temporal raíz en Render
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- RUTAS DE LA APLICACIÓN ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    filepath = None
    try:
        if 'file' not in request.files: return jsonify({'error': 'No se envió ningún archivo.'}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({'error': 'Ningún archivo fue seleccionado.'}), 400

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        # --- EXTRACCIÓN Y CORRECCIÓN USANDO SOLO LA API DE GOOGLE ---
        # Este código usa la API de Google Vision (que es parte de Google Cloud)
        # para leer el texto directamente, eliminando la necesidad de Tesseract.
        # Es necesario tener las credenciales JSON configuradas en Render para que esto funcione.
        
        # (Aquí iría la lógica que usa google.cloud.vision, que habíamos implementado antes.
        # Si prefieres usar el flujo Tesseract + Gemini, entonces el problema es diferente y
        # requeriría instalar Tesseract en el servidor de Render usando un Dockerfile,
        # lo cual es un proceso mucho más complejo).

        # Asumiendo que nos quedamos con la última arquitectura funcional (Tesseract + Gemini)
        # pero adaptada para Render, el problema es que Tesseract no está instalado en el servidor.
        
        # Por simplicidad y robustez, volvamos a la arquitectura de solo Google API que no requiere Tesseract.
        # Requerirá reinstalar google-cloud-vision y ajustar el código.
        
        # --- CÓDIGO SIMPLIFICADO USANDO SOLO GEMINI (NECESITA IMAGEN) ---
        # Nota: Gemini no es ideal para OCR directo, Vision API es mejor.
        # Dado que el objetivo es mantenerlo simple, y ya tienes el código de Tesseract+Gemini
        # el problema es que Tesseract no está en el servidor de Render.
        
        # Para que tu código actual funcione, necesitarías Docker para instalar Tesseract en Render.
        # Dado que esto es muy complejo, la solución más VIABLE es la que habíamos discutido:
        # Usar una API en la nube que haga el OCR.
        
        # VAMOS A USAR EL CÓDIGO QUE USA GOOGLE VISION API, PUES ES EL ÚNICO
        # QUE NO DEPENDE DE PROGRAMAS LOCALES.
        
        # Asegúrate de tener 'google-cloud-vision' en tu requirements.txt
        from google.cloud import vision

        client = vision.ImageAnnotatorClient()
        content = None
        
        with open(filepath, 'rb') as f:
            content = f.read()

        image = vision.Image(content=content)
        response = client.document_text_detection(image=image)
        extracted_text = response.full_text_annotation.text

        return jsonify({'text': extracted_text})

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': f"Ocurrió un error en el servidor: {str(e)}"}), 500
    
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True)