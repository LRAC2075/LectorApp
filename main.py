import os
from flask import Flask, request, render_template, jsonify
from PIL import Image
import pytesseract 
from pdf2image import convert_from_path
import google.generativeai as genai

# --- CONFIGURACIÓN INICIAL ---
# Leemos la clave desde las variables de entorno de Render para mayor seguridad
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    print("ALERTA: La variable de entorno GOOGLE_API_KEY no está configurada.")
genai.configure(api_key=GOOGLE_API_KEY)

# Le decimos a Flask que los archivos estáticos y templates están en la misma carpeta 'static'
app = Flask(__name__, static_folder='static', template_folder='static')
app.json.ensure_ascii = False
UPLOAD_FOLDER = '/tmp' # Usamos la carpeta temporal del servidor
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
        # Capturamos los dos idiomas desde el formulario
        input_lang_code = request.form.get('lang', 'spa')
        output_lang_name = request.form.get('output_lang', 'Mismo idioma (solo corregir)')
        
        if not file or file.filename == '': return jsonify({'error': 'Ningún archivo fue seleccionado.'}), 400

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        # Extracción con Tesseract
        raw_text = ""
        if file.filename.lower().endswith('.pdf'):
            images = convert_from_path(filepath, dpi=300)
            text_pages = [pytesseract.image_to_string(p, lang=input_lang_code) for p in images]
            raw_text = "\n\n".join(text_pages)
        else:
            image = Image.open(filepath)
            raw_text = pytesseract.image_to_string(image, lang=input_lang_code)

        # Corrección y Traducción con IA
        final_text = raw_text
        if raw_text.strip():
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            # Construimos el prompt dinámicamente
            if output_lang_name == 'Mismo idioma (solo corregir)':
                prompt = f"Actúa como un editor experto. Corrige y formatea el siguiente texto de un OCR, que está en el idioma con código '{input_lang_code}'. Repara palabras incompletas, añade tildes y mejora la puntuación. El resultado debe estar solo en el idioma original. Texto a corregir: --- {raw_text} ---"
            else:
                prompt = f"Primero, corrige el siguiente texto de un OCR, que está en el idioma '{input_lang_code}'. Segundo, traduce el texto ya corregido al idioma {output_lang_name}. El resultado final debe ser únicamente la traducción limpia y formateada. Texto a procesar: --- {raw_text} ---"
            
            response = model.generate_content(prompt)
            if response.parts:
                final_text = response.text

        return jsonify({'text': final_text})

    except Exception as e:
        print(f"ERROR DETALLADO: {e}")
        return jsonify({'error': f"Ocurrió un error en el servidor. Revisa los logs para más detalles."}), 500
    
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

# No necesitamos el if __name__ == '__main__' para Gunicorn