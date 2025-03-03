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

# OpenAI-Funktion zur Generierung von Textantworten (GPT-4)
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

# OpenAI-Funktion zur Sprachgenerierung (Text-zu-Sprache)
def generate_audio_response(text: str) -> bytes:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.audio.speech.create(
        model="gpt-4o",
        voice="alloy",
        input=text
    )
    return response.content

# OpenAI-Funktion zur Sprachanalyse (Transkription via Whisper)
def transcribe_audio(audio_path: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with open(audio_path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
    return transcription.text

# OpenAI-Funktion zur Bildanalyse via Vision API (ursprünglich funktionierend)
def analyze_image(image_path: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    with open(image_path, "rb") as image_file:
        base64_image = base64.b64encode(image_file.read()).decode("utf-8")
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": [
                {"type": "text", "text": "Was ist auf diesem Bild zu sehen?"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}},
            ]},
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content

# OpenAI-Funktion zur Bilderstellung (DALL·E‑3)
def generate_image(prompt: str) -> str:
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    return response.data[0].url

# Handler für den /start-Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-gestützter Telegram-Bot. Sende mir eine Nachricht, ein Bild oder eine Sprachnachricht, und ich werde antworten!")

# Handler für Textnachrichten
async def handle_message(update, context):
    chat_id = str(update.effective_chat.id)
    message = update.message.text
    # Prüfen, ob eine Bildgenerierung angefragt wird
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.lower().replace("erstelle ein bild von", "").replace("generate an image of", "").strip()
        image_url = generate_image(prompt)
        get_chat_history(chat_id).append({"role": "user", "content": f"[Bildgenerierung] {prompt}"})
        get_chat_history(chat_id).append({"role": "assistant", "content": f"[Bild] {image_url}"})
        await context.bot.send_photo(chat_id=chat_id, photo=image_url)
    else:
        reply = generate_response(chat_id, message)
        await context.bot.send_message(chat_id=chat_id, text=reply)

# Handler für empfangene Fotos (Bildanalyse)
async def handle_photo(update, context):
    chat_id = str(update.effective_chat.id)
    photo = update.message.photo[-1]
    file = await bot.get_file(photo.file_id)
    image_path = f"temp_{photo.file_id}.jpg"
    await file.download_to_drive(image_path)
    
    description = analyze_image(image_path)
    os.remove(image_path)
    
    await context.bot.send_message(chat_id=chat_id, text=f"Bildanalyse: {description}")

# Handler für den /generate-Befehl (Bilderstellung)
async def handle_generate_image(update, context):
    chat_id = str(update.effective_chat.id)
    prompt = update.message.text.replace("/generate", "").strip()
    if not prompt:
        await context.bot.send_message(chat_id=chat_id, text="Bitte gib eine Bildbeschreibung an!")
        return
    image_url = generate_image(prompt)
    await context.bot.send_photo(chat_id=chat_id, photo=image_url)

# Handler für Sprachnachrichten (Voice-Input)
async def handle_voice(update, context):
    chat_id = str(update.effective_chat.id)
    voice = update.message.voice
    file = await bot.get_file(voice.file_id)
    audio_path = f"temp_{voice.file_id}.ogg"
    await file.download_to_drive(audio_path)
    
    text = transcribe_audio(audio_path)
    os.remove(audio_path)
    
    # Wenn im transkribierten Text "text" erwähnt wird, antworte als Text,
    # ansonsten als Sprachnachricht.
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

# Globaler Event Loop in einem separaten Thread
global_loop = asyncio.new_event_loop()
def start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
loop_thread = threading.Thread(target=start_loop, args=(global_loop,), daemon=True)
loop_thread.start()

# Handler registrieren
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(MessageHandler(filters.VOICE, handle_voice))
application.add_handler(CommandHandler("generate", handle_generate_image))

# Webhook-Route: Hier empfängt der Bot Updates von Telegram
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
