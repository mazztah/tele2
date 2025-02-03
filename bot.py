import os
import logging
import asyncio
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from openai import OpenAI
from dotenv import load_dotenv  # Für Umgebungsvariablen

# Lade Umgebungsvariablen
load_dotenv()

# Konfiguration aus Umgebungsvariablen
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# OpenAI Client
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialisiere Flask
app = Flask(__name__)

# Erhöhe den Verbindungs-Pool für die Telegram API
request = HTTPXRequest(con_pool_size=20)
bot = Bot(token=TOKEN, request=request)

# Initialisiere Telegram-Application
app_telegram = Application.builder().token(TOKEN).build()

# Logging aktivieren
logging.basicConfig(level=logging.INFO)


def generate_response(message):
    """Generiert eine Antwort mit OpenAI GPT-4o."""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein hilfreicher Telegram-Bot."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()


async def start(update: Update, context):
    """Start-Handler für den Bot."""
    await update.message.reply_text("Hallo! Ich bin dein Bot. Wie kann ich helfen?")


async def handle_message(update: Update, context):
    """Antwortet auf Nachrichten mit GPT-4o."""
    user_message = update.message.text
    chat_id = update.message.chat_id
    response = generate_response(user_message)
    await bot.send_message(chat_id=chat_id, text=response)


@app.route('/webhook', methods=['POST'])
async def webhook():
    """Empfängt Telegram-Updates via Webhook."""
    data = await request.get_json()
    update = Update.de_json(data, bot)
    await app_telegram.process_update(update)
    return "OK", 200


async def set_webhook():
    """Setzt den Webhook für den Bot."""
    await bot.set_webhook(url=WEBHOOK_URL)


if __name__ == '__main__':
    # Registriere die Telegram-Handler
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Starte Flask mit asyncio
    asyncio.run(set_webhook())
    app.run(debug=True, port=5000)

