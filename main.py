import os
import io
from flask import Flask, request, render_template, jsonify
from PIL import Image
from pdf2image import convert_from_path
from google.cloud import vision

# --- CONFIGURACIÓN PARA RENDER ---
CREDENTIALS_PATH = '/etc/secrets/google-credentials.json'
if os.path.exists(CREDENTIALS_PATH):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
else:
    if os.path.exists('google-credentials.json'):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-credentials.json'
    else:
        print("ALERTA: No se encontró el archivo de credenciales de Google.")

app = Flask(__name__, static_folder='static', template_folder='static')
app.json.ensure_ascii = False
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    filepath = None
    try:
        print("Iniciando el procesamiento de un archivo...")
        if 'file' not in request.files:
            return jsonify({'error': 'No se envió ningún archivo.'}), 400
        
        file = request.files['file']
        if not file or file.filename == '':
            return jsonify({'error': 'Ningún archivo fue seleccionado.'}), 400

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        client = vision.ImageAnnotatorClient()
        all_texts = []

        if file.filename.lower().endswith('.pdf'):
            print(f"Procesando PDF: {file.filename}. Convirtiendo a imágenes...")
            # OPTIMIZACIÓN: Procesamos solo las primeras 5 páginas para no exceder la memoria
            images_from_pdf = convert_from_path(filepath, dpi=200, last_page=5)
            print(f"PDF convertido a {len(images_from_pdf)} imágenes. Enviando a la API...")
            
            for i, pil_image in enumerate(images_from_pdf):
                print(f"  - Procesando página {i+1}...")
                with io.BytesIO() as output:
                    pil_image.save(output, format="PNG")
                content = output.getvalue()
                
                image = vision.Image(content=content)
                response = client.document_text_detection(image=image)
                if response.error.message: raise Exception(response.error.message)
                all_texts.append(response.full_text_annotation.text)
        else:
            print(f"Procesando imagen: {file.filename}...")
            with open(filepath, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            if response.error.message: raise Exception(response.error.message)
            all_texts.append(response.full_text_annotation.text)

        print("Proceso completado exitosamente.")
        final_text = "\n\n--- Página Siguiente ---\n\n".join(all_texts)
        return jsonify({'text': final_text})

    except Exception as e:
        print(f"ERROR DETALLADO: {e}")
        return jsonify({'error': f"Ocurrió un error en el servidor. Revisa los logs."}), 500
    
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)