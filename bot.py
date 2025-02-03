import telegram
from telegram.ext import Application, MessageHandler, filters
import openai

# Deine API-Schlüssel (ersetze mit deinen echten Token)
TELEGRAM_BOT_TOKEN = "7711689040:AAGjCqdOQKPj-hJbqWvJKv0n_xGf0Rlfx2Q"
api_key = "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"
client = openai.OpenAI(api_key=api_key)

# Telegram Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# 🔧 Webhook löschen, um Konflikte zu vermeiden
async def delete_old_webhook():
    await bot.delete_webhook(drop_pending_updates=True)

# Funktion zum Generieren von Antworten mit OpenAI GPT-4o
def generate_response(message):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot hosted on Render. Always prioritize clarity and accuracy."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

# Handler für eingehende Nachrichten
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await update.message.reply_text(response)

# Handler zum Bot hinzufügen
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    # Löscht alten Webhook, bevor Polling startet
    application.run_coroutine(delete_old_webhook())
    
    # Starte den Bot im Polling-Modus
    application.run_polling(drop_pending_updates=True)
