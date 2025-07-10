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


@app.route("/save-conversation", methods=["POST"])
def save_conversation():
    data = request.json
    user_id = data.get("user_id") or "demo"
    title = data.get("title", "Sin título")
    messages = data.get("messages")
    timestamp = data.get("timestamp") or datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    if not user_id or not messages:
        return jsonify({"status": "error", "message": "Faltan datos"}), 400

    folder_path = os.path.join("historial", user_id)
    os.makedirs(folder_path, exist_ok=True)

    safe_title = "".join(c for c in title if c.isalnum() or c in (" ", "_")).strip().replace(" ", "_")
    filename = f"{timestamp}_{safe_title}.json"
    filepath = os.path.join(folder_path, filename)

    print(f"💾 Guardando historial en: {filepath}")

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({
            "user_id": user_id,
            "title": title,
            "timestamp": timestamp,
            "messages": messages
        }, f, ensure_ascii=False, indent=2)

    return jsonify({"status": "ok"})


# ======== CARGAR HISTORIAL DE USUARIO ========
@app.route("/get-history/<user_id>", methods=["GET"])
def get_history(user_id):
    historial = []
    folder_path = os.path.join("historial", user_id)
    if not os.path.exists(folder_path):
        return jsonify([])

    for file in os.listdir(folder_path):
        if file.endswith(".json"):
            with open(os.path.join(folder_path, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                historial.append({
                    "title": data.get("title", "Sin título"),
                    "timestamp": data.get("timestamp"),
                    "messages": data.get("messages")
                })

    historial.sort(key=lambda x: x["timestamp"], reverse=True)
    return jsonify(historial)


# ======== INICIAR FLASK APP ========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)