import asyncio
import os
import logging
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
import time
from threading import Thread

# Umgebungsvariablen für API-Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask App initialisieren
app = Flask(__name__)

# Bot und Application *sofort* initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Funktion zum Generieren von Textantworten mit OpenAI GPT-4
def generate_response(message):
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-0613",  # or gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech und gelangweilt mit jugendsprache"},
                {"role": "user", "content": message},
            ],
            max_tokens=1500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Fehler bei OpenAI-Anfrage: {e}")
        return "Es gab ein Problem mit der OpenAI-API."  # Rückmeldung an den Benutzer

# Funktion zum Generieren von Bildern mit OpenAI DALL·E-3
def generate_image(prompt):
    try:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        logger.error(f"Fehler bei DALL·E-Anfrage: {e}")
        return None  # Keine Bild-URL zurückgeben

# /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

# /help Befehl
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten! Falls du ein Bild generieren willst, schreib: 'Erstelle ein Bild von...'")

# Nachricht-Handler für alle Texteingaben
async def handle_message(update, context):
    message = update.message.text

    # Prüfen, ob der Benutzer ein Bild generieren möchte
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        prompt = prompt.replace("generate an image of", "").strip()

        image_url = generate_image(prompt)
        if image_url:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Es gab ein Problem bei der Bildgenerierung.")
    else:
        response = generate_response(message)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Fehlerbehandlung
async def error_handler(update, context):
    logger.error(f"Update {update} verursachte folgenden Fehler: {context.error}")

# Flask-Route für den Webhook
@app.route('/', methods=['GET', 'POST'])
async def webhook():
    if request.method == 'POST':
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        loop = asyncio.get_running_loop()  # Den *aktuell* laufenden Loop holen
        if loop:
            loop.create_task(application.process_update(update))  # Update-Verarbeitung als Task planen
        else:
            logger.error("Kein laufender Event Loop gefunden.")
        return 'ok'
    else:
        return "Bot is running!"

# Handler hinzufügen (muss nach der Initialisierung erfolgen!)
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)  # Füge den Fehlerhandler hinzu

# Port für Flask setzen
PORT = int(os.environ.get("PORT", 5000))

def run_telegram_bot():
    async def set_webhook_and_initialize():
        await bot.set_webhook("https://tele2-pnhl.onrender.com/")  # Deine Webhook-URL (SICHERSTELLEN, DASS DIES KORREKT IST!)
        await application.initialize()

    async def bot_main():
        await set_webhook_and_initialize()
        await application.run_polling()  # Verwende Polling im Bot-Thread

    loop = asyncio.new_event_loop()  # Neuen Event Loop erstellen
    asyncio.set_event_loop(loop)  # Neuen Loop als Standard setzen

    try:
        loop.run_until_complete(bot_main())  # Initialisiere den Bot
        loop.run_forever()  # Bot am Laufen halten

    except Exception as e:
        logger.exception("Fehler in bot_main:")  # Log die *vollen* Exception-Details

    finally:  # Stelle sicher, dass der Loop geschlossen wird
        application.shutdown()  # Shutdown planen
        loop.run_until_complete(application.shutdown())  # Warte auf den Abschluss des Shutdowns
        loop.close()


if __name__ == "__main__":
    # Starte den Flask-Server in einem separaten Thread
    flask_thread = Thread(target=lambda: app.run(host="0.0.0.0", port=PORT))
    flask_thread.daemon = True  # Erlaubt dem Hauptthread das Beenden
    flask_thread.start()

    # Starte den Telegram-Bot im *Hauptthread*
    telegram_thread = Thread(target=run_telegram_bot)
    telegram_thread.daemon = True  # Erlaubt dem Hauptthread das Beenden
    telegram_thread.start()

    # Halte den Hauptthread am Laufen (oder mache andere Dinge)
    while True:
        time.sleep(10)
