import os
import logging
from flask import Flask

# Umgebungsvariablen für API-Keys (falls du sie in der Flask-App auch brauchst)
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Nicht mehr hier benötigt, da im separaten Skript
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")      # Nicht mehr hier benötigt, da im separaten Skript

# Logging einrichten
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask App initialisieren
app = Flask(__name__)

# Flask-Routen und Funktionen (hier kannst du deine Flask-spezifischen Routen hinzufügen)
@app.route('/')
def home():
    return "Bot is running! (Flask)"

# ... weitere Flask-Routen

# Port für Flask setzen
PORT = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, use_reloader=False)
