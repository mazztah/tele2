import os
import logging
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.llms import OpenAI
from dotenv import load_dotenv
import asyncio

# Umgebungsvariablen aus der .env laden
load_dotenv()

# Konfiguration aus Umgebungsvariablen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 5000))

# Logging konfigurieren
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Langchain Setup ---
# Definiere ein Prompt-Template und initialisiere den LLMChain
template = "The user has asked: {question}. Generate a detailed response."
prompt = PromptTemplate(input_variables=["question"], template=template)
llm = OpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)
chain = LLMChain(llm=llm, prompt=prompt)

# --- Flask-Webanwendung ---
app = Flask(__name__)

# --- Telegram Bot Setup ---
# Initialisiere die Telegram Application
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# --- Handler-Definitionen ---
async def start(update: Update, context):
    user = update.effective_user
    await update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\! I\'m a bot powered by OpenAI\. Ask me anything\.'
    )

async def help_command(update: Update, context):
    await update.message.reply_text("Ask me any question, and I'll try to answer using AI!")

async def handle_message(update: Update, context):
    user_message = update.message.text
    try:
        # Generiere eine Antwort über Langchain
        response = chain.run(question=user_message)
        await update.message.reply_text(response)
    except Exception as e:
        await update.message.reply_text("Sorry, I couldn't process your request at the moment.")
        logger.error(f"Error: {e}")

# Registriere Telegram-Handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# --- Webhook-Route in Flask ---
@app.route("/webhook", methods=["POST"])
def webhook():
    # Lese die eingehenden JSON-Daten (Telegram-Update)
    data = request.get_json(force=True)
    logger.info(f"Received update: {data}")
    update = Update.de_json(data, application.bot)
    # Verarbeite das Update (dies ruft die registrierten Telegram-Handler auf)
    application.process_update(update)
    return "OK", 200

# --- Webhook setzen ---
async def set_webhook():
    webhook_endpoint = f"{WEBHOOK_URL}/webhook"
    await application.bot.set_webhook(url=webhook_endpoint)
    logger.info(f"Webhook set to: {webhook_endpoint}")

# --- Hauptprogramm ---
if __name__ == "__main__":
    # Setze den Webhook (asynchron)
    asyncio.run(set_webhook())
    # Starte den Flask-Webserver; Render verwendet den PORT aus den Umgebungsvariablen
    app.run(host="0.0.0.0", port=PORT)


