import sys
import types
sys.modules['imghdr'] = types.ModuleType('imghdr')

import sqlite3
import os
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
UPI_ID = "7864063872.wallet@phonepe"

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN missing")
    exit()

conn = sqlite3.connect('igbooster_pro.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, telegram_id TEXT UNIQUE, coins INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0, referred_by TEXT)''')
c.execute('''CREATE TABLE IF NOT EXISTS coin_orders (id INTEGER PRIMARY KEY AUTOINCREMENT, telegram_id TEXT, amount_inr INTEGER, coins_to_add INTEGER, utr_id TEXT UNIQUE, status TEXT DEFAULT 'pending')''')
conn.commit()

main_menu = ReplyKeyboardMarkup([['/earn ⚡', '/balance 👛'],['/order 📦', '/shop 💰'],['/refer 🤝', '/leaderboard 🏆']], resize_keyboard=True)

def start(update: Update, context: CallbackContext):
    telegram_id = str(update.effective_user.id)
    c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
    if not c.fetchone():
        coins = random.randint(200, 500)
        c.execute("INSERT INTO users (telegram_id, coins) VALUES (?,?)", (telegram_id, coins))
        conn.commit()
        update.message.reply_text(f"⚡ Welcome to IG BOOSTER PRO\n🎁 You got {coins} FREE coins!", reply_markup=main_menu)
    else:
        update.message.reply_text("Welcome back!", reply_markup=main_menu)

def balance(update: Update, context: CallbackContext):
    telegram_id = str(update.effective_user.id)
    c.execute("SELECT coins, referrals FROM users WHERE telegram_id=?", (telegram_id,))
    user = c.fetchone()
    update.message.reply_text(f"👛 Balance: {user[0]} Coins\n🤝 Referrals: {user[1]}", reply_markup=main_menu)

def shop(update: Update, context: CallbackContext):
    update.message.reply_text(f"💰 BUY COINS\n1000 = ₹99 | 5000 = ₹399\nUPI ID: `{UPI_ID}`\n\nAfter payment: `/pay UTR1234567890`", parse_mode='Markdown')

def pay(update: Update, context: CallbackContext):
    try:
        utr = context.args[0]
        telegram_id = str(update.effective_user.id)
        c.execute("INSERT INTO coin_orders (telegram_id, utr_id, amount_inr, coins_to_add) VALUES (?,?,?,?)",(telegram_id, utr, 399, 5000))
        conn.commit()
        update.message.reply_text("✅ Payment submitted. Admin will verify in 5 min")
        context.bot.send_message(ADMIN_ID, f"💰 NEW PAYMENT\nUser: {telegram_id}\nUTR: {utr}\nAmount: ₹399")
    except:
        update.message.reply_text("Format: /pay UTR1234567890")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("balance", balance))
    dp.add_handler(CommandHandler("shop", shop))
    dp.add_handler(CommandHandler("pay", pay))
    print("✅ IG BOOSTER PRO BOT LIVE ON RAILWAY")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
