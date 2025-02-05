import os
import logging
import asyncio

import openai
import telegram

from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler

# Umgebungsvariablen für API-Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging einrichten
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App initialisieren
app = Flask(__name__)

# OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# Funktionen zum Generieren von Text- und Bildantworten mit OpenAI
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # or gpt-3.5-turbo if you prefer
            messages=[
                {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully."},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except openai.error.OpenAIError as e:  # Catch OpenAI specific errors
        logger.error(f"OpenAI API Error: {e}")
        return "There was an error processing your request with OpenAI."  # User-friendly message
    except Exception as e:  # Catch other potential errors
        logger.error(f"An unexpected error occurred: {e}")
        return "An unexpected error occurred."

def generate_image(prompt):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )
        return response.data[0].url
    except openai.error.OpenAIError as e:
        logger.error(f"OpenAI API Error: {e}")
        return "There was an error generating the image with OpenAI."
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        return "An unexpected error occurred."


# Telegram Bot Handler
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot.")

async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, oder nutze /start und /help.")

async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        image_url = generate_image(prompt)
        await update.message.reply_photo(photo=image_url)
    else:
        response = generate_response(message)  # No need for try/except here, it's handled in the function
        await update.message.reply_text(response)


async def error_handler(update, context):
    logger.error(f"Update {update} verursacht Fehler {context.error}")
    try:
        await update.message.reply_text("An error occurred. Please try again later.") # Notify the user
    except AttributeError as e: # Handle cases where update.message might be None
        logger.error(f"Error sending error message to user: {e}")


# Flask-Route für Webhooks
@app.route('/' + TELEGRAM_BOT_TOKEN, methods=['POST'])
async def webhook(request):
    if request.content_type == "application/json":
        update = telegram.Update.de_json(request.get_json(force=True), application.bot) # Use application.bot
        await application.process_update(update)
        return 'ok'
    return 'ok' # Important: Return 'ok' even if not JSON, to avoid Telegram retries


async def main():
    global application  # Make application global so webhook can access it
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    bot = application.bot  # Holen Sie sich die Bot-Instanz
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME')}/{TELEGRAM_BOT_TOKEN}" # Use Render's env variable
    await bot.set_webhook(webhook_url)  # Richten Sie den Webhook ein

    # Flask-App starten
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    asyncio.run(main())
