from flask import Flask, request
import telegram
import openai
import json
import asyncio  # Hier importieren wir asyncio

# Feste API-Schlüssel (ersetze sie mit deinen echten Werten)
TELEGRAM_BOT_TOKEN = "DEIN_BOT_TOKEN"
OPENAI_API_KEY = "DEIN_OPENAI_API_KEY"

# Initialisierung des Telegram-Bots
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)

# Initialisierung von OpenAI-Client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)

def generate_response(message):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein hilfreicher Telegram-Bot."},
            {"role": "user", "content": message},
        ],
        max_tokens=150,
    )
    return response.choices[0].message.content.strip()

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # JSON-Daten von Telegram abrufen
        update = request.get_json()
        print("Update erhalten:")
        print(json.dumps(update, indent=4))
        
        # Überprüfen, ob es sich um eine Nachricht mit Text handelt
        if "message" in update and "text" in update["message"]:
            chat_id = update["message"]["chat"]["id"]
            message_text = update["message"]["text"]
            
            # Antwort mit OpenAI generieren
            answer = generate_response(message_text)
            
            # Die asynchrone send_message-Methode mit asyncio.run() aufrufen
            asyncio.run(bot.send_message(chat_id=chat_id, text=answer))
        
        # Eine leere Antwort mit HTTP-Status 200 zurückgeben
        return "", 200
    except Exception as e:
        print(f"Fehler bei der Verarbeitung des Webhooks: {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    # Flask-Server starten (hier auf Port 10000)
    app.run(host="0.0.0.0", port=10000, debug=True)

