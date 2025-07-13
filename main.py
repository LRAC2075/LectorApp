import os
import io
from flask import Flask, request, render_template, jsonify
from pdf2image import convert_from_path
from google.cloud import vision

# --- CONFIGURACIÓN PARA RENDER ---
# Busca las credenciales en la ruta segura de Render
CREDENTIALS_PATH = '/etc/secrets/google-credentials.json'
if os.path.exists(CREDENTIALS_PATH):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
else:
    # Si no, busca el archivo localmente (para pruebas en tu PC)
    local_credentials_path = 'google-credentials.json'
    if os.path.exists(local_credentials_path):
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = local_credentials_path
    else:
        print("ALERTA: No se encontró el archivo de credenciales de Google.")

# Configuración de Flask
app = Flask(__name__, static_folder='static', template_folder='static')
app.json.ensure_ascii = False
UPLOAD_FOLDER = '/tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True, mode=0o777)

# --- RUTAS ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    filepath = None
    try:
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
            # Convertimos el PDF a imágenes en memoria
            images_from_pdf = convert_from_path(filepath, dpi=200) # Reducimos DPI para ahorrar memoria
            
            for i, pil_image in enumerate(images_from_pdf):
                with io.BytesIO() as output:
                    pil_image.save(output, format="PNG")
                content = output.getvalue()
                
                image = vision.Image(content=content)
                response = client.document_text_detection(image=image)
                all_texts.append(response.full_text_annotation.text)
        else:
            with open(filepath, 'rb') as image_file:
                content = image_file.read()
            
            image = vision.Image(content=content)
            response = client.document_text_detection(image=image)
            all_texts.append(response.full_text_annotation.text)

        final_text = "\n\n--- Página Siguiente ---\n\n".join(all_texts)
        return jsonify({'text': final_text})

    except Exception as e:
        print(f"ERROR DETALLADO: {e}")
        return jsonify({'error': "Ocurrió un error en el servidor. Revisa los logs."}), 500
    
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)