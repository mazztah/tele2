import os
import logging
import asyncio
import threading
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

# Umgebungsvariablen (z. B. via .env-Datei setzen)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # z.B. "https://deinedomain.de/webhook"

# Logging konfigurieren
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask-App initialisieren
app = Flask(__name__)

# OpenAI konfigurieren
openai.api_key = OPENAI_API_KEY

# Benutzerdefinierten Request-Adapter erstellen (ohne pool_size, da dieser Parameter nicht unterstützt wird)
request_instance = HTTPXRequest(pool_timeout=20)

# Bot und Application initialisieren (verwende den benutzerdefinierten Request)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request_instance)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Funktion zur Generierung von Textantworten via OpenAI (GPT-4)
def generate_response(message: str) -> str:
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

# Funktion zur Generierung von Bildern via OpenAI (DALL·E‑3)
def generate_image(prompt: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="hd",
        n=1,
    )
    return response.data[0].url

# /start-Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage, schicke mir eine Bildbeschreibung oder fordere 'Erstelle ein Bild von ...' an.")

# Nachricht-Handler: Prüft, ob ein Bild generiert werden soll
async def handle_message(update, context):
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        # Bildgenerierung: entferne den Befehlsteil und trimme den Prompt
        prompt = message.lower().replace("erstelle ein bild von", "").replace("generate an image of", "").strip()
        image_url = generate_image(prompt)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
    else:
        response = generate_response(message)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# Handler registrieren
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# ─────────────────────────────
# Globalen Event Loop in separatem Thread starten
global_loop = asyncio.new_event_loop()

def start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

loop_thread = threading.Thread(target=start_loop, args=(global_loop,), daemon=True)
loop_thread.start()
# ─────────────────────────────

# Webhook-Route: Telegram sendet hier Updates
@app.route('/webhook', methods=['POST'])
def webhook():
    update_json = request.get_json(force=True)
    logger.info(f"Webhook erhalten: {update_json}")
    update = telegram.Update.de_json(update_json, bot)
    # Update asynchron im globalen Loop verarbeiten
    asyncio.run_coroutine_threadsafe(application.process_update(update), global_loop)
    return "OK", 200

# Eine einfache Home-Route
@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == '__main__':
    async def startup():
        # Initialisiere Bot und Application, damit z.B. bot.username verfügbar ist
        await bot.initialize()
        await application.initialize()
        # Webhook löschen und neu setzen
        await bot.delete_webhook()
        success = await bot.set_webhook(WEBHOOK_URL)
        if success:
            logger.info(f"Webhook erfolgreich gesetzt: {WEBHOOK_URL}")
        else:
            logger.error("Webhook konnte nicht gesetzt werden!")
        await application.start()

    # Führe Startup im globalen Loop aus (statt asyncio.run, damit dieser nicht geschlossen wird)
    startup_future = asyncio.run_coroutine_threadsafe(startup(), global_loop)
    startup_future.result()  # Warten, bis Startup abgeschlossen ist

    # Starte den Flask-Server (dies blockt den Main Thread)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)

