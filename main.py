import os
import sqlite3
import asyncio
import datetime
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ========================================================
# 🔴 AAPKA BOT TOKEN YAHA DALEIN (QUOTES KE ANDAR)
# ========================================================
TOKEN = "8906765022:AAHW8rhmVddEilwT-RmXX82n_CKCbOlqt3Q"
# ========================================================

# Koyeb Cloud ke liye Database Path Configuration (Auto-set)
DB_NAME = os.getenv("DATABASE_PATH", "multi_group_banana.db")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            group_id INTEGER, user_id INTEGER, username TEXT, first_name TEXT,
            daily_given INTEGER DEFAULT 0, lifetime_given INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_messages (
            group_id INTEGER, message_id INTEGER, PRIMARY KEY (group_id, message_id)
        )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_groups (group_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS last_reset (date TEXT PRIMARY KEY)''')
    conn.execute("PRAGMA journal_mode=WAL;") 
    conn.commit()
    conn.close()

init_db()

def add_banana_fast(group_id, user_id, username, first_name, message_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT 1 FROM tracked_messages WHERE group_id = ? AND message_id = ?", (group_id, message_id))
    if cursor.fetchone():
        conn.close()
        return False
        
    cursor.execute("INSERT INTO tracked_messages (group_id, message_id) VALUES (?, ?)", (group_id, message_id))
    cursor.execute("INSERT OR IGNORE INTO active_groups (group_id) VALUES (?)", (group_id,))
    cursor.execute('''
        INSERT INTO users (group_id, user_id, username, first_name, daily_given, lifetime_given)
        VALUES (?, ?, ?, ?, 1, 1)
        ON CONFLICT(group_id, user_id) DO UPDATE SET
        daily_given = daily_given + 1, lifetime_given = lifetime_given + 1,
        username = excluded.username, first_name = excluded.first_name
    ''', (group_id, user_id, username, first_name))
    
    conn.commit()
    conn.close()
    return True

def get_user_stats(group_id, user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT daily_given, lifetime_given FROM users WHERE group_id = ? AND user_id = ?", (group_id, user_id))
    row = cursor.fetchone()
    conn.close()
    return row if row else (0, 0)

# 🍌 /kela command handler
async def handle_kela(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    
    if update.effective_chat.type not in ["group", "supergroup"]: return
    if not msg.reply_to_message:
        try: await msg.delete()
        except Exception: pass
        return

    giver = msg.from_user
    receiver = msg.reply_to_message.from_user
    
    if giver.id == receiver.id:
        try:
            await msg.delete()
            warning = await context.bot.send_message(chat_id=chat_id, text=f"❌ {giver.first_name}, aap khud ko 🍌 nahi de sakte!")
            await asyncio.sleep(2)
            await warning.delete()
        except Exception: pass
        return

    if add_banana_fast(chat_id, giver.id, giver.username, giver.first_name, msg.reply_to_message.message_id):
        try: await msg.delete()
        except Exception: pass
        
        username_str = f" (@{giver.username})" if giver.username else ""
        confirm_msg = await context.bot.send_message(
            chat_id=chat_id, 
            text=f"🍌 {giver.first_name}{username_str} ne {receiver.first_name} ke message par ek kela diya!"
        )
        await asyncio.sleep(3)
        try: await confirm_msg.delete()
        except Exception: pass
    else:
        try:
            await msg.delete()
            warning = await context.bot.send_message(chat_id=chat_id, text=f"❌ Is message par pehle hi 🍌 diya ja chuka hai!")
            await asyncio.sleep(2)
            await warning.delete()
        except Exception: pass

# 👤 /mybananas command handler
async def my_bananas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]: return
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    stats = get_user_stats(chat_id, user.id)
    msg = await update.message.reply_text(f"👤 {user.first_name}, aapne aaj is group me **{stats[0]}** 🍌 diye hain! (Lifetime: {stats[1]})")
    
    await asyncio.sleep(4)
    try:
        await update.message.delete()
        await msg.delete()
    except Exception: pass

# 📊 /leaderboard command handler
async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]: return
    chat_id = update.effective_chat.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, lifetime_given FROM users WHERE group_id = ? AND lifetime_given > 0 ORDER BY lifetime_given DESC LIMIT 10", (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        text = "📊 **Leaderboard:** Is group me abhi tak kisi ne 🍌 nahi diya."
    else:
        text = f"🏆 **{update.effective_chat.title} All-Time Leaderboard** 📊\n\n"
        for idx, row in enumerate(rows, start=1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            text += f"{medal} {row[0]} — {row[1]} 🍌\n"
            
    await update.message.reply_text(text)

# Raat ke 12 baje reset karne wala background loop
async def custom_reset_loop(context: ContextTypes.DEFAULT_TYPE):
    while True:
        try:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(tz)
            if now.hour == 0 and now.minute == 0:
                today_str = now.strftime("%Y-%m-%d")
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM last_reset WHERE date = ?", (today_str,))
                if not cursor.fetchone():
                    cursor.execute("INSERT INTO last_reset (date) VALUES (?)", (today_str,))
                    cursor.execute("SELECT group_id FROM active_groups")
                    for (g_id,) in cursor.fetchall():
                        cursor.execute("SELECT first_name, username, daily_given FROM users WHERE group_id = ? AND daily_given > 0 ORDER BY daily_given DESC LIMIT 1", (g_id,))
                        winner = cursor.fetchone()
                        award_text = f"🏆 **DAILY BANANA AWARD** 🏆\n\nRaat ke 12 baj chuke hain! Is group me aaj ke **Most Banana Giver** hain: {f'@{winner[1]}' if winner[1] else winner[0]} jinhone sabse zyada **{winner[2]}** 🍌 diye! 🎉👏" if winner else "🌙 Raat ke 12 baj gaye hain. Aaj is group me kisi ne kisi ko 🍌 nahi diya!"
                        try: await context.bot.send_message(chat_id=g_id, text=award_text)
                        except Exception: pass
                    cursor.execute("UPDATE users SET daily_given = 0")
                    cursor.execute("DELETE FROM tracked_messages")
                    conn.commit()
                conn.close()
        except Exception: pass
        await asyncio.sleep(30)

async def post_init(application: Application):
    asyncio.create_task(custom_reset_loop(ContextTypes.DEFAULT_TYPE(application)))

def main():
    if TOKEN == "Aapka_Telegram_Bot_Token_Yaha_Dalein": return
    
    app = Application.builder().token(TOKEN).post_init(post_init).get_updates_connection_pool_size(16).build()
    
    app.add_handler(CommandHandler("kela", handle_kela))
    app.add_handler(CommandHandler("mybananas", my_bananas))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    
    print("Multi-Group Kela Bot successfully shuru ho gaya hai...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
  
