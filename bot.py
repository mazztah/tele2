from flask import Flask, request
import telegram
import openai
import json
import os
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# API-Schlüssel aus Umgebungsvariablen abrufen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Fehlende Umgebungsvariablen: TELEGRAM_BOT_TOKEN oder OPENAI_API_KEY")

# Initialisierung des Telegram-Bots
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Initialisierung von OpenAI-Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

def generate_response(message):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Du bist ein hilfreicher Telegram-Bot."},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Fehler bei OpenAI-Anfrage: {e}")
        return "Entschuldigung, ich konnte keine Antwort generieren."

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # JSON-Daten von Telegram abrufen
        update = request.get_json()
        print("Update erhalten:")
        print(json.dumps(update, indent=4))

        # Überprüfen, ob es sich um eine Nachricht mit Text handelt
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            message_text = update["message"]["text"]

            # Antwort mit OpenAI generieren
            answer = generate_response(message_text)

            # Antwort an den Chat senden
            bot.send_message(chat_id=chat_id, text=answer)

        return "", 200
    except Exception as e:
        print(f"Fehler bei der Verarbeitung des Webhooks: {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000, debug=True)

