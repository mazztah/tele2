import os
import logging
import openai
import telegram
from telegram.ext import Application, MessageHandler, filters, CommandHandler

# 🔹 Umgebungsvariablen für API-Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🔹 Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔹 OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# 🔹 Telegram-Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# 🔹 Funktion zum Generieren von Antworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# 🔹 /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage!")

# 🔹 /help Befehl
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten!")

# 🔹 Nachricht-Handler für alle Texteingaben
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# 🔹 Fehlerbehandlung
async def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")

# 🔹 Handler hinzufügen
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🔹 Polling direkt starten
if __name__ == "__main__":
    application.run_polling()
