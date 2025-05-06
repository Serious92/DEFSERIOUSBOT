
from keep_alive import keep_alive

import os
import logging
import base64
from telegram import Update, InputFile
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters
)
from openai import OpenAI
from datetime import datetime
from memory import add_to_memory, get_memory, reset_memory
from logger import log_interaction
from pdf_tools import extract_text_from_pdf
from web_search import brave_search, serpapi_search

# Config
logging.basicConfig(level=logging.INFO)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

client = OpenAI(api_key=OPENAI_API_KEY)

# === TEXT ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text

    # Auto trigger ricerca web
    keywords = ["oggi", "tempo", "meteo", "novità", "ultime", "notizie", "ieri", "adesso", "recenti", "chi ha vinto", "è uscito", "quando esce"]
    if any(k in message.lower() for k in keywords):
        await update.message.reply_text("🧠 Sto cercando info aggiornate per te...")
        results = await brave_search(message)
        await update.message.reply_text(results)
        return

    chat_history = get_memory(user_id)
    chat_history.append({"role": "user", "content": message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=chat_history
        )
        reply = response.choices[0].message.content
        await update.message.reply_text(reply)
        add_to_memory(user_id, "user", message)
        add_to_memory(user_id, "assistant", reply)
        log_interaction(user_id, message, reply)
    except Exception as e:
        logging.error(f"Errore GPT: {e}")
        await update.message.reply_text("Errore durante la generazione della risposta 😢")

# === RESET ===
async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reset_memory(update.effective_user.id)
    await update.message.reply_text("🧠 Memoria resettata!")

# === SHUTDOWN ===
async def handle_shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Accesso negato.")
        return
    await update.message.reply_text("Bot in arresto. 🛑")
    os._exit(0)

# === WHOAMI ===
async def handle_whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"🧾 Il tuo ID è `{user.id}`
Username: @{user.username}", parse_mode="Markdown")

# === /WEB ===
async def handle_web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usa: /web [brave|serp] <domanda>")
        return
    engine = args[0].lower()
    query = " ".join(args[1:])
    await update.message.reply_text(f"🔍 Cerco '{query}' con {engine.title()}...")
    if engine == "brave":
        results = await brave_search(query)
    elif engine == "serp":
        results = await serpapi_search(query)
    else:
        results = "Motore non riconosciuto. Usa 'brave' o 'serp'."
    await update.message.reply_text(results)

# === /IMAGE ===
async def handle_image_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Scrivi un prompt dopo il comando /image.")
        return
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=1,
            size="1024x1024"
        )
        image_url = response.data[0].url
        await update.message.reply_photo(photo=image_url)
    except Exception as e:
        logging.error(f"Errore DALL·E: {e}")
        await update.message.reply_text("Errore nella generazione dell'immagine.")

# === VISION ===
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    file_path = "photo.jpg"
    await file.download_to_drive(file_path)
    try:
        with open(file_path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode("utf-8")
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": [
                        {"type": "text", "text": "Cosa c'è in questa immagine?"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded}"}}
                    ]}
                ]
            )
        await update.message.reply_text(response.choices[0].message.content)
    except Exception as e:
        logging.error(f"Errore Vision: {e}")
        await update.message.reply_text("Errore nell'analisi dell'immagine.")

# === TTS ===
async def handle_tts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Scrivi qualcosa dopo il comando /tts.")
        return
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text
        )
        with open("speech.mp3", "wb") as f:
            f.write(response.content)
        with open("speech.mp3", "rb") as f:
            await update.message.reply_voice(voice=InputFile(f))
    except Exception as e:
        logging.error(f"Errore TTS: {e}")
        await update.message.reply_text("Errore nella sintesi vocale.")

# === VOICE INPUT ===
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_path = "audio.ogg"
    await file.download_to_drive(file_path)
    try:
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
        await handle_text(update, context)
        add_to_memory(update.effective_user.id, "user", transcript.text)
    except Exception as e:
        logging.error(f"Errore VOICE: {e}")
        await update.message.reply_text("Errore nella trascrizione del vocale.")

# === PDF ===
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc.file_name.endswith(".pdf"):
        await update.message.reply_text("Invia un file PDF per poterlo leggere.")
        return
    file_path = "documento.pdf"
    await doc.get_file().download_to_drive(file_path)
    try:
        text = extract_text_from_pdf(file_path)
        add_to_memory(update.effective_user.id, "user", f"[PDF CONTENT]\n{text[:1000]}")
        await update.message.reply_text("✅ PDF ricevuto e analizzato!")
    except Exception as e:
        logging.error(f"Errore PDF: {e}")
        await update.message.reply_text("Errore nella lettura del PDF.")

# === START ===
if __name__ == '__main__':
    keep_alive()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("reset", handle_reset))
    app.add_handler(CommandHandler("web", handle_web_command))
    app.add_handler(CommandHandler("image", handle_image_command))
    app.add_handler(CommandHandler("tts", handle_tts))
    app.add_handler(CommandHandler("whoami", handle_whoami))
    app.add_handler(CommandHandler("shutdown", handle_shutdown))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Bot completo avviato!")
    app.run_polling(drop_pending_updates=True)
