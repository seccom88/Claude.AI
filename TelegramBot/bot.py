from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
import asyncio
import shutil
import os

load_dotenv(os.path.expanduser("~/TelegramBot/.env"))

BOT_TOKEN = os.environ["BOT_TOKEN"]
ALLOWED_USER = int(os.environ["ALLOWED_USER"])

CLAUDE_BIN = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
SESSIONS_DIR = os.path.expanduser("~/TelegramBot/sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

def session_dir(chat_id):
    path = os.path.join(SESSIONS_DIR, str(chat_id))
    os.makedirs(path, exist_ok=True)
    return path

def has_session(chat_id):
    d = os.path.join(SESSIONS_DIR, str(chat_id))
    return os.path.isdir(d) and any(f.endswith(".jsonl") for f in os.listdir(d))

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ALLOWED_USER:
        return

    user_msg = (update.message.text or "").strip()
    if not user_msg:
        return

    cwd = session_dir(update.message.chat_id)
    cmd = [CLAUDE_BIN, "-c", "-p", user_msg] if has_session(update.message.chat_id) else [CLAUDE_BIN, "-p", user_msg]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        response = (stdout.decode() or stderr.decode() or "No output").strip()
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        response = "Error: Claude took too long to respond."
    except Exception as e:
        response = f"Error: {e}"

    await update.message.reply_text(response[:4000])

async def clear_session(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id != ALLOWED_USER:
        return
    cwd = session_dir(update.message.chat_id)
    shutil.rmtree(cwd)
    os.makedirs(cwd)
    await update.message.reply_text("Session cleared. Starting fresh.")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("clear", clear_session))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.run_polling()
