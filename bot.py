import os
import logging
import asyncio
import openai
import telegram
from telegram.ext import Application, MessageHandler, filters, CommandHandler

# Umgebungsvariablen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Logging konfigurieren
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# OpenAI initialisieren
openai.api_key = OPENAI_API_KEY

# Funktionen zur Generierung von Antworten
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",  # Alternativ: "gpt-3.5-turbo"
            messages=[
                {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully."},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Fehler beim Generieren der Antwort: {e}")
        return "Es gab einen Fehler bei der Bearbeitung deiner Anfrage."

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
    except Exception as e:
        logger.error(f"Fehler bei der Bildgenerierung: {e}")
        return None

# Telegram Bot Handler
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten! Falls du ein Bild generieren möchtest, schreib: 'Erstelle ein Bild von...'")

async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").replace("generate an image of", "").strip()
        # Ausführung der blockierenden Funktion in einem Executor
        image_url = await context.application.run_in_executor(None, generate_image, prompt)
        if image_url:
            await update.message.reply_photo(photo=image_url)
        else:
            await update.message.reply_text("Fehler bei der Bildgenerierung.")
    else:
        response = await context.application.run_in_executor(None, generate_response, message)
        await update.message.reply_text(response)

async def error_handler(update, context):
    logger.error(f"Update {update} verursachte Fehler {context.error}")
    try:
        await update.message.reply_text("Ein Fehler ist aufgetreten. Bitte versuche es später noch einmal.")
    except Exception as e:
        logger.error(f"Fehler beim Senden der Fehlermeldung: {e}")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    # run_polling() ist die korrekte Methode (start_polling() gibt es nicht)
    application.run_polling()

if __name__ == "__main__":
    main()
