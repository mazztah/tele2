import os
import telegram
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from flask import Flask, request
import openai
from werkzeug.serving import run_simple

TELEGRAM_BOT_TOKEN = "7711689040:AAGjCqdOQKPj-hJbqWvJKv0n_xGf0Rlfx2Q"
api_key = "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"
client = openai.OpenAI(api_key=api_key)

# Flask Server einrichten
app = Flask(__name__)

# Telegram Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Funktion zum Generieren von Antworten mit OpenAI GPT-4
def generate_response(message):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Du bist ein hilfreicher Telegram-Bot."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message['content'].strip()

# Webhook Handler
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(), bot)
    
    # Textnachricht des Nutzers holen
    message = update.message.text
    # Antwort generieren
    response = generate_response(message)
    
    # Antwort an den Nutzer senden
    update.message.reply_text(response)
    
    return 'OK'

# Webhook setzen
def set_webhook():
    webhook_url = f"https://api.render.com/deploy/srv-cug9s58gph6c73d0987g?key=jZ8WAQ8q9KQ"
    bot.set_webhook(url=webhook_url)

# Flask-App starten
def start_flask_app():
    port = int(os.getenv("PORT", 5000))  # Dynamischer Port für Render
    run_simple('0.0.0.0', port, app)

# Setze den Webhook und starte den Flask Server
if __name__ == '__main__':
    set_webhook()  # Setzt den Webhook für Telegram
    start_flask_app()  # Startet den Flask Server
