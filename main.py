import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PRIMARY_MODEL = "meta-llama/llama-3.3-70b-instruct:free"
FALLBACK_MODEL = "nex-agi/deepseek-v3.1-nex-n1:free"
CLEANUP_MODEL  = "mistralai/mistral-small-3.1-24b-instruct:free"

user_data = {}

def ai_call(prompt, model):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional copywriter. Write clear, benefit-focused copy. No hype."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 700
    }
    r = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ Copy Bot Ready\n\n"
        "/brief – send product info\n"
        "/write – generate copy\n"
        "/pick – select draft\n"
        "/revise – improve\n"
        "/deliver – final copy"
    )

async def brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id] = {}
    await update.message.reply_text("Send product info (product, audience, features).")

async def save_brief(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data[update.effective_chat.id]["brief"] = update.message.text
    await update.message.reply_text("✅ Brief saved. Use /write")

async def write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    brief = user_data.get(chat, {}).get("brief")
    if not brief:
        await update.message.reply_text("Use /brief first.")
        return

    prompt = f"""
Write 3 product descriptions (120–150 words each).

Product info:
{brief}

Rules:
- Short sentences
- Plain English
- Benefits over features
- No hype
"""
    try:
        text = ai_call(prompt, PRIMARY_MODEL)
    except:
        text = ai_call(prompt, FALLBACK_MODEL)

    user_data[chat]["draft"] = text
    await update.message.reply_text(f"✍️ Drafts:\n\n{text}\n\nUse /pick")

async def pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    user_data[chat]["chosen"] = user_data[chat]["draft"]
    await update.message.reply_text("✅ Draft selected. Use /revise or /deliver")

async def revise(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    text = user_data.get(chat, {}).get("chosen")
    if not text:
        await update.message.reply_text("Pick a draft first.")
        return

    prompt = f"Improve this copy. Make it clearer and shorter.\n\n{text}"
    revised = ai_call(prompt, CLEANUP_MODEL)
    user_data[chat]["final"] = revised
    await update.message.reply_text(f"🛠 Revised:\n\n{revised}")

async def deliver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat.id
    final = user_data.get(chat, {}).get("final")
    if not final:
        await update.message.reply_text("Nothing to deliver yet.")
        return

    await update.message.reply_text(
        f"📦 FINAL COPY\n\n{final}\n\n"
        "Client message:\n"
        "Here’s the draft. Want it shorter, more premium, or more casual?"
    )

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("brief", brief))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_brief))
    app.add_handler(CommandHandler("write", write))
    app.add_handler(CommandHandler("pick", pick))
    app.add_handler(CommandHandler("revise", revise))
    app.add_handler(CommandHandler("deliver", deliver))
    app.run_polling()

if __name__ == "__main__":
    main()
