import os
import logging
import asyncio
import threading
import openai
import telegram
import base64
from flask import Flask, request
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest

# Umgebungsvariablen (z. B. via .env-Datei setzen)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # z.B. "https://deinedomain.de/webhook"

# Logging konfigurieren
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask-App initialisieren
app = Flask(__name__)
openai.api_key = OPENAI_API_KEY

# Telegram Bot und Application initialisieren (mit benutzerdefiniertem Request)
request_instance = HTTPXRequest(pool_timeout=20)
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN, request=request_instance)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# Globaler Chatverlauf pro Chat (Speicherung als Liste von Nachrichten)
chat_histories = {}

def get_chat_history(chat_id: str):
    if chat_id not in chat_histories:
        chat_histories[chat_id] = [{
            "role": "system",
            "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech."
        }]
    return chat_histories[chat_id]

# OpenAI-Funktion zur Generierung von Textantworten
def generate_response(chat_id: str, message: str) -> str:
    history = get_chat_history(chat_id)
    history.append({"role": "user", "content": message})
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=history,
        max_tokens=1500,
    )
    reply = response.choices[0].message.content.strip()
    history.append({"role": "assistant", "content": reply})
    return reply

# OpenAI-Funktion zur Sprachgenerierung
def generate_audio_response(text: str) -> bytes:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.audio.speech.create(
        model="gpt-4o",
        voice="alloy",
        input=text
    )
    return response.content

# OpenAI-Funktion zur Sprachanalyse
def transcribe_audio(audio_path: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with open(audio_path, "rb") as audio_file:
        audio_data = audio_file.read()
    response = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_data,
        response_format="text"
    )
    return response.text

# OpenAI-Funktion zur Bildanalyse
def analyze_image(image_path: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
    response = client.images.analyze(
        model="gpt-4o-vision",
        image=image_data
    )
    return response.text

# OpenAI-Funktion zur Bilderstellung
def generate_image(prompt: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.create(
        model="dalle-3",
        prompt=prompt,
        n=1,
        size="1024x1024"
    )
    return response.data[0].url

# Handler für Sprachnachrichten
async def handle_voice(update, context):
    chat_id = str(update.effective_chat.id)
    voice = update.message.voice
    file = await bot.get_file(voice.file_id)
    audio_path = f"temp_{voice.file_id}.ogg"
    await file.download_to_drive(audio_path)
    
    text = transcribe_audio(audio_path)
    os.remove(audio_path)
    
    if "text" in text.lower():
        reply = generate_response(chat_id, text)
        await context.bot.send_message(chat_id=chat_id, text=reply)
    else:
        reply = generate_response(chat_id, text)
        audio_response = generate_audio_response(reply)
        with open("response.ogg", "wb") as audio_file:
            audio_file.write(audio_response)
        await context.bot.send_voice(chat_id=chat_id, voice=open("response.ogg", "rb"))
        os.remove("response.ogg")

# Handler für Bilder
async def handle_photo(update, context):
    chat_id = str(update.effective_chat.id)
    photo = update.message.photo[-1]
    file = await bot.get_file(photo.file_id)
    image_path = f"temp_{photo.file_id}.jpg"
    await file.download_to_drive(image_path)
    
    description = analyze_image(image_path)
    os.remove(image_path)
    
    await context.bot.send_message(chat_id=chat_id, text=f"Bildanalyse: {description}")

# Handler für Bilderstellung
async def handle_generate_image(update, context):
    chat_id = str(update.effective_chat.id)
    prompt = update.message.text.replace("/generate", "").strip()
    if not prompt:
        await context.bot.send_message(chat_id=chat_id, text="Bitte gib eine Bildbeschreibung an!")
        return
    
    image_url = generate_image(prompt)
    await context.bot.send_photo(chat_id=chat_id, photo=image_url)

# Handler registrieren
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(MessageHandler(filters.VOICE, handle_voice))
application.add_handler(CommandHandler("generate", handle_generate_image))

# Webhook-Route
@app.route('/webhook', methods=['POST'])
def webhook():
    update_json = request.get_json(force=True)
    logger.info(f"Webhook erhalten: {update_json}")
    update = telegram.Update.de_json(update_json, bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), global_loop)
    return "OK", 200

# Home-Route
@app.route('/')
def home():
    return "Bot is running!", 200

if __name__ == '__main__':
    async def startup():
        await bot.initialize()
        await application.initialize()
        await bot.delete_webhook()
        success = await bot.set_webhook(WEBHOOK_URL)
        if success:
            logger.info(f"Webhook erfolgreich gesetzt: {WEBHOOK_URL}")
        else:
            logger.error("Webhook konnte nicht gesetzt werden!")
        await application.start()
    startup_future = asyncio.run_coroutine_threadsafe(startup(), global_loop)
    startup_future.result()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
