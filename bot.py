import os
import logging
import asyncio
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from threading import Thread

# Umgebungsvariablen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # z.B. "https://yourdomain.com/webhook"

# Logging konfigurieren
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask-App initialisieren
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot is running!"

# OpenAI initialisieren
openai.api_key = OPENAI_API_KEY

def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully."},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Fehler beim Generieren der Antwort: {e}")
        return "Es gab einen Fehler bei der Bearbeitung deiner Anfrage."

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
    except Exception as e:
        logger.error(f"Fehler bei der Bildgenerierung: {e}")
        return None

# Telegram Bot Handler
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten! Falls du ein Bild generieren möchtest, schreib: 'Erstelle ein Bild von...'")

async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").replace("generate an image of", "").strip()
        image_url = await asyncio.get_running_loop().run_in_executor(None, generate_image, prompt)
        if image_url:
            await update.message.reply_photo(photo=image_url)
        else:
            await update.message.reply_text("Fehler bei der Bildgenerierung.")
    else:
        response = await asyncio.get_running_loop().run_in_executor(None, generate_response, message)
        await update.message.reply_text(response)

async def error_handler(update, context):
    logger.error(f"Update {update} verursachte Fehler {context.error}")
    try:
        await update.message.reply_text("Ein Fehler ist aufgetreten. Bitte versuche es später noch einmal.")
    except Exception as e:
        logger.error(f"Fehler beim Senden der Fehlermeldung: {e}")

# Global initialisiertes Application-Objekt
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)

# Globaler Event Loop, um Updates aus Flask asynchron zu verarbeiten
BOT_LOOP = None

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    logger.info(f"Webhook erhalten: {data}")
    update = telegram.Update.de_json(data, application.bot)
    if BOT_LOOP is not None:
        asyncio.run_coroutine_threadsafe(application.process_update(update), BOT_LOOP)
    else:
        logger.error("BOT_LOOP ist nicht gesetzt!")
    return "OK", 200

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

async def main():
    global BOT_LOOP
    BOT_LOOP = asyncio.get_running_loop()
    try:
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook gesetzt auf {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Fehler beim Setzen des Webhooks: {e}")
    Thread(target=run_flask).start()
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

