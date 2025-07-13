import os
from flask import Flask, request, render_template, jsonify
from PIL import Image
import pytesseract 
from pdf2image import convert_from_path
import google.generativeai as genai

# --- CONFIGURACIÓN INICIAL ---
# Ya no se necesitan rutas locales, Docker se encarga de Tesseract.
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY') # Leemos la clave desde las variables de entorno de Render
if not GOOGLE_API_KEY:
    print("ALERTA: La variable de entorno GOOGLE_API_KEY no está configurada.")
genai.configure(api_key=GOOGLE_API_KEY)

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
        if 'file' not in request.files: return jsonify({'error': 'No se envió ningún archivo.'}), 400
        file = request.files['file']
        lang = request.form.get('lang', 'spa') # Asumimos español si no se especifica
        if not file or file.filename == '': return jsonify({'error': 'Ningún archivo fue seleccionado.'}), 400

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        extracted_text = ""
        if file.filename.lower().endswith('.pdf'):
            images = convert_from_path(filepath, dpi=300)
            text_pages = [pytesseract.image_to_string(p, lang=lang) for p in images]
            extracted_text = "\n\n".join(text_pages)
        else:
            image = Image.open(filepath)
            extracted_text = pytesseract.image_to_string(image, lang=lang)

        if extracted_text.strip():
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            prompt = f"Por favor, corrige y formatea el siguiente texto de un OCR en {lang}: {extracted_text}"
            response = model.generate_content(prompt)
            if response.parts:
                extracted_text = response.text

        return jsonify({'text': extracted_text})
    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': f"Ocurrió un error en el servidor."}), 500
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)