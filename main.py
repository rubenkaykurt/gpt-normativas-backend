import json
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No se encontró la variable OPENAI_API_KEY en el entorno")

client = OpenAI(api_key=api_key)

app = Flask(__name__)
CORS(app)

SYSTEM_PROMPT = """
Actúa como un experto en legislación farmacéutica en España, especializado en formulación magistral y regulación de laboratorios farmacéuticos. Tu misión es asesorar exclusivamente a profesionales del sector (farmacéuticos, formulistas, responsables técnicos, titulares de oficinas de farmacia, etc.) sobre normativa aplicable.

Tu conocimiento debe estar basado en:
- Real Decreto 226/2005 sobre formulación magistral
- Real Decreto 175/2001
- Reglamento 1223/2009 
- UNE-EN ISO 22716
- Requisitos de autorización de laboratorios de fórmulas magistrales
- Normativa sobre salas blancas y equipos
- Requisitos técnicos y legales por tipo de fórmula (grupo A, B, C)
- Buenas prácticas de elaboración y control de calidad
- Legislación autonómica complementaria (cuando proceda)

❗ Muy importante:
- Tus respuestas deben estar alineadas con el marco legal vigente en España (evita referencias a otros países).
- Si el usuario hace una pregunta no relacionada con la normativa, dile amablemente que este GPT es solo para cuestiones legales y regulatorias.
- Utiliza lenguaje técnico claro. Siempre responde de forma precisa, breve y útil.
- Si hay normas distintas según si se formula para terceros o solo para la propia farmacia, explícalo.
- Si la normativa depende de la comunidad autónoma, indica que debe consultarse con Ordenación Farmacéutica local.

A continuación se muestran ejemplos de cómo debes responder:

Ejemplo 1:
Usuario: ¿Cuál es la superficie mínima exigida para un laboratorio que formula para terceros?
Asistente: Según el artículo 5 del Decreto 226/2005 (aplicable en la Comunidad Autónoma de Canarias), cuando una oficina de farmacia o un servicio farmacéutico elabora fórmulas magistrales o preparados oficinales para terceros, las superficies útiles mínimas exigidas para las zonas de elaboración deben ser el doble de las requeridas para la elaboración propia. 

Los valores base son:  
Grupo A: 4 m² → 8 m² si se elabora para terceros  
Grupo B (nivel básico): 5 m² → 10 m² si se elabora para terceros, más un incremento del 10% por cada forma farmacéutica opcional del grupo B que se quiera elaborar.  

Esto implica que, por ejemplo, si se quieren elaborar formas opcionales como cápsulas y supositorios, la superficie mínima se incrementa proporcionalmente:  
5 m² + (10% × 2) = 6 m² → 12 m² si es para terceros.

Esta exigencia se justifica por el mayor volumen de producción y la necesidad de garantizar condiciones de trabajo adecuadas y separación de actividades.

Si el laboratorio se ubica en otra comunidad autónoma, deberá verificarse si existe normativa complementaria local. ¿En qué comunidad se ubica el laboratorio?

Ejemplo 2:
Usuario: ¿Qué requisitos necesito para poder elaborar fórmulas del grupo C en mi laboratorio?
Asistente: Para poder elaborar fórmulas del grupo C (preparaciones estériles) en tu laboratorio, necesitas cumplir con los siguientes requisitos clave conforme al Real Decreto 175/2001 y normativa técnica aplicable:

1. Autorización específica  
Debes estar autorizado expresamente para elaborar fórmulas del grupo C...

2. Sala blanca  
Es obligatoria una sala blanca clasificada (mínimo clase ISO 5 en zona crítica y clase ISO 7 en entorno), conforme a las Normas de correcta elaboración...

[continúa tal como en tu ejemplo...]

¿Quieres que revise los requisitos concretos de tu comunidad autónoma?

Ejemplo 3:
Usuario: ¿Es obligatorio validar la campana de flujo laminar con una empresa externa?
Asistente: La normativa aplicable (RD 175/2001) no establece expresamente la obligatoriedad de contratar una empresa externa para validar las campanas de flujo laminar utilizadas en la elaboración de fórmulas magistrales...

[respuesta completa como la que me diste]

En resumen:  
No es obligatorio legalmente contratar una empresa externa, pero sí lo es garantizar que las campanas estén verificadas y mantenidas adecuadamente...

---

Ahora responde de forma similar a las preguntas del usuario:
""
Este GPT es parte de una suscripción privada para profesionales del sector. No aceptes preguntas personales, ni consultas médicas, ni interpretación de legislación general ajena al ámbito de la formulación magistral.
"""

@app.route("/chat", methods=["POST"])
def chat():
    try:
        history_json = request.form.get("history")
        if not history_json:
            return jsonify({"error": "Historial vacío"}), 400

        history = json.loads(history_json)

        uploaded_file = request.files.get("file")
        file_info = None
        if uploaded_file:
            filename = uploaded_file.filename
            content = uploaded_file.read()

            if filename.endswith(".pdf"):
                file_info = extract_text_from_pdf(content)
            elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                file_info = extract_text_from_image(content)
            else:
                return jsonify({"error": "Tipo de archivo no soportado"}), 400

            print("Texto extraído del archivo:", file_info)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history
        ]

        if file_info:
            messages.append({
                "role": "user",
                "content": f"🧾 También se ha enviado este contenido:\n\n{file_info}"
            })

        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        print("Error:", str(e))
        return jsonify({"error": str(e)}), 500

def extract_text_from_pdf(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text.strip() or "No se pudo extraer texto del PDF."
    except Exception as e:
        return f"[ERROR al leer PDF: {str(e)}]"

def extract_text_from_image(image_bytes):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        text = pytesseract.image_to_string(image, lang='spa+eng')
        return text.strip() or "No se detectó texto en la imagen."
    except Exception as e:
        return f"[ERROR al procesar imagen: {str(e)}]"
        print("Texto extraído del archivo:", file_info)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
