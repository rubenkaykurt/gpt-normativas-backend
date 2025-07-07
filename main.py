from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from dotenv import load_dotenv
import os
import time

# Cargar variables de entorno (.env)
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No se encontró la variable OPENAI_API_KEY en el entorno")

# Inicializar cliente OpenAI
client = OpenAI(api_key=api_key)

# Flask App
app = Flask(__name__)
CORS(app)

# ID de tu Assistant creado con tus PDFs
ASSISTANT_ID = "asst_CqBekTmldddt9ESsp0QJEoHm"  
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    try:
        # Crear nuevo thread para esta consulta
        thread = client.beta.threads.create()

        # Añadir mensaje del usuario al thread
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_message
        )

        # Ejecutar el Assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )

        # Esperar a que termine
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status == "completed":
                break
            elif run_status.status == "failed":
                return jsonify({"error": "La ejecución del assistant ha fallado"}), 500
            time.sleep(1)

        # Obtener la respuesta
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        reply = messages.data[0].content[0].text.value

        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Ejecutar la app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
