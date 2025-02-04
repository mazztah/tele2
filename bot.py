import os
import openai
import telegram
from telegram.ext import Application, MessageHandler, filters
from flask import Flask, request
from dotenv import load_dotenv
import asyncio

# Umgebungsvariablen laden
load_dotenv()

# API-Schlüssel aus der Umgebung laden
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Render-URL

# Flask-App starten
app = Flask(__name__)

# Telegram-Bot initialisieren
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# OpenAI API-Key setzen
openai.api_key = OPENAI_API_KEY

# Funktion zum Generieren von Antworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot hosted on Render."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# Handler für eingehende Nachrichten
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await update.message.reply_text(response)

# Flask-Route für den Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run(application.process_update(update))
    return "OK", 200

# Webhook setzen
async def set_webhook():
    await application.bot.set_webhook(f"{WEBHOOK_URL}/webhook")

# Starten
if __name__ == '__main__':
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Webhook setzen (asynchron)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(set_webhook())

    # Flask-Server starten
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
