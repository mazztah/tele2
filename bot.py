import os
import logging
import asyncio
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
from threading import Thread
import concurrent.futures

# Environment variables and logging (same as before)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 5000))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Thread pool for blocking operations
thread_pool = concurrent.futures.ThreadPoolExecutor()

# OpenAI initialization (same as before)
openai.api_key = OPENAI_API_KEY

async def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = await asyncio.to_thread(client.chat.completions.create,
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully."},
                {"role": "user", "content": message},
            ],
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        return f"An error occurred: {e}. Please try again later or contact support."

async def generate_image(prompt):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    try:
        response = await asyncio.to_thread(client.images.generate,
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="hd",
            n=1,
        )
        return response.data[0].url
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return "Error generating image. Please check the prompt and try again."

# Telegram handlers (same as before)
async def start(update, context):
    await update.message.reply_text("Hello! I'm your AI chatbot. Ask me anything or send me an image description!")

async def help_command(update, context):
    await update.message.reply_text("Send me a message, and I'll respond with AI! If you want to generate an image, type: 'Create an image of...'")

async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("create an image of") or message.lower().startswith("generate an image of"):
        prompt = message.replace("create an image of", "").replace("generate an image of", "").strip()
        image_url = await generate_image(prompt)
        if image_url:
            await update.message.reply_photo(photo=image_url)
        else:
            await update.message.reply_text("Error generating image.")
    else:
        response = await generate_response(message)
        await update.message.reply_text(response)

async def error_handler(update, context):
    logger.error(f"Update {update} caused error {context.error}")
    try:
        await update.message.reply_text("An error occurred. Please try again later.")
    except Exception as e:
        logger.error(f"Error sending error message: {e}")

# Application setup (same as before)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_error_handler(error_handler)

async def process_telegram_update(update):
    await application.process_update(update)

@app.route('/webhook', methods=['POST'])
async def webhook():
    data = request.get_json(force=True)
    update = telegram.Update.de_json(data, application.bot)
    await process_telegram_update(update)
    return "OK", 200

def run_flask(loop):
    asyncio.set_event_loop(loop)
    app.run(host="0.0.0.0", port=PORT)

async def main():
    try:
        await application.bot.set_webhook(WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")
    except Exception as e:
        logger.error(f"Error setting webhook: {e}")
        return

    loop = asyncio.get_running_loop()
    flask_thread = Thread(target=run_flask, args=(loop,))
    flask_thread.start()

    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())

