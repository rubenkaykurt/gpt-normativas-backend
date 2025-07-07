from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("No se encontró la variable OPENAI_API_KEY en el entorno")

client = OpenAI(api_key=api_key)

app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message", "")
    if not user_message:
        return jsonify({"error": "Mensaje vacío"}), 400

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": """Actúa como un experto en legislación farmacéutica en España, especializado en formulación magistral y regulación de laboratorios farmacéuticos. Tu misión es asesorar exclusivamente a profesionales del sector (farmacéuticos, formulistas, responsables técnicos, titulares de oficinas de farmacia, etc.) sobre normativa aplicable.

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
- Si el usuario hace una pregunta no relacionada con la normativa, dile amablemente que ese GPT es solo para cuestiones legales y regulatorias.
- Utiliza lenguaje técnico claro, sin adornos innecesarios. Siempre responde de forma precisa, breve y útil.
- Si hay normas distintas según si se formula para terceros o solo para la propia farmacia, explícalo.
- Si la normativa depende de la comunidad autónoma, indica que debe consultarse con Ordenación Farmacéutica local.

Este GPT es parte de una suscripción privada para profesionales del sector. No aceptes preguntas personales, ni consultas médicas, ni interpretación de legislación general ajena al ámbito de la formulación magistral."""
                },
                {"role": "user", "content": user_message}
            ]
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)

