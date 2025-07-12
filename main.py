import os
import io
from flask import Flask, request, render_template, jsonify
from pdf2image import convert_from_path
from google.cloud import vision

# --- CONFIGURACIÓN PARA RENDER ---
# Render montará el archivo de credenciales en esta ruta específica
# Lo configuraremos en el panel de Render en un paso posterior.
CREDENTIALS_PATH = '/etc/secrets/google-credentials.json'
if os.path.exists(CREDENTIALS_PATH):
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = CREDENTIALS_PATH
else:
    # Esto es para que siga funcionando en tu PC si el archivo está localmente
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = 'google-credentials.json'

app = Flask(__name__, static_folder='static', template_folder='static')
app.json.ensure_ascii = False
UPLOAD_FOLDER = '/tmp/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --- RUTAS DE LA APLICACIÓN ---
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    filepath = None
    try:
        tessdata_dir = r'C:\Program Files\Tesseract-OCR\tessdata'
        os.environ['TESSDATA_PREFIX'] = tessdata_dir

        if 'file' not in request.files: return jsonify({'error': 'No se envió ningún archivo.'}), 400
        
        file = request.files['file']
        input_lang_name = request.form.get('lang', 'Inglés')
        output_lang_name = request.form.get('output_lang', 'Mismo idioma (solo corregir)')
        lang_map = {'inglés': 'eng', 'español': 'spa', 'portugués': 'por'}
        lang_code = lang_map.get(input_lang_name.lower(), 'eng')
        
        if file.filename == '': return jsonify({'error': 'Ningún archivo fue seleccionado.'}), 400

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        raw_text = ""
        if file.filename.lower().endswith('.pdf'):
            poppler_ruta = r"C:\poppler-24.08.0\Library\bin"
            images = convert_from_path(filepath, poppler_path=poppler_ruta, dpi=300)
            text_pages = [pytesseract.image_to_string(p, lang=lang_code) for p in images]
            raw_text = "\n\n".join(text_pages)
        else:
            image = Image.open(filepath)
            raw_text = pytesseract.image_to_string(image, lang=lang_code)

        final_text = raw_text
        if raw_text.strip():
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            # --- PROMPT MEJORADO ---
            # Se ha añadido una instrucción explícita para reparar palabras incompletas.
            if output_lang_name == 'Mismo idioma (solo corregir)':
                prompt = f"""
                Tu tarea es actuar como un experto en corrección de textos extraídos por OCR.
                Corrige y formatea el siguiente texto. El idioma original es {input_lang_name}.
                Presta especial atención a palabras a las que les puedan faltar letras o tildes (ej. 'fabricacin' debe ser 'fabricación').
                Usa el contexto para deducir la palabra correcta. Mejora la puntuación y el uso de mayúsculas.
                No añadas información que no esté implícita en el texto.

                Texto a corregir:
                ---
                {raw_text}
                ---
                """
            else:
                prompt = f"""
                Realiza dos pasos:
                1. Primero, corrige el siguiente texto de un OCR. El idioma es {input_lang_name}. Presta especial atención a palabras incompletas o sin tildes, usando el contexto para repararlas.
                2. Segundo, traduce el texto ya corregido al idioma {output_lang_name}.
                El resultado final debe ser únicamente la traducción limpia y formateada.

                Texto a procesar:
                ---
                {raw_text}
                ---
                """
            
            response = model.generate_content(prompt)
            if response.parts:
                final_text = response.text

        return jsonify({'text': final_text})

    except Exception as e:
        return jsonify({'error': f"Ocurrió un error en el servidor: {str(e)}"}), 500
    
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True)