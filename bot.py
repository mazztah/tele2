import os
import logging
import asyncio

import openai
import telegram

from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from threading import Thread

# Umgebungsvariablen für API-Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging einrichten
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App initialisieren (optional, für Health Checks etc.)
app = Flask(__name__)

# OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# Funktionen zum Generieren von Text- und Bildantworten mit OpenAI
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview", # Oder gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully."},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except openai.error.OpenAIError as e: # OpenAI-spezifische Fehler abfangen
        logger.error(f"OpenAI API Fehler: {e}")
        return "Es gab einen Fehler bei der Bearbeitung deiner Anfrage mit OpenAI." # Benutzerfreundliche Nachricht
    except Exception as e: # Andere potenzielle Fehler abfangen
        logger.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        return "Ein unerwarteter Fehler ist aufgetreten."

def generate_image(prompt):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )
        return response.data[0].url
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API Fehler: {e}")
        return "Es gab einen Fehler bei der Generierung des Bildes mit OpenAI."
    except Exception as e:
        logger.error(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
        return "Ein unerwarteter Fehler ist aufgetreten."

# Telegram Bot Handler
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot.")

async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, oder nutze /start und /help.")

async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        image_url = generate_image(prompt)
        await update.message.reply_photo(photo=image_url)
    else:
        response = generate_response(message) # Kein try/except nötig, da in Funktion behandelt
        await update.message.reply_text(response)

async def error_handler(update, context):
    logger.error(f"Update {update} verursacht Fehler {context.error}")
    try:
        await update.message.reply_text("Ein Fehler ist aufgetreten. Bitte versuche es später noch einmal.") # Benutzer benachrichtigen
    except AttributeError as e: # Fälle behandeln, in denen update.message None sein könnte
        logger.error(f"Fehler beim Senden der Fehlermeldung an den Benutzer: {e}")

# Flask-Route (optional)
@app.route('/')
def home():
    return "Bot is running!"

async def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Long Polling
    await application.initialize()
    await application.start_polling(allowed_updates=telegram.Update.ALL_TYPES)
    await application.idle()

if __name__ == "__main__":
    # Flask in einem separaten Thread starten (optional)
    Thread(target=lambda: app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))).start()

    # Telegram Bot in der Hauptschleife ausführen
    asyncio.run(main())
