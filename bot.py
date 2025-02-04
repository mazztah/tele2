import os
import logging
import time
import base64
from threading import Thread

import openai
import telegram
from flask import Flask, request
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    CommandHandler,
)

# 🔹 Umgebungsvariablen für API-Keys und Port
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PORT = int(os.environ.get("PORT", 5000))

# 🔹 Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔹 Flask App initialisieren
app = Flask(__name__)

# 🔹 OpenAI-Client initialisieren
openai.api_key = OPENAI_API_KEY

# 🔹 Telegram-Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()


# ─────────────────────────────
# Funktionen zur Verarbeitung von Nachrichten
# ─────────────────────────────

def generate_response(message):
    """
    Generiert eine Textantwort mithilfe von GPT-4o.
    """
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an AI assistant for a Telegram bot. Answer concisely and helpfully. "
                    "Manchmal ironisch und frech und gelangweilt mit jugendsprache"
                ),
            },
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()


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


def analyze_image(image_bytes):
    """
    Analysiert den Inhalt eines Bildes mithilfe eines Vision-fähigen Modells (hier: gpt-4o-mini).
    Das Bild wird als Base64-kodierter String übergeben.
    """
    # Base64-Kodierung des Bildes
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")

    # Anfrage an OpenAI, bei der das Bild als Input eingebunden wird
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        # Hier verwenden wir den Schlüssel "image_base64" – stelle sicher, dass dein Modell dies unterstützt!
                        "type": "image_base64",
                        "image_base64": encoded_image,
                    },
                ],
            }
        ],
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


# ─────────────────────────────
# Telegram-Handler
# ─────────────────────────────

async def start(update, context):
    await update.message.reply_text(
        "Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage, schick mir eine Bildbeschreibung "
        "oder ein Foto, das ich analysieren soll!"
    )


async def help_command(update, context):
    await update.message.reply_text(
        "Sende mir eine Nachricht und ich antworte mit AI. Für Bilder: "
        "Schicke einen Text wie 'Erstelle ein Bild von ...' oder ein Foto zur Analyse."
    )


async def handle_message(update, context):
    """
    Behandelt normale Textnachrichten. Je nach Inhalt wird entweder eine Bildgenerierung oder
    eine Textgenerierung durchgeführt.
    """
    message = update.message.text

    # Prüfen, ob der Benutzer ein Bild generieren möchte
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        prompt = prompt.replace("generate an image of", "").strip()
        try:
            image_url = generate_image(prompt)
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
        except Exception as e:
            logger.error(f"Fehler bei der Bildgenerierung: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, es gab einen Fehler bei der Bildgenerierung.",
            )
    else:
        try:
            response = generate_response(message)
            await context.bot.send_message(chat_id=update.effective_chat.id, text=response)
        except Exception as e:
            logger.error(f"Fehler bei der Textgenerierung: {e}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, es gab einen Fehler bei der Antwortgenerierung.",
            )


async def handle_photo(update, context):
    """
    Behandelt eingehende Fotos. Das Foto wird heruntergeladen, Base64-kodiert und an die Vision-Funktion
    übergeben.
    """
    try:
        # Wähle das Foto in der höchsten Auflösung aus
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        # Lade das Foto als Bytearray herunter
        image_bytes = await file.download_as_bytearray()
        answer = analyze_image(image_bytes)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=answer)
    except Exception as e:
        logger.error(f"Fehler bei der Bildanalyse: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, es gab einen Fehler bei der Bildanalyse.",
        )


async def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")


# ─────────────────────────────
# Flask-Webserver (z. B. für Health-Checks)
# ─────────────────────────────

@app.route('/')
def home():
    return "Bot is running!", 200


# ─────────────────────────────
# Handler registrieren
# ─────────────────────────────

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
# Textnachrichten
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
# Fotos (für Vision)
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_error_handler(error_handler)


# ─────────────────────────────
# Hauptprogramm: Starten von Flask und Polling in einer Endlosschleife
# ─────────────────────────────

if __name__ == "__main__":
    # Starte den Flask-Server in einem separaten Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()

    # Endlosschleife für den Polling-Prozess
    while True:
        try:
            logger.info("Starte Polling...")
            application.run_polling()
        except Exception as e:
            logger.error(f"Fehler beim Polling: {e}")
            # 5 Sekunden warten, bevor neu gestartet wird
            time.sleep(5)
