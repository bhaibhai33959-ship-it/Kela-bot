import os
import sqlite3
import asyncio
import datetime
import random
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

# ========================================================
# 🔴 AAPKA BOT TOKEN YAHA DALEIN
# ========================================================
TOKEN = "8906765022:AAHW8rhmVddEilwT-RmXX82n_CKCbOlqt3Q"
# ========================================================

DB_NAME = os.getenv("DATABASE_PATH", "multi_group_banana.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (group_id INTEGER, user_id INTEGER, username TEXT, first_name TEXT, daily_given INTEGER DEFAULT 0, lifetime_given INTEGER DEFAULT 0, received_bananas INTEGER DEFAULT 0, PRIMARY KEY (group_id, user_id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_groups (group_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS last_reset (date TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# 🍌 KELA COMMAND & BOT REACTION HANDLER
async def kela_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or not msg.reply_to_message: return

    # Check for /kela or 🍌
    text = msg.text.strip() if msg.text else ""
    if text != "🍌" and text.lower() != "/kela": return

    giver = update.effective_user
    receiver = msg.reply_to_message.from_user
    chat_id = update.effective_chat.id
    target_msg_id = msg.reply_to_message.message_id

    if giver.id == receiver.id:
        await msg.reply_text("❌ Khud ko kela nahi de sakte! 😂", delete_after=3)
        return

    # 1. BOT REACTION (Bot apna 🍌 reaction dega)
    try:
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=target_msg_id,
            reaction=[{"type": "emoji", "emoji": "🍌"}]
        )
    except Exception: pass

    # 2. UPDATE DATABASE
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''INSERT OR IGNORE INTO active_groups (group_id) VALUES (?)''', (chat_id,))
    cursor.execute('''INSERT OR IGNORE INTO users (group_id, user_id, username, first_name) VALUES (?, ?, ?, ?)''', (chat_id, giver.id, giver.username, giver.first_name))
    cursor.execute('''UPDATE users SET daily_given = daily_given + 1, lifetime_given = lifetime_given + 1 WHERE group_id = ? AND user_id = ?''', (chat_id, giver.id))
    cursor.execute('''INSERT OR IGNORE INTO users (group_id, user_id, username, first_name) VALUES (?, ?, ?, ?)''', (chat_id, receiver.id, receiver.username, receiver.first_name))
    cursor.execute('''UPDATE users SET received_bananas = received_bananas + 1 WHERE group_id = ? AND user_id = ?''', (chat_id, receiver.id))
    conn.commit()
    conn.close()

    # 3. CONFIRMATION MESSAGE (Jo 3 sec mein delete hoga)
    confirm = await msg.reply_text(f"🍌 {giver.first_name} ne {receiver.first_name} ko kela diya!")
    await asyncio.sleep(3)
    try:
        await msg.delete()
        await confirm.delete()
    except Exception: pass

# --- BAAKI COMMANDS (Steal, Gamble, Stats) ---
# [Aap yahan wahi purana code paste kar sakte hain, main structure wahi hai]

async def my_bananas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT daily_given, lifetime_given, received_bananas FROM users WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
    row = cursor.fetchone()
    conn.close()
    dg, lg, rb = row if row else (0, 0, 0)
    await update.message.reply_text(f"👤 **{user.first_name}**\n• Aaj: {dg} 🍌\n• Total Diye: {lg} 🍌\n• Total Mile: {rb} 📥")

def main():
    if TOKEN == "Aapka_Telegram_Bot_Token_Yaha_Dalein": return
    app = Application.builder().token(TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("kela", kela_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kela_handler))
    app.add_handler(CommandHandler("mybananas", my_bananas))
    
    print("Bot 3.0 Live - Reaction + Command enabled!")
    app.run_polling()

if __name__ == '__main__':
    main()
    
