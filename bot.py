import os
import asyncio
import json
from flask import Flask, request
from dotenv import load_dotenv
from telegram import Bot
from telegram.constants import ParseMode
import openai
import logging

# Lade Umgebungsvariablen aus .env
load_dotenv()

# API-Schlüssel aus Umgebungsvariablen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialisierung des Telegram-Bots (jetzt asynchron)
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Initialisierung von OpenAI-Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Flask-App erstellen
app = Flask(__name__)

# Logging aktivieren
logging.basicConfig(level=logging.INFO)

# Funktion zur Antwortgenerierung mit OpenAI
async def generate_response(message):
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
async def webhook():
    try:
        update = request.get_json()
        logging.info(f"Update erhalten:\n{json.dumps(update, indent=4)}")

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            message_text = update["message"]["text"]

            # Antwort mit OpenAI generieren
            answer = await generate_response(message_text)

            # Nachricht senden (asynchron)
            await bot.send_message(chat_id=chat_id, text=answer, parse_mode=ParseMode.MARKDOWN)

        return "", 200
    except Exception as e:
        logging.error(f"Fehler bei der Verarbeitung des Webhooks: {e}")
        return "Internal Server Error", 500

# Flask-Server starten
if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()  # Ermöglicht asyncio in Flask

    app.run(host="0.0.0.0", port=10000, debug=True)
