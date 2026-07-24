import sqlite3
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import random
import asyncio

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
UPI_ID = "7864063872.wallet@phonepe"

# ========= DATABASE =========
conn = sqlite3.connect('igbooster_pro.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, telegram_id TEXT UNIQUE, ig_username TEXT, coins INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0, referred_by TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS tasks
             (id INTEGER PRIMARY KEY AUTOINCREMENT, order_id INTEGER, ig_username TEXT, ig_dp TEXT, type TEXT, link TEXT, reward INTEGER DEFAULT 10, status TEXT DEFAULT 'active', completed_by TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS coin_orders
             (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT, amount_inr INTEGER, coins_to_add INTEGER, utr_id TEXT UNIQUE, status TEXT DEFAULT 'pending')''')

c.execute('''CREATE TABLE IF NOT EXISTS settings
             (id INTEGER PRIMARY KEY, upi_id TEXT, cost_per_follower REAL, cost_per_10k_views REAL, cost_per_like REAL)''')

c.execute("INSERT OR IGNORE INTO settings VALUES (1,?, 0.5, 10, 1.5)", (UPI_ID,))
conn.commit()

# ========= KEYBOARDS =========
main_menu = ReplyKeyboardMarkup([
    ['/earn ⚡', '/balance 👛'],
    ['/order 📦', '/shop 💰'],
    ['/refer 🤝', '/leaderboard 🏆']
], resize_keyboard=True)

# ========= COMMANDS =========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    ref = context.args[0] if context.args else None

    c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    user = c.fetchone()

    if not user:
        coins = random.randint(200, 500)
        c.execute("INSERT INTO users (telegram_id, coins, referred_by) VALUES (?,?,?)", (telegram_id, coins, ref))
        if ref:
            c.execute("UPDATE users SET coins = coins + 50, referrals = referrals + 1 WHERE telegram_id=?", (ref,))
        conn.commit()
        await update.message.reply_text(f"⚡ Welcome to IG BOOSTER PRO\n🎁 You got {coins} FREE coins!", reply_markup=main_menu)
    else:
        await update.message.reply_text("Welcome back!", reply_markup=main_menu)

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    c.execute("SELECT coins, referrals FROM users WHERE telegram_id=?", (telegram_id,))
    user = c.fetchone()
    await update.message.reply_text(f"👛 Balance: {user[0]} Coins\n🤝 Referrals: {user[1]}", reply_markup=main_menu)

async def earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT * FROM tasks WHERE status='active' AND completed_by IS NULL LIMIT 1")
    task = c.fetchone()

    if not task:
        return await update.message.reply_text("😔 No tasks available. Try later.", reply_markup=main_menu)

    task_id, order_id, ig_username, ig_dp, type, link, reward = task[0], task[1], task[2], task[3], task[4], task[5], task[6]

    keyboard = [
        [InlineKeyboardButton("🔥 OPEN INSTAGRAM", url=link)],
        [InlineKeyboardButton(f"✅ CLAIM {reward} COINS", callback_data=f"claim_{task_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(photo=ig_dp,
                                     caption=f"*NEW TASK*\n\n👤 @{ig_username}\n🎯 Action: {type.upper()}\n💰 Reward: {reward} Coins",
                                     parse_mode='Markdown', reply_markup=reply_markup)

async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    task_id = query.data.split('_')[1]
    telegram_id = str(query.from_user.id)

    c.execute("UPDATE tasks SET completed_by=?, status='done' WHERE id=? AND completed_by IS NULL", (telegram_id, task_id))
    if c.rowcount == 0:
        return await query.answer("❌ Already claimed")

    c.execute("UPDATE users SET coins = coins + 10 WHERE telegram_id=?", (telegram_id,))
    conn.commit()
    await query.edit_message_caption("✅ Task Completed! +10 Coins")

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""💰 BUY COINS
1000 = ₹99 | 5000 = ₹399 | 12000 = ₹799
UPI ID: `{UPI_ID}`

After payment: `/pay UTR1234567890`"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        utr = context.args[0]
        telegram_id = str(update.effective_user.id)
        c.execute("INSERT INTO coin_orders (telegram_id, utr_id, amount_inr, coins_to_add) VALUES (?,?,?,?)",
                  (telegram_id, utr, 399, 5000))
        conn.commit()
        await update.message.reply_text("✅ Payment submitted. Admin will verify in 5 min")
        await context.bot.send_message(ADMIN_ID, f"💰 NEW PAYMENT\nUser: {telegram_id}\nUTR: {utr}\nAmount: ₹399")
    except:
        await update.message.reply_text("Format: /pay UTR1234567890")

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    keyboard = [[InlineKeyboardButton("💰 Pending Payments", callback_data="admin_payments")]]
    await update.message.reply_text("Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    c.execute("SELECT * FROM coin_orders WHERE status='pending'")
    rows = c.fetchall()
    for r in rows:
        keyboard = [
            [InlineKeyboardButton("APPROVE", callback_data=f"approve_{r[0]}")],
            [InlineKeyboardButton("REJECT", callback_data=f"reject_{r[0]}")]
        ]
        await query.message.reply_text(f"UTR: {r[4]}\nUser: {r[1]}\nCoins: {r[3]}", reply_markup=InlineKeyboardMarkup(keyboard))

async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    order_id = query.data.split('_')[1]
    c.execute("SELECT * FROM coin_orders WHERE id=?", (order_id,))
    order = c.fetchone()
    c.execute("UPDATE users SET coins = coins +? WHERE telegram_id=?", (order[3], order[1]))
    c.execute("UPDATE coin_orders SET status='approved' WHERE id=?", (order_id,))
    conn.commit()
    await context.bot.send_message(order[1], f"✅ {order[3]} Coins Credited!")
    await query.edit_message_text("✅ Approved")

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("earn", earn))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(claim, pattern=r'^claim_'))
    app.add_handler(CallbackQueryHandler(admin_payments, pattern=r'^admin_payments'))
    app.add_handler(CallbackQueryHandler(approve, pattern=r'^approve_'))

    print("✅ IG BOOSTER PRO BOT V3 PYTHON LIVE")
    app.run_polling()

if __name__ == "__main__":
    main()
