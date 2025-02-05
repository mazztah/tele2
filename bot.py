import os
import logging
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
import asyncio
from threading import Thread

# 🔹 Umgebungsvariablen für API-Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🔹 Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔹 Flask App initialisieren
app = Flask(__name__)

# 🔹 OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# 🔹 Telegram-Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# 🔹 Event Loop für Async-Tasks
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# 🔹 Funktion zum Generieren von Textantworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully."},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()

# 🔹 Nachricht-Handler für alle Texteingaben
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await update.message.reply_text(response)

# 🔹 Fehlerbehandlung
async def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")

# 🔹 Flask-Route für den Webserver
@app.route('/')
def home():
    return "Bot is running!"

# 🔹 Handler hinzufügen
application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("Hallo! Ich bin dein AI-Chatbot.")))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)

# 🔹 Polling in separatem Thread starten
def start_polling():
    try:
        loop.run_until_complete(application.run_polling())
    except Exception as e:
        logger.error(f"Fehler beim Polling: {e}")

# 🔹 Flask-Server starten
def start_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

# 🔹 Threads für Flask & Polling starten
if __name__ == "__main__":
    Thread(target=start_flask, daemon=True).start()
    Thread(target=start_polling, daemon=True).start()
    while True:
        pass  # Hält das Hauptskript am Laufen





