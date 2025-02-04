import os
import logging
import asyncio
from flask import Flask, request
import telegram
from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv
import openai

# Lade Umgebungsvariablen aus der .env-Datei
load_dotenv()

# Konfiguration aus Umgebungsvariablen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 5000))

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask-App initialisieren
app = Flask(__name__)

# Telegram-Bot und Application initialisieren
bot = Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# OpenAI API-Key setzen
openai.api_key = OPENAI_API_KEY

# Funktion zum Generieren von Antworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot hosted on ply.onrender.com. Your purpose is to provide informative, concise, and engaging responses while maintaining a friendly and professional tone. Always prioritize clarity and accuracy."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# Asynchroner Handler für eingehende Nachrichten
async def handle_message(update: Update, context):
    message = update.message.text
    response = generate_response(message)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Registriere den Nachrichten-Handler
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Flask-Route: Healthcheck (optional)
@app.route("/", methods=["GET"])
def home():
    return "OK", 200

# Flask-Route: Webhook-Endpunkt
@app.route("/webhook", methods=["POST"])
def webhook():
    # Lese das eingehende Telegram-Update
    data = request.get_json(force=True)
    logger.info(f"Received update: {data}")
    update = Update.de_json(data, bot)
    # Verarbeite das Update – blockierend mit asyncio.run()
    asyncio.run(application.process_update(update))
    return "OK", 200

# Funktion zum Setzen des Webhooks (asynchron)
async def set_webhook():
    webhook_endpoint = f"{WEBHOOK_URL}/webhook"
    await bot.set_webhook(url=webhook_endpoint)
    logger.info(f"Webhook gesetzt: {webhook_endpoint}")

# Hauptprogramm
if __name__ == "__main__":
    # Webhook setzen (mit einer eigenen Event-Loop)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_webhook())
    # Starte den Flask-Webserver; Render verwendet den in der Umgebungsvariable PORT angegebenen Port
    app.run(host="0.0.0.0", port=PORT)

