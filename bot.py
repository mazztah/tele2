import os
import logging
import asyncio
import threading
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Umgebungsvariablen abrufen
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # z.B. "https://deinedomain.de/webhook"

# Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask App initialisieren
app = Flask(__name__)

# OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# Telegram-Bot und Application initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Beispiel-Funktionen
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech."},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()

# /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

# Nachricht-Handler
async def handle_message(update, context):
    message = update.message.text
    response = generate_response(message)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Handler registrieren
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ───────────────────────────────────────────────────────────────
# Globalen Event Loop in einem separaten Thread starten
global_loop = asyncio.new_event_loop()

def start_loop(loop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop_thread = threading.Thread(target=start_loop, args=(global_loop,), daemon=True)
loop_thread.start()
# ───────────────────────────────────────────────────────────────

# Webhook-Route: Telegram sendet hier Updates
@app.route('/webhook', methods=['POST'])
def webhook():
    update_json = request.get_json(force=True)
    logger.info(f"Webhook erhalten: {update_json}")
    update = telegram.Update.de_json(update_json, bot)
    # Den asynchronen Task im globalen Loop einplanen:
    asyncio.run_coroutine_threadsafe(application.process_update(update), global_loop)
    return "OK", 200

@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == '__main__':
    async def startup():
        # Webhook setzen
        await bot.delete_webhook()
        success = await bot.set_webhook(WEBHOOK_URL)
        if success:
            logger.info(f"Webhook erfolgreich gesetzt: {WEBHOOK_URL}")
        else:
            logger.error("Webhook konnte nicht gesetzt werden!")
        # **Wichtig: Application initialisieren und starten!**
        await application.initialize()
        await application.start()

    # Startup-Aufgaben im globalen Loop ausführen
    asyncio.run(startup())
    
    # Flask-Server starten
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
