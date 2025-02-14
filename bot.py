import os
import logging
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler

# 🔹 Umgebungsvariablen abrufen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Setze deine Webhook-URL

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

# 🔹 Funktion zum Generieren von Textantworten mit OpenAI GPT-4o
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

# 🔹 /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

# 🔹 /help Befehl
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten! Falls du ein Bild generieren willst, schreib: 'Erstelle ein Bild von...'")

# 🔹 Nachricht-Handler für alle Texteingaben
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# 🔹 Fehlerbehandlung
async def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")

# 🔹 Webhook-Handler für Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    """Telegram sendet Updates an diesen Endpoint"""
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)
    return "OK", 200

# 🔹 Flask-Route für den Webserver
@app.route('/')
def home():
    return "Bot ist aktiv!", 200

async def main():
    """Initialisiert und startet die Telegram-App mit Webhook"""
    # Handler registrieren
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Webhook für Telegram-Bot setzen
    await bot.set_webhook(url=WEBHOOK_URL)

    logger.info("Bot ist bereit mit Webhook!")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()  # Optional für Debugging

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    
    # Flask starten
    app.run(host="0.0.0.0", port=5000)

