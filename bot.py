import os
import logging
import asyncio
from flask import Flask, request
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from dotenv import load_dotenv
import openai

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# API-Schlüssel und Webhook-URL aus der Umgebung laden
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # z.B. "https://deinbot.onrender.com"

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask-App initialisieren
app = Flask(__name__)

# Telegram-Bot und Application initialisieren
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# OpenAI API-Key setzen
openai.api_key = OPENAI_API_KEY

# Funktion zum Generieren einer Antwort mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot hosted on Render. Your purpose is to provide informative, concise, and engaging responses while maintaining a friendly and professional tone. Always prioritize clarity and accuracy."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message['content'].strip()

# Handler für den /start-Befehl (synchroner Handler)
def start(update, context):
    update.message.reply_text("Hallo! Ich bin dein Bot. Wie kann ich dir helfen?")

# Asynchroner Nachrichten-Handler für Textnachrichten
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Telegram-Handler registrieren
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Synthetischer, synchroner Flask-WebHook-Endpunkt
@app.route('/webhook', methods=['POST'])
def webhook():
    # Lese JSON-Daten aus der Anfrage
    data = request.get_json(force=True)
    logger.info(f"Received update: {data}")
    # Wandle die Daten in ein Telegram-Update um
    update = telegram.Update.de_json(data, bot)
    # Verarbeite das Update; asyncio.run() blockiert bis zur Fertigstellung
    asyncio.run(application.process_update(update))
    return "OK", 200

if __name__ == '__main__':
    # Setze den Webhook bei Telegram (synchron mittels asyncio.run())
    port = int(os.environ.get("PORT", 5000))
    asyncio.run(bot.set_webhook(f"{WEBHOOK_URL}/webhook"))
    # Starte die Flask-App; Render erwartet, dass der Port aus der Umgebungsvariablen PORT gelesen wird.
    app.run(host="0.0.0.0", port=port)

