import os
import logging
import openai
from flask import Flask, request
import telegram
import asyncio
import nest_asyncio
from dotenv import load_dotenv

# .env-Datei laden
load_dotenv()

# Log-Level setzen
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# API-Schlüssel aus Umgebungsvariablen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Telegram Bot-Initialisierung ohne Request
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# OpenAI-Client-Initialisierung
openai.api_key = OPENAI_API_KEY
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Flask-App initialisieren
app = Flask(__name__)

# Nest Asyncio für Flask verwenden, um asynchrone Aufrufe zu ermöglichen
nest_asyncio.apply()

# Funktion zum Generieren einer Antwort von OpenAI
def generate_response(message):
    """Generiert eine Antwort von OpenAI."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein hilfreicher Telegram-Bot."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    
    return response.choices[0].message.content.strip()

# Flask-Route für den Webhook
@app.route('/webhook', methods=['POST'])
async def webhook():
    try:
        # JSON-Daten von Telegram empfangen
        update = request.get_json()
        logger.info(f"Update erhalten: {update}")

        # Überprüfen, ob eine Textnachricht vorhanden ist
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            message_text = update["message"]["text"]

            # Antwort generieren
            answer = generate_response(message_text)

            # Antwort an den Telegram-Chat senden
            await bot.send_message(chat_id=chat_id, text=answer)
        return "", 200
    except Exception as e:
        logger.error(f"Fehler bei der Verarbeitung des Webhooks: {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=10000, debug=True)




