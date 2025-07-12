import os
import numpy as np
import cv2
from flask import Flask, request, render_template, jsonify
from PIL import Image # <-- ASEGÚRATE DE QUE ESTA LÍNEA EXISTA
import pytesseract 
from pdf2image import convert_from_path
import google.generativeai as genai

# --- CONFIGURACIÓN INICIAL ---
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# ¡IMPORTANTE! Reemplaza con tu Clave de API real de Google AI Studio
GOOGLE_API_KEY = 'TU_API_KEY_AQUÍ' 
if 'TU_API_KEY_AQUÍ' in GOOGLE_API_KEY:
    print("ALERTA: Por favor, reemplaza 'TU_API_KEY_AQUÍ' con tu clave real de la API de Gemini en app.py")
genai.configure(api_key=GOOGLE_API_KEY)

app = Flask(__name__)
app.json.ensure_ascii = False
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def preprocess_image_robust(image):
    """
    Función robusta para limpiar una imagen para OCR.
    """
    img_array = np.array(image.convert('L'))
    denoised_image = cv2.medianBlur(img_array, 3)
    binary_image = cv2.adaptiveThreshold(denoised_image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    return binary_image

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
        lang_map = {'inglés': 'eng', 'español': 'spa', 'portugués': 'por'}
        lang = lang_map.get(request.form.get('lang', 'Inglés').lower(), 'eng')
        if file.filename == '': return jsonify({'error': 'Ningún archivo fue seleccionado.'}), 400

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)
        
        final_text_parts = []
        model = genai.GenerativeModel('gemini-1.5-flash-latest')

        prompt_template = """
        Por favor, corrige y formatea el siguiente texto extraído por un OCR. 
        Arregla errores ortográficos, añade tildes faltantes, corrige mayúsculas y minúsculas, 
        y mejora la puntuación para que el texto sea coherente y legible. 
        No añadas información nueva. Si una palabra no tiene sentido, intenta deducir la correcta.
        Texto a corregir:
        ---
        {}
        ---
        """

        if file.filename.lower().endswith('.pdf'):
            poppler_ruta = r"C:\poppler-24.08.0\Library\bin"
            images = convert_from_path(filepath, poppler_path=poppler_ruta, dpi=300)
            
            print(f"Procesando {len(images)} páginas del PDF...")
            for i, page_image in enumerate(images):
                print(f"  - Página {i+1}: Extrayendo texto con Tesseract...")
                processed_page = preprocess_image_robust(page_image)
                raw_text = pytesseract.image_to_string(processed_page, lang=lang)
                
                if raw_text.strip():
                    print(f"  - Página {i+1}: Corrigiendo texto con IA...")
                    prompt = prompt_template.format(raw_text)
                    response = model.generate_content(prompt)
                    
                    if response.parts:
                        final_text_parts.append(response.text)
                    else:
                        final_text_parts.append(raw_text)
                else:
                    final_text_parts.append("")
        else:
            print("Procesando imagen única...")
            # La variable se llama 'image'
            image = Image.open(filepath)
            # Pasamos 'image' a la función
            processed_image = preprocess_image_robust(image)
            # Usamos el resultado 'processed_image' para el OCR
            raw_text = pytesseract.image_to_string(processed_image, lang=lang)

            if raw_text.strip():
                prompt = prompt_template.format(raw_text)
                response = model.generate_content(prompt)
                if response.parts:
                    final_text_parts.append(response.text)
                else:
                    final_text_parts.append(raw_text)

        print("Proceso completado. Uniendo resultados.")
        extracted_text = "\n\n--- Página Siguiente ---\n\n".join(final_text_parts)
        return jsonify({'text': extracted_text})

    except Exception as e:
        print(f"ERROR: {e}")
        return jsonify({'error': f"Ocurrió un error en el servidor: {str(e)}"}), 500
    
    finally:
        if filepath and os.path.exists(filepath):
            os.remove(filepath)

if __name__ == '__main__':
    app.run(debug=True)