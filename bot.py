import os
import logging
import asyncio
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Umgebungsvariablen abrufen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # z. B. "https://deinedomain.de/webhook"

# Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask App initialisieren
app = Flask(__name__)

# OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# Telegram-Bot und Application initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Funktionen für OpenAI-Antworten
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech."},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()

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

# /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

# /help Befehl
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich antworte mit AI. Für ein Bild: 'Erstelle ein Bild von...'")

# Nachricht-Handler
async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        prompt = prompt.replace("generate an image of", "").strip()
        image_url = generate_image(prompt)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
    else:
        response = generate_response(message)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Fehlerbehandlung
async def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")

# Handler registrieren
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)

# Webhook-Route: Telegram sendet hier Updates
@app.route('/webhook', methods=['POST'])
def webhook():
    update_json = request.get_json(force=True)
    logger.info(f"Webhook erhalten: {update_json}")
    update = telegram.Update.de_json(update_json, bot)
    # Asynchronen Task starten, um die Update-Verarbeitung nicht blockierend zu gestalten
    asyncio.create_task(application.process_update(update))
    # Mit HTTP-200 antworten, damit Telegram weiß, dass der Update empfangen wurde
    return "OK", 200

# Einfache Home-Route
@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == '__main__':
    # Webhook beim Start löschen und neu setzen
    async def set_webhook():
        await bot.delete_webhook()
        success = await bot.set_webhook(WEBHOOK_URL)
        if success:
            logger.info(f"Webhook erfolgreich gesetzt: {WEBHOOK_URL}")
        else:
            logger.error("Webhook konnte nicht gesetzt werden!")
    
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())
    
    # Flask-Server starten (dieser bleibt aktiv und reagiert auf eingehende Nachrichten)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
