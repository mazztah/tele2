import asyncio
import os
import logging
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
import time
from threading import Thread

#  Umgebungsvariablen für API-Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#  Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

#  Flask App initialisieren
app = Flask(__name__)

#  OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

#  Telegram-Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

#  Funktion zum Generieren von Textantworten mit OpenAI GPT-4
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech und gelangweilt mit jugendsprache"},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()

#  Funktion zum Generieren von Bildern mit OpenAI DALL·E-3
def generate_image(prompt):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    return response.data[0].url

#  /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

#  /help Befehl
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten! Falls du ein Bild generieren willst, schreib: 'Erstelle ein Bild von...'")

#  Nachricht-Handler für alle Texteingaben
async def handle_message(update, context):
    message = update.message.text

    # Prüfen, ob der Benutzer ein Bild generieren möchte
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        prompt = prompt.replace("generate an image of", "").strip()

        image_url = generate_image(prompt)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
    else:
        response = generate_response(message)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

#  Fehlerbehandlung
async def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")

#  Flask-Route für den Webhook
@app.route('/', methods=['GET', 'POST'])
async def webhook():
    if request.method == 'POST':
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        await application.process_update(update)
        return 'ok'
    else:
        return "Bot is running!"

#  Handler hinzufügen
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

#  Port für Flask setzen
PORT = int(os.environ.get("PORT", 5000))

#  Hauptprogramm: Flask und Webhook Setup
if __name__ == "__main__":
    # Starte den Flask-Server in einem separaten Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()

    async def set_webhook_async():
        await bot.set_webhook(f"https://tele2-pnhl.onrender.com/7711689040:AAHmXeuKFF3dBMtOJS2Wj1BOfOvqbf7EBzw")

    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook_async())

    # Keep the main thread alive (you might need a more robust solution for production)
    while True:
        time.sleep(10)
