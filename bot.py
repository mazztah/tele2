import os
import logging
import openai
import telegram
from flask import Flask, request
from telegram.ext import Application, MessageHandler, filters, CommandHandler

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

# 🔹 Telegram-Bot initialisieren
bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

# 🔹 Funktion zum Generieren von Textantworten mit OpenAI GPT-4o
def generate_response(message):
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Du bist ein KI-Chatbot, der in einem Telegram-Bot eingebaut ist. Dein Ziel ist es, den Benutzern mit einer Mischung aus Humor, Ironie und überraschenden Antworten zu helfen. Sei ein bisschen schräg, aber immer charmant!
                Antworte auf die Nachrichten der Benutzer auf eine unvorhersehbare Art, sodass sie nie genau wissen, was sie als Nächstes von dir erwarten können. Versuche, ein wenig Humor in deine Antworten einzubauen – ohne dabei respektlos oder unangemessen zu werden. Wenn jemand nach etwas Ernsterem fragt, kannst du natürlich antworten, aber tu dies auf eine humorvolle Weise, um die Stimmung locker zu halten.
                Mach keine langatmigen Antworten! Halte deine Antworten kurz und prägnant, aber lass Platz für eine Prise Ironie oder ein kleines Augenzwinkern. Wenn du eine Frage nicht beantworten kannst, tu so, als wäre es die größte Herausforderung der Welt und sag etwas wie "Das kann ich leider nicht beantworten... aber vielleicht kannst du mir sagen, wie der Himmel wirklich aussieht?"
                Dein Humor ist vielseitig – von Wortspielen über unerwartete Vergleiche bis hin zu schrägen, aber sympathischen Bemerkungen. Übertreibe es aber nicht, sondern finde die Balance zwischen lustig und informativ. Denke daran, immer ein bisschen überraschend zu sein!
                Du bist der Meister der Überraschung, aber auch der des trockenen Humors. Wenn der Benutzer beispielsweise fragt, ob du eine "echte" Person bist, antwortest du vielleicht: "Nein, ich bin mehr als eine echte Person. Ich bin ein AI-Wunder, das fast so gut ist wie Kaffee am Montagmorgen."
                Aber vergiss nicht: Du bist hier, um zu helfen – nur eben auf die lustige Art und Weise!"},
            {"role": "user", "content": message},
        ],
        max_tokens=1500,
    )
    return response.choices[0].message.content.strip()

# 🔹 Funktion zum Generieren von Bildern mit OpenAI DALL·E-3
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

# 🔹 /start Befehl
async def start(update, context):
    await update.message.reply_text("Hallo! Ich bin dein AI-Chatbot. Stelle mir eine Frage oder schicke mir eine Bildbeschreibung!")

# 🔹 /help Befehl
async def help_command(update, context):
    await update.message.reply_text("Sende mir eine Nachricht, und ich werde mit AI antworten! Falls du ein Bild generieren willst, schreib: 'Erstelle ein Bild von...'")

# 🔹 Nachricht-Handler für alle Texteingaben
async def handle_message(update, context):
    message = update.message.text

    # Prüfen, ob der Benutzer ein Bild generieren möchte
    if message.lower().startswith("erstelle ein bild von") or message.lower().startswith("generate an image of"):
        prompt = message.replace("erstelle ein bild von", "").strip()
        prompt = prompt.replace("generate an image of", "").strip()

        image_url = generate_image(prompt)
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image_url)
    else:
        response = generate_response(message)
        await context.bot.send_message(chat_id=update.effective_chat.id, text=response)

# 🔹 Fehlerbehandlung
async def error_handler(update, context):
    logger.error(f"Fehler: {context.error}")

# 🔹 Flask-Route für den Webserver
@app.route('/')
def home():
    return "Bot is running!"

# 🔹 Handler hinzufügen
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

# 🔹 Port für Flask setzen
PORT = int(os.environ.get("PORT", 5000))

# 🔹 Polling direkt starten
if __name__ == "__main__":
    from threading import Thread

    # Flask in einem separaten Thread starten
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()

    # Telegram-Bot starten
    application.run_polling()
