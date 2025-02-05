import os
import logging
import openai
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters

# 🔹 Umgebungsvariablen für API-Keys
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🔹 Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔹 Flask App initialisieren
app = Flask(__name__)

# 🔹 OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# 🔹 Telegram-Bot und Dispatcher initialisieren
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

# 🔹 Funktion zum Generieren von Textantworten mit OpenAI GPT-4
def generate_response(message):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Du bist ein KI-Assistent für einen Telegram-Bot. Antworte prägnant und hilfsbereit. Manchmal ironisch und frech und gelangweilt mit Jugendsprache."},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message["content"].strip()

# 🔹 Funktion zum Generieren von Bildern mit OpenAI DALL·E-3
def generate_image(prompt):
    response = client.images.generate(
        prompt=prompt,
        n=1,
        size="1024x1024",
    )
    return response['data'][0]['url']

# 🔹 /start Befehl
def start(update, context):
    update.message.reply_text("Hallo! Ich bin dein KI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

# 🔹 /help Befehl
def help_command(update, context):
    update.message.reply_text("Sende mir eine Nachricht, und ich werde mit KI antworten! Falls du ein Bild generieren willst, schreib: 'Erstelle ein Bild von...'")

# 🔹 Nachricht-Handler für alle Texteingaben
def handle_message(update, context):
    message = update.message.text

    # Prüfen, ob der Benutzer ein Bild generieren möchte
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        prompt = prompt.replace("generate an image of", "").strip()

        image_url = generate_image(prompt)
        update.message.reply_photo(photo=image_url)
    else:
        response = generate_response(message)
        update.message.reply_text(response)

# 🔹 Fehlerbehandlung
def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")

# 🔹 Handler hinzufügen
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("help", help_command))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_error_handler(error_handler)

# 🔹 Flask-Route für den Webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return 'OK', 200

# 🔹 Webhook bei Telegram registrieren
WEBHOOK_URL = 'https://yourdomain.com/webhook'  # Ersetzen Sie dies durch Ihre tatsächliche URL
bot.set_webhook(url=WEBHOOK_URL)

# 🔹 Flask-Server starten
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
