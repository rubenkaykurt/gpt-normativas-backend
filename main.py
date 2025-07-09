from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No se encontró la variable OPENAI_API_KEY en el entorno")

client = OpenAI(api_key=api_key)

app = Flask(__name__)
CORS(app)

# Asegúrate de que la carpeta de historial exista
os.makedirs("historial", exist_ok=True)

# ======== ENDPOINT PRINCIPAL DEL CHAT ========
SYSTEM_PROMPT = """
Actúa como un experto en legislación farmacéutica en España, especializado en formulación magistral...
"""

@app.route("/chat", methods=["POST"])
def chat():
    try:
        history = json.loads(request.form.get("history", "[]"))
        file = request.files.get("file")

        if file:
            filename = file.filename.lower()
            if filename.endswith(".pdf"):
                text = extract_text_from_pdf(file)
            elif filename.endswith((".png", ".jpg", ".jpeg")):
                text = extract_text_from_image(file)
            else:
                return jsonify({"reply": "❌ Tipo de archivo no soportado"}), 400
            history.append({ "role": "user", "content": text })

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        completion = client.chat.completions.create(
            model="gpt-4",
            messages=messages
        )
        reply = completion.choices[0].message.content
        return jsonify({ "reply": reply })

    except Exception as e:
        print("Error:", e)
        return jsonify({ "reply": "⚠️ Error al procesar la solicitud." })

# ======== FUNCIONES PARA PDF E IMÁGENES ========
def extract_text_from_pdf(file_storage):
    text = ""
    pdf_data = file_storage.read()
    doc = fitz.open("pdf", pdf_data)
    for page in doc:
        text += page.get_text()
    return text.strip()

def extract_text_from_image(file_storage):
    image = Image.open(file_storage.stream)
    return pytesseract.image_to_string(image).strip()


# ======== ENDPOINT PARA GUARDAR UNA CONVERSACIÓN ========
@app.route("/save-conversation", methods=["POST"])
def save_conversation():
    data = request.json
    user_id = data.get("user_id") or "demo"
    title = data.get("title", "Sin título")
    messages = data.get("messages")
    timestamp = data.get("timestamp")

    if not user_id or not messages:
        return jsonify({"status": "error", "message": "Faltan datos"}), 400

    safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
    filename = f"{user_id}_{safe_timestamp}.json"
    filepath = os.path.join("historial", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "user_id": user_id,
            "title": title,
            "timestamp": timestamp,
            "messages": messages
        }, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})


# ======== ENDPOINT PARA CARGAR EL HISTORIAL DEL USUARIO ========
@app.route("/get-history/<user_id>", methods=["GET"])
def get_history(user_id):
    historial = []
    for file in os.listdir("historial"):
        if file.startswith(user_id):
            with open(os.path.join("historial", file), "r", encoding="utf-8") as f:
                data = json.load(f)
                historial.append({
                    "title": data.get("title", "Sin título"),
                    "timestamp": data.get("timestamp"),
                    "messages": data.get("messages")
                })
    historial.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(historial)

from datetime import datetime

@app.route("/guardar_historial", methods=["POST"])
def guardar_historial():
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"status": "error", "message": "JSON inválido", "detail": str(e)}), 400

    user_id = data.get("user_id")
    title = data.get("title", "Sin título")
    messages = data.get("messages")
    timestamp = data.get("timestamp")

    if not user_id or not messages:
        return jsonify({"status": "error", "message": "Faltan datos"}), 400

    # Guardado
    safe_timestamp = timestamp.replace(":", "-").replace(" ", "_")
    filename = f"{user_id}_{safe_timestamp}.json"
    filepath = os.path.join("historial", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "user_id": user_id,
            "title": title,
            "timestamp": timestamp,
            "messages": messages
        }, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})


    # Crear título automático con los primeros 6-8 palabras
    titulo = messages[1]["content"][:40] + "..." if len(messages) > 1 else "Sin título"

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{user_id}_{timestamp}.json"
    filepath = os.path.join("historial", filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "user_id": user_id,
            "title": titulo,
            "timestamp": timestamp,
            "messages": messages
        }, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok", "filename": filename})

# ======== INICIAR FLASK ========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
