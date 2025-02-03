import os
import asyncio
import logging
from flask import Flask, request
from dotenv import load_dotenv
import telegram
import openai

# Lade Umgebungsvariablen aus .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Überprüfung, ob Umgebungsvariablen geladen wurden
if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Fehlende Umgebungsvariablen! Stelle sicher, dass die .env Datei existiert.")

# Initialisierung des Telegram-Bots mit asyncio-kompatibler API
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Initialisierung von OpenAI-Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Flask-App initialisieren
app = Flask(__name__)

async def send_telegram_message(chat_id, text):
    """Sendet eine Nachricht asynchron an Telegram."""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logging.error(f"Fehler beim Senden der Nachricht an Telegram: {e}")

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

@app.route('/webhook', methods=['POST'])
def webhook():
    """Verarbeitet eingehende Telegram-Webhook-Nachrichten."""
    try:
        update = request.get_json()
        logging.info(f"Update erhalten: {update}")

        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            message_text = update["message"]["text"]

            # OpenAI Antwort generieren
            answer = generate_response(message_text)

            # Telegram-Nachricht asynchron senden
            asyncio.run(send_telegram_message(chat_id, answer))

        return "", 200
    except Exception as e:
        logging.error(f"Fehler bei der Verarbeitung des Webhooks: {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=10000, debug=True)

