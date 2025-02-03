import telegram
from telegram.ext import Application, MessageHandler, filters
import openai
import os

# Ersetzen Sie diese mit Ihren tatsächlichen API-Schlüsseln
TELEGRAM_BOT_TOKEN = "7711689040:AAGjCqdOQKPj-hJbqWvJKv0n_xGf0Rlfx2Q"
api_key = "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"
client = openai.OpenAI(api_key=api_key)

# Telegram Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Webhook-URL (ersetze 'your-app-name.onrender.com' mit deiner Render-Domain)
WEBHOOK_URL = "https://api.render.com/deploy/srv-cug9s58gph6c73d0987g?key=jZ8WAQ8q9KQ"

# Funktion zum Generieren von Antworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=api_key)
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

# Handler hinzufügen
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# Port setzen
PORT = int(os.environ.get("PORT", 8443))

# Webhook starten
application.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_url=WEBHOOK_URL
)
