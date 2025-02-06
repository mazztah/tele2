import os
import logging
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler
import time
from threading import Thread
import asyncio

#  Environment Variables for API Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

#  Logging Setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

#  Flask App Initialization
app = Flask(__name__)

#  OpenAI Client Initialization
openai.api_key = OPENAI_API_KEY

#  Telegram Bot Initialization
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

#  OpenAI GPT-4 Response Generation Function
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech und gelangweilt mit jugendsprache"},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()

#  OpenAI DALL·E-3 Image Generation Function
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

#  /start Command
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

#  /help Command
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten! Falls du ein Bild generieren willst, schreib: 'Erstelle ein Bild von...'")

#  Message Handler for Text Inputs
async def handle_message(update, context):
    message = update.message.text

    # Check if the user wants to generate an image
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        prompt = prompt.replace("generate an image of", "").strip()

        image_url = generate_image(prompt)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
    else:
        response = generate_response(message)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

#  Error Handling
async def error_handler(update, context):
    logger.error(f"Error: {context.error}")

#  Flask Route for Webhook
@app.route('/', methods=['POST'])
async def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    await application.process_update(update)
    return 'ok'

#  Handlers Adding
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

#  Port Setting for Flask
PORT = int(os.environ.get("PORT", 5000))

#  Main Program: Flask and Webhook Setup
if __name__ == "__main__":
    # Start the Flask server in a separate thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()

    # Set up the webhook
    bot.set_webhook(f"https://tele2-pnhl.onrender.com/{TELEGRAM_BOT_TOKEN}") # Replace with your webhook URL

    # Keep the main thread alive (you might need a more robust solution for production)
    while True:
        time.sleep(10)
