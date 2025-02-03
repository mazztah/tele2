import os
import asyncio
import json
from flask import Flask, request
from dotenv import load_dotenv
import telegram
import openai
import logging

# Lade Umgebungsvariablen aus .env
load_dotenv()

# API-Schlüssel aus Umgebungsvariablen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialisierung von OpenAI-Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Initialisierung des Telegram-Bots mit erweitertem Connection-Pool
bot = telegram.Bot(
    token=TELEGRAM_BOT_TOKEN, 
    request=telegram.utils.request.Request(con_pool_size=10)
)

# Flask-App erstellen
app = Flask(__name__)

# Logging aktivieren
logging.basicConfig(level=logging.INFO)

# Funktion zur Antwortgenerierung mit OpenAI
def generate_response(message):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein hilfreicher Telegram-Bot."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# Webhook für eingehende Telegram-Nachrichten
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        logging.info(f"Update erhalten:\n{json.dumps(update, indent=4)}")
        
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            message_text = update["message"]["text"]

            # Antwort mit OpenAI generieren
            answer = generate_response(message_text)

            # Asynchron Nachricht senden
            asyncio.run(bot.send_message(chat_id=chat_id, text=answer))

        return "", 200
    except Exception as e:
        logging.error(f"Fehler bei der Verarbeitung des Webhooks: {e}")
        return "Internal Server Error", 500

# Flask-Server starten
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000, debug=True)



