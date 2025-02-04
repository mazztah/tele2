import os
import logging
import openai
import telegram
from telegram.ext import Application, MessageHandler, filters
from dotenv import load_dotenv

# Umgebungsvariablen aus der .env-Datei laden
load_dotenv()

# API-Schlüssel aus der Umgebung laden
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram Bot Application initialisieren
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# OpenAI API-Key setzen
openai.api_key = OPENAI_API_KEY

# Funktion zum Generieren von Antworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": "You are an AI assistant for a Telegram bot hosted on ply.onrender.com. Your purpose is to provide informative, concise, and engaging responses while maintaining a friendly and professional tone. Always prioritize clarity and accuracy."
            },
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# Handler für eingehende Nachrichten (asynchron)
async def handle_message(update, context):
    message = update.message.text
    logger.info("Received message: %s", message)
    response = generate_response(message)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Handler hinzufügen
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Hauptprogramm: Bot im Polling-Modus starten
if __name__ == '__main__':
    # Lösche den aktiven Webhook, um den Polling-Modus zu ermöglichen.
    logger.info("Deleting webhook to enable polling mode...")
    bot.delete_webhook()
    logger.info("Starting bot with polling...")
    application.run_polling()
