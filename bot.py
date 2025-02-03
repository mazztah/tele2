from flask import Flask, request
import telegram
import openai
import os

app = Flask(__name__)

# Telegram Bot und OpenAI API-Schlüssel
TELEGRAM_BOT_TOKEN = "7711689040:AAGjCqdOQKPj-hJbqWvJKv0n_xGf0Rlfx2Q"
api_key = "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"
client = openai.OpenAI(api_key=api_key)

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

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        # Die eingehende Nachricht von Telegram verarbeiten
        update = telegram.Update.de_json(request.get_json(), bot)
        
        # Wenn die Nachricht Text enthält, verarbeite die Nachricht
        if update.message and update.message.text:
            chat_id = update.message.chat.id
            message = update.message.text
            
            # Generiere die Antwort über OpenAI
            response = generate_response(message)
            
            # Sende die Antwort zurück an den Telegram-Chat
            bot.send_message(chat_id=chat_id, text=response)
        
        # Telegram erwartet eine OK-Antwort für den Webhook
        return 'OK', 200
    except Exception as e:
        # Im Fehlerfall gib eine Fehlermeldung zurück
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=int(os.getenv('PORT', 5000)))

