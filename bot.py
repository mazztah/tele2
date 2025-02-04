import os
import openai
import telegram
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, request
from dotenv import load_dotenv

# Umgebungsvariablen laden
load_dotenv()

# API-Schlüssel aus der Umgebung laden
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Die öffentliche Render-URL

# Flask-App starten
app = Flask(__name__)

# Telegram-Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# Funktion zum Generieren von Antworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot hosted on ply.onrender.com. Your purpose is to provide informative, concise, and engaging responses while maintaining a friendly and professional tone. Always prioritize clarity and accuracy."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# Handler für eingehende Nachrichten
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Flask-Endpunkt für den Telegram-Webhook
@app.route('/webhook', methods=['POST'])
async def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    await application.update_queue.put(update)
    return "OK", 200

# Webhook setzen
async def set_webhook():
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

# Flask starten
if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.run_until_complete(set_webhook())  # Webhook setzen
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # Nachrichten-Handler
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))  # Server starten

