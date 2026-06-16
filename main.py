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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            group_id INTEGER, user_id INTEGER, username TEXT, first_name TEXT,
            daily_given INTEGER DEFAULT 0, lifetime_given INTEGER DEFAULT 0,
            received_bananas INTEGER DEFAULT 0,
            PRIMARY KEY (group_id, user_id)
        )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS active_groups (group_id INTEGER PRIMARY KEY)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS last_reset (date TEXT PRIMARY KEY)''')
    conn.commit()
    conn.close()

init_db()

# 🍌 1. KELA COMMAND & BOT REACTION HANDLER
async def kela_shortcut_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    if not msg or update.effective_chat.type not in ["group", "supergroup"]:
        return

    text_content = msg.text.strip() if msg.text else ""
    if text_content != "🍌" and text_content.lower() != "/kela":
        return

    if not msg.reply_to_message:
        return

    chat_id = update.effective_chat.id
    giver = update.effective_user
    receiver = msg.reply_to_message.from_user
    target_msg_id = msg.reply_to_message.message_id

    if receiver.is_bot:
        return 

    if giver.id == receiver.id:
        warning = await msg.reply_text("❌ Khud ko kela nahi de sakte bhai! 😂")
        await asyncio.sleep(3)
        try:
            await msg.delete()
            await warning.delete()
        except Exception: pass
        return

    # Bot reaction lagayega
    try:
        await context.bot.set_message_reaction(
            chat_id=chat_id,
            message_id=target_msg_id,
            reaction=[{"type": "emoji", "emoji": "🍌"}]
        )
    except Exception:
        pass

    # Database updates
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO active_groups (group_id) VALUES (?)", (chat_id,))
    
    # Giver stats
    cursor.execute('''
        INSERT INTO users (group_id, user_id, username, first_name, daily_given, lifetime_given)
        VALUES (?, ?, ?, ?, 1, 1)
        ON CONFLICT(group_id, user_id) DO UPDATE SET
        daily_given = daily_given + 1, lifetime_given = lifetime_given + 1,
        username = excluded.username, first_name = excluded.first_name
    ''', (chat_id, giver.id, giver.username, giver.first_name))

    # Receiver stats
    cursor.execute('''
        INSERT INTO users (group_id, user_id, username, first_name, received_bananas)
        VALUES (?, ?, ?, ?, 0, 0, 1)
        ON CONFLICT(group_id, user_id) DO UPDATE SET
        received_bananas = received_bananas + 1,
        username = excluded.username, first_name = excluded.first_name
    ''', (chat_id, receiver.id, receiver.username, receiver.first_name))

    conn.commit()
    conn.close()

    # Flash confirmation message
    username_str = f" (@{giver.username})" if giver.username else ""
    confirm_msg = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🍌 {giver.first_name}{username_str} ne {receiver.first_name} ko ek kela diya!"
    )

    try: await msg.delete()
    except Exception: pass
    
    await asyncio.sleep(3)
    try: await confirm_msg.delete()
    except Exception: pass

# 🥷 2. /steal COMMAND HANDLER
async def steal_banana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    chat_id = update.effective_chat.id
    user = update.effective_user

    if update.effective_chat.type not in ["group", "supergroup"]: return
    if not msg.reply_to_message:
        await msg.reply_text("❌ Kisi ke message par Reply karke `/steal` likho!")
        return

    target = msg.reply_to_message.from_user
    if user.id == target.id:
        await msg.reply_text("❌ Apne aap se kya chori karoge bhai? 😂")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT lifetime_given FROM users WHERE group_id = ? AND user_id = ?", (chat_id, target.id))
    t_row = cursor.fetchone()
    if not t_row or t_row[0] < 1:
        await msg.reply_text(f"❌ {target.first_name} ke paas ek bhi kela nahi hai baantne ke liye, chori fail!")
        conn.close()
        return

    cursor.execute("SELECT lifetime_given FROM users WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
    s_row = cursor.fetchone()
    if not s_row or s_row[0] < 1:
        await msg.reply_text("❌ Chori karne ke liye aapke paas khud ka kam se kam 1 Lifetime Kela hona chahiye fine backup ke liye!")
        conn.close()
        return

    if random.choice([True, False]):
        cursor.execute("UPDATE users SET lifetime_given = lifetime_given - 1 WHERE group_id = ? AND user_id = ?", (chat_id, target.id))
        cursor.execute("UPDATE users SET lifetime_given = lifetime_given + 1 WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
        await msg.reply_text(f"🥷 **CHORI SUCCESSFUL!**\n\n{user.first_name} ne chupke se {target.first_name} ka 1 Lifetime 🍌 chura liya! 😂")
    else:
        cursor.execute("UPDATE users SET lifetime_given = lifetime_given - 1 WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
        cursor.execute("UPDATE users SET lifetime_given = lifetime_given + 1 WHERE group_id = ? AND user_id = ?", (chat_id, target.id))
        await msg.reply_text(f"👮‍♂️ **CHORI PAKDI GAYI!**\n\n{user.first_name} chori karte hue pakda gaya! Fine ke taur par iska 1 🍌 {target.first_name} ko de diya gaya! 🏴‍☠️")

    conn.commit()
    conn.close()

# 🎲 3. /gamble COMMAND HANDLER
async def gamble_banana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    if update.effective_chat.type not in ["group", "supergroup"]: return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT lifetime_given FROM users WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
    row = cursor.fetchone()

    if not row or row[0] < 2:
        await update.message.reply_text("🎲 Gamble ke liye aapke paas kam se kam **2 Lifetime Given Kelay** hone chahiye!")
        conn.close()
        return

    if random.random() < 0.45:
        cursor.execute("UPDATE users SET lifetime_given = lifetime_given + 2 WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
        await update.message.reply_text(f"🎰 **JACKPOT!!** {user.first_name} ne gambling ki aur **+2 Lifetime Kelay** jeet liye! 🎉")
    else:
        cursor.execute("UPDATE users SET lifetime_given = lifetime_given - 2 WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
        await update.message.reply_text(f"💸 **KANGAL!** {user.first_name} ka naseeb kharab tha aur woh **2 Lifetime Kelay** har gaya! 💀")

    conn.commit()
    conn.close()

# 👤 4. /mybananas COMMAND HANDLER
async def my_bananas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]: return
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT daily_given, lifetime_given, received_bananas FROM users WHERE group_id = ? AND user_id = ?", (chat_id, user.id))
    row = cursor.fetchone()
    conn.close()
    
    dg, lg, rb = row if row else (0, 0, 0)
    
    if lg >= 100: title = "Kela King 👑"
    elif lg >= 50: title = "Kela Trader 🤝"
    elif lg >= 10: title = "Kela Lover 🐒"
    else: title = "Kanjoos 🦉"

    msg = await update.message.reply_text(
        f"👤 **{user.first_name} ({title})**\n"
        f"• Aaj diye: {dg} 🍌\n"
        f"• Lifetime diye: {lg} 🍌\n"
        f"• Lifetime mile: {rb} 📥"
    )
    await asyncio.sleep(5)
    try:
        await update.message.delete()
        await msg.delete()
    except Exception: pass

# 📊 5. /leaderboard COMMAND HANDLER
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
        text = f"🏆 **{update.effective_chat.title} Top Givers Leaderboard** 📊\n\n"
        for idx, row in enumerate(rows, start=1):
            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            text += f"{medal} {row[0]} — {row[1]} diye 🍌\n"
            
    await update.message.reply_text(text)

# 📥 6. /topreceivers COMMAND HANDLER
async def top_receivers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type not in ["group", "supergroup"]: return
    chat_id = update.effective_chat.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, received_bananas FROM users WHERE group_id = ? AND received_bananas > 0 ORDER BY received_bananas DESC LIMIT 10", (chat_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        text = "📊 **Top Receivers:** Is group me abhi tak kisi ko 🍌 nahi mila."
    else:
        text = f"👑 **{update.effective_chat.title} Most Popular (Top Receivers)** 📥\n\n"
        for idx, row in enumerate(rows, start=1):
            medal = "👑" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
            text += f"{medal} {row[0]} — {row[1]} mile 🍌\n"
            
    await update.message.reply_text(text)

# ⏰ DAILY RESET LOOP (Raat ke 12 Baje)
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
                    conn.commit()
                conn.close()
        except Exception: pass
        await asyncio.sleep(30)

async def post_init(application: Application):
    asyncio.create_task(custom_reset_loop(ContextTypes.DEFAULT_TYPE(application)))

def main():
    if TOKEN == "Aapka_Telegram_Bot_Token_Yaha_Dalein": return
    
    app = Application.builder().token(TOKEN).post_init(post_init).get_updates_connection_pool_size(16).build()
    
    # 💥 SARE HANDLERS REGISTER HO GAYE HAIN (FIXED)
    app.add_handler(CommandHandler("steal", steal_banana))
    app.add_handler(CommandHandler("gamble", gamble_banana))
    app.add_handler(CommandHandler("mybananas", my_bananas))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("topreceivers", top_receivers))
    
    # Kela Handler Commands & Emojis ke liye
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, kela_shortcut_handler))
    app.add_handler(CommandHandler("kela", kela_shortcut_handler))
    
    print("Kela Bot 3.0 perfectly running with ALL commands enabled...")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
    
