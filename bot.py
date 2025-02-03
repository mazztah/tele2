import os
import logging
import asyncio
from flask import Flask, request
from telegram import Bot
from telegram.ext import CommandHandler, MessageHandler, Filters, Updater
from telegram.ext import Dispatcher
from dotenv import load_dotenv
import openai
from telegram.utils.request import HTTPXRequest

# Lade Umgebungsvariablen
load_dotenv()

# Setze die OpenAI API-Schlüssel und Telegram-Bot-Token
openai.api_key = os.getenv("OPENAI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_API_KEY")

# Flask-Setup
app = Flask(__name__)

# Telegram-Setup
request = HTTPXRequest(con_pool_size=20)
bot = Bot(TELEGRAM_TOKEN, request=request)
updater = Updater(TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher

# Logger-Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Funktion zur Generierung der Antwort von OpenAI
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
    return response.choices[0].message['content'].strip()

# Command-Handler für /start
def start(update, context):
    update.message.reply_text("Hallo! Wie kann ich dir helfen?")

# Nachricht-Handler für Textnachrichten
def handle_message(update, context):
    user_message = update.message.text
    response = generate_response(user_message)
    update.message.reply_text(response)

# Setze den Webhook für Telegram
async def set_webhook():
    webhook_url = os.getenv("WEBHOOK_URL")  # Setze die URL für den Webhook
    await bot.set_webhook(webhook_url)

# Flask-Endpunkt für Webhook
@app.route('/webhook', methods=['POST'])
async def webhook():
    if request.method == "POST":
        json_str = request.get_data().decode("UTF-8")
        update = updater.bot.parse_update(json_str)
        dispatcher.process_update(update)
        return 'OK', 200
    return 'Invalid Method', 405

# Flask-Server starten
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Falls keine Umgebungsvariable gesetzt ist, wird Port 5000 verwendet
    # Registriere die Telegram-Handler
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    # Starte Flask mit asyncio und dynamischem Port
    asyncio.run(set_webhook())
    app.run(debug=True, host="0.0.0.0", port=port)
