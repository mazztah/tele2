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
        # Initialisiere mit einer Systemnachricht
        chat_histories[chat_id] = [{
            "role": "system",
            "content": "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. Manchmal ironisch und frech."
        }]
    return chat_histories[chat_id]

# OpenAI-Funktion zur Generierung von Textantworten (GPT-4) unter Einbeziehung des Chatverlaufs
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

# OpenAI-Funktion zur Generierung von Bildern (DALL·E‑3)
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

# OpenAI-Funktion zur Bildanalyse via Vision API
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

# /start-Befehl
async def start(update, context):
    await update.message.reply_text(
        "Hallo! Ich bin dein AI-Chatbot. Sende mir einen Text, ein Bild oder fordere 'Erstelle ein Bild von ...' an."
    )

# Nachrichten-Handler: Prüft, ob ein Bild generiert werden soll oder eine Textnachricht vorliegt
async def handle_message(update, context):
    chat_id = str(update.effective_chat.id)
    message = update.message.text
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        # Bildgenerierung: entferne den Befehlsteil und trimme den Prompt
        prompt = message.lower().replace("erstelle ein bild von", "").replace("generate an image of", "").strip()
        image_url = generate_image(prompt)
        # Füge den Bild-Prompt dem Chatverlauf hinzu
        get_chat_history(chat_id).append({"role": "user", "content": f"[Bildgenerierung] {prompt}"})
        # Optional: Die Antwort des Bildgenerators wird auch im Chatverlauf vermerkt\n        get_chat_history(chat_id).append({"role": "assistant", "content": f"[Bild] {image_url}"})
        await context.bot.send_photo(chat_id=chat_id, photo=image_url)
    else:
        reply = generate_response(chat_id, message)
        await context.bot.send_message(chat_id=chat_id, text=reply)

# Foto-Handler: Analysiert empfangene Bilder und speichert den Verlauf
async def handle_photo(update, context):
    chat_id = str(update.effective_chat.id)
    photo = update.message.photo[-1]  # Wähle das Foto in höchster Auflösung
    file = await bot.get_file(photo.file_id)
    image_path = f"temp_{photo.file_id}.jpg"
    await file.download_to_drive(image_path)
    # Vermerke im Chatverlauf, dass ein Bild geschickt wurde
    get_chat_history(chat_id).append({"role": "user", "content": "[Bild]"}) 
    description = analyze_image(image_path)
    os.remove(image_path)
    get_chat_history(chat_id).append({"role": "assistant", "content": description})
    await context.bot.send_message(chat_id=chat_id, text=description)

# Handler registrieren
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Globalen Event Loop in separatem Thread starten
global_loop = asyncio.new_event_loop()
def start_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()
loop_thread = threading.Thread(target=start_loop, args=(global_loop,), daemon=True)
loop_thread.start()

# Webhook-Route: Telegram sendet hier Updates
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
