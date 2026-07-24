import sqlite3
import os
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")

if not BOT_TOKEN or BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
    print("❌ ERROR: BOT_TOKEN missing in.env file")
    exit()

if not ADMIN_ID or ADMIN_ID == "PASTE_YOUR_TELEGRAM_ID_HERE":
    print("❌ ERROR: ADMIN_ID missing in.env file")
    exit()

ADMIN_ID = int(ADMIN_ID)
UPI_ID = "7864063872.wallet@phonepe"

# ========= DATABASE AUTO CREATE =========
conn = sqlite3.connect('igbooster_pro.db', check_same_thread=False)
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users
             (id INTEGER PRIMARY KEY, telegram_id TEXT UNIQUE, coins INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0, referred_by TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS tasks
             (id INTEGER PRIMARY KEY AUTOINCREMENT, ig_username TEXT, ig_dp TEXT, type TEXT, link TEXT, reward INTEGER DEFAULT 10, status TEXT DEFAULT 'active', completed_by TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS coin_orders
             (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT, amount_inr INTEGER, coins_to_add INTEGER, utr_id TEXT UNIQUE, status TEXT DEFAULT 'pending')''')

c.execute('''CREATE TABLE IF NOT EXISTS orders
             (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT, order_type TEXT, target_ig_username TEXT, quantity INTEGER, coins_spent INTEGER, status TEXT DEFAULT 'pending')''')
conn.commit()

# ========= KEYBOARD =========
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
    if user:
        await update.message.reply_text(f"👛 Balance: {user[0]} Coins\n🤝 Referrals: {user[1]}", reply_markup=main_menu)

async def earn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT * FROM tasks WHERE status='active' AND completed_by IS NULL LIMIT 1")
    task = c.fetchone()

    if not task:
        return await update.message.reply_text("😔 No tasks available. Check after 10 min.", reply_markup=main_menu)

    task_id, ig_username, ig_dp, type, link, reward = task[0], task[1], task[2], task[3], task[4], task[5]

    keyboard = [
        [InlineKeyboardButton("🔥 OPEN INSTAGRAM", url=link)],
        [InlineKeyboardButton(f"✅ CLAIM {reward} COINS", callback_data=f"claim_{task_id}")]
    ]
    await update.message.reply_photo(photo=ig_dp,
                                     caption=f"*NEW TASK*\n\n👤 @{ig_username}\n🎯 Action: {type.upper()}\n💰 Reward: {reward} Coins",
                                     parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

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

async def order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("1K Followers - 500 Coins", callback_data="order_followers")],
        [InlineKeyboardButton("10K Views - 100 Coins", callback_data="order_views")],
        [InlineKeyboardButton("100 Likes - 150 Coins", callback_data="order_likes")]
    ]
    await update.message.reply_text("Select Service:", reply_markup=InlineKeyboardMarkup(keyboard))

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = f"""💰 BUY COINS
1000 = ₹99 | 5000 = ₹399 | 12000 = ₹799
UPI ID: `{UPI_ID}`

After payment send: `/pay UTR1234567890`"""
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

async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = f"https://t.me/{context.bot.username}?start={update.effective_user.id}"
    await update.message.reply_text(f"🤝 Invite & Earn 50 Coins\nYour Link:\n{link}")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c.execute("SELECT telegram_id, coins FROM users ORDER BY coins DESC LIMIT 10")
    rows = c.fetchall()
    text = "🏆 TOP 10 EARNERS\n"
    for i, r in enumerate(rows):
        text += f"{i+1}. {r[0]} - {r[1]} Coins\n"
    await update.message.reply_text(text)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    keyboard = [[InlineKeyboardButton("💰 Pending Payments", callback_data="admin_payments")]]
    await update.message.reply_text("Admin Panel", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "admin_payments":
        c.execute("SELECT * FROM coin_orders WHERE status='pending'")
        rows = c.fetchall()
        if not rows:
            return await query.edit_message_text("No pending payments")
        for r in rows:
            keyboard = [
                [InlineKeyboardButton("APPROVE", callback_data=f"approve_{r[0]}")],
                [InlineKeyboardButton("REJECT", callback_data=f"reject_{r[0]}")]
            ]
            await query.message.reply_text(f"UTR: {r[4]}\nUser: {r[1]}\nCoins: {r[3]}", reply_markup=InlineKeyboardMarkup(keyboard))

    elif query.data.startswith("approve_"):
        order_id = query.data.split('_')[1]
        c.execute("SELECT * FROM coin_orders WHERE id=?", (order_id,))
        order = c.fetchone()
        c.execute("UPDATE users SET coins = coins +? WHERE telegram_id=?", (order[3], order[1]))
        c.execute("UPDATE coin_orders SET status='approved' WHERE id=?", (order_id,))
        conn.commit()
        await context.bot.send_message(order[1], f"✅ {order[3]} Coins Credited!")
        await query.edit_message_text("✅ Approved")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("earn", earn))
    app.add_handler(CommandHandler("order", order))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("pay", pay))
    app.add_handler(CommandHandler("refer", refer))
    app.add_handler(CommandHandler("leaderboard", leaderboard))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(claim, pattern=r'^claim_'))
    app.add_handler(CallbackQueryHandler(admin_buttons))

    print("✅ IG BOOSTER PRO BOT V3 - SINGLE FILE LIVE")
    app.run_polling()

if __name__ == "__main__":
    main()
