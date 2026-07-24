import sys, types, sqlite3, os, random
sys.modules['imghdr'] = types.ModuleType('imghdr')
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, InputFile
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

conn = sqlite3.connect('igbooster_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, telegram_id TEXT UNIQUE, coins INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0, referred_by TEXT, ig_username TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS fake_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, ig_username TEXT, password TEXT, followers INTEGER DEFAULT 0)''')
c.execute('''CREATE TABLE IF NOT EXISTS earn_tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT, fake_acc_id INTEGER, status TEXT DEFAULT 'pending')''')
c.execute('''CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT, type TEXT, qty INTEGER, username TEXT, link TEXT, status TEXT DEFAULT 'pending', coins_cut INTEGER)''')
c.execute('''CREATE TABLE IF NOT EXISTS coin_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT, amount_inr INTEGER, coins_to_add INTEGER, utr_id TEXT UNIQUE, status TEXT DEFAULT 'pending')''')
c.execute('''CREATE TABLE IF NOT EXISTS packages (id INTEGER PRIMARY KEY AUTOINCREMENT, price INTEGER, coins INTEGER, name TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)''')
c.execute("SELECT COUNT(*) FROM packages")
if c.fetchone()[0]==0: c.executemany("INSERT INTO packages (price, coins, name) VALUES (?,?,?)", [(30,300,'300 Coins'),(99,1000,'1000 Coins'),(399,5000,'5000 Coins')])
conn.commit()

main_menu = ReplyKeyboardMarkup([['/earn ⚡', '/balance 👛'],['/order 📦', '/shop 💰'],['/refer 🤝', '/leaderboard 🏆']], resize_keyboard=True)

# 1. EARN SYSTEM - FAKE ACCOUNT FOLLOW
def earn(update: Update, context: CallbackContext):
    telegram_id = str(update.effective_user.id)
    c.execute("SELECT * FROM fake_accounts ORDER BY followers ASC LIMIT 1")
    acc = c.fetchone()
    if not acc: return update.message.reply_text("❌ Abhi koi task nahi hai")

    acc_id, ig_username, password, _ = acc
    c.execute("INSERT INTO earn_tasks (user_id, fake_acc_id) VALUES (?,?)", (telegram_id, acc_id))
    task_id = c.lastrowid
    conn.commit()

    text = f"⚡ EARN 10 COINS\n\n1. Go to Instagram\n2. Follow: @{ig_username}\n3. Send screenshot here with: `/done {task_id}`"
    update.message.reply_text(text)

def done(update: Update, context: CallbackContext):
    telegram_id = str(update.effective_user.id)
    try:
        task_id = context.args[0]
        c.execute("SELECT * FROM earn_tasks WHERE id=? AND user_id=? AND status='pending'", (task_id, telegram_id))
        if not c.fetchone(): return update.message.reply_text("❌ Invalid Task ID")
        c.execute("UPDATE earn_tasks SET status='completed' WHERE id=?", (task_id,))
        c.execute("UPDATE users SET coins=coins+10 WHERE telegram_id=?", (telegram_id,))
        conn.commit()
        update.message.reply_text("✅ +10 Coins Added! Screenshot admin check karega")
    except: update.message.reply_text("Format: /done 1")

# 2. ADMIN - FAKE ACCOUNT ADD
def addig(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    try:
        _, username, password = context.args
        c.execute("INSERT INTO fake_accounts (ig_username, password) VALUES (?,?)", (username, password))
        conn.commit()
        update.message.reply_text(f"✅ Fake IG Added: @{username}")
    except: update.message.reply_text("Format: /addig username password")

# 3. ORDER SYSTEM - LINK SE
def order(update: Update, context: CallbackContext):
    telegram_id = str(update.effective_user.id)
    try:
        _, type, qty, username = context.args
        link = context.args[4] if len(context.args)>4 else ""
        qty = int(qty)
        coins_needed = qty if type=="followers" else qty//2
        c.execute("SELECT coins FROM users WHERE telegram_id=?", (telegram_id,))
        if c.fetchone()[0] < coins_needed: return update.message.reply_text("❌ Not enough coins")
        c.execute("UPDATE users SET coins=coins-? WHERE telegram_id=?", (coins_needed, telegram_id))
        c.execute("INSERT INTO orders (telegram_id, type, qty, username, link, coins_cut) VALUES (?,?,?,?,?,?)", (telegram_id, type, qty, username, link, coins_needed))
        conn.commit()
        update.message.reply_text(f"✅ Order Placed! ID: {c.lastrowid}\nStatus: Pending\nLink: {link}")
        context.bot.send_message(ADMIN_ID, f"📦 NEW ORDER #{c.lastrowid}\nUser: {telegram_id}\n{type} {qty} for @{username}\nLink: {link}")
    except: update.message.reply_text("Format: /order followers 100 username https://instagram.com/username")

def myorders(update: Update, context: CallbackContext):
    telegram_id = str(update.effective_user.id)
    c.execute("SELECT id, type, qty, username, status FROM orders WHERE telegram_id=? ORDER BY id DESC LIMIT 5", (telegram_id,))
    orders = c.fetchall()
    text = "📦 YOUR ORDERS\n"
    for o in orders: text += f"#{o[0]} {o[1]} {o[2]} @{o[3]} - {o[4]}\n"
    update.message.reply_text(text if orders else "No orders yet")

def adminpanel(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    text = "👑 ADMIN PANEL\n/addig username password - Fake ID add\n/orderlist - Orders\n/setpackage 30 300 - Package add"
    update.message.reply_text(text)

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", lambda u,c: u.message.reply_text("Welcome!", reply_markup=main_menu)))
    dp.add_handler(CommandHandler("earn", earn))
    dp.add_handler(CommandHandler("done", done))
    dp.add_handler(CommandHandler("order", order))
    dp.add_handler(CommandHandler("myorders", myorders))
    dp.add_handler(CommandHandler("addig", addig))
    dp.add_handler(CommandHandler("adminpanel", adminpanel))
    print("✅ IG BOOSTER PRO BOT LIVE")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
