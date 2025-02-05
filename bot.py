import os
import logging
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
import asyncio
from threading import Thread

# Globaler Event Loop für den Bot
BOT_LOOP = None

# Umgebungsvariablen für API-Keys und Konfiguration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # z. B. "https://deinedomain.de/webhook"

# Logging konfigurieren
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask-App initialisieren
app = Flask(__name__)

# OpenAI API-Key setzen
openai.api_key = OPENAI_API_KEY

# Globaler Client, der in generate_response und generate_image verwendet wird
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Telegram Bot Application initialisieren
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Funktion: Generiere Textantworten via OpenAI GPT-4o
def generate_response(message):
    response = client.chat.completions.create(
        model="gpt-4o",  # passe den Modellnamen ggf. an
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech und gelangweilt mit jugendsprache"},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()

# Funktion: Generiere Bild via OpenAI DALL·E-3
def generate_image(prompt):
    response = client.images.generate(
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    return response['data'][0]['url']

# /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

# /help Befehl
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich antworte mit AI! Falls du ein Bild generieren möchtest, beginne deine Nachricht mit 'Erstelle ein Bild von...'")

# Nachricht-Handler
async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = (message.lower()
                  .replace("erstelle ein bild von", "")
                  .replace("generate an image of", "")
                  .strip())
        try:
            image_url = generate_image(prompt)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
        except Exception as e:
            logger.error("Fehler bei der Bildgenerierung: %s", e)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Es gab einen Fehler beim Erstellen des Bildes.")
    else:
        try:
            response = generate_response(message)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except Exception as e:
            logger.error("Fehler bei der Textgenerierung: %s", e)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Es gab einen Fehler bei der Antwortgenerierung.")

# Fehlerbehandlung
async def error_handler(update, context):
    logger.error("Fehler: %s", context.error)

# Flask-Routen
@app.route('/')
def home():
    return "Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    logger.info("Webhook-Aufruf erhalten: %s", data)
    update = telegram.Update.de_json(data, application.bot)
    if BOT_LOOP is not None:
        asyncio.run_coroutine_threadsafe(application.process_update(update), BOT_LOOP)
    else:
        logger.error("BOT_LOOP ist nicht gesetzt!")
    return "OK", 200

# Funktion zum Starten von Flask in einem separaten Thread
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def main():
    global BOT_LOOP
    BOT_LOOP = asyncio.get_running_loop()

    # Handler hinzufügen
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    # Webhook bei Telegram registrieren
    if not WEBHOOK_URL:
        logger.error("WEBHOOK_URL Umgebungsvariable ist nicht gesetzt!")
        return
    await application.bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook gesetzt auf: %s", WEBHOOK_URL)
    
    # Starte den Flask-Server in einem separaten Thread
    flask_thread = Thread(target=run_flask)
    flask_thread.start()
    
    # Bot am Laufen halten
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
