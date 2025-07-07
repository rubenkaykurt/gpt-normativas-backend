from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import tempfile
import base64

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No se encontró la variable OPENAI_API_KEY en el entorno")

client = OpenAI(api_key=api_key)

app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    history = request.form.get("history")
    if not history:
        return jsonify({"error": "Historial vacío"}), 400

    try:
        import json
        history = json.loads(history)

        # Procesar archivos si existen
        files_data = []
        vision_parts = []
        if "files" in request.files:
            for f in request.files.getlist("files"):
                if f.filename.lower().endswith(".pdf"):
                    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
                    f.save(temp.name)
                    openai_file = client.files.create(file=open(temp.name, "rb"), purpose="assistants")
                    files_data.append(openai_file.id)
                    os.unlink(temp.name)
                elif f.mimetype.startswith("image/"):
                    encoded_image = base64.b64encode(f.read()).decode("utf-8")
                    vision_parts.append({"type": "image_url", "image_url": {"url": f"data:{f.mimetype};base64,{encoded_image}"}})

        # Construir mensajes
        messages = [
            {
                "role": "system",
                "content": "Actúa como un experto en legislación farmacéutica en España, especializado en formulación magistral..."
            },
            *history
        ]

        # Agregar imagen si existe
        if vision_parts:
            messages.append({"role": "user", "content": vision_parts})

        # Elegir modelo según el tipo de contenido
        model_name = "gpt-4-vision-preview" if vision_parts else "gpt-4-turbo"

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            file_ids=files_data if files_data else None
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
