import sqlite3, os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
DB_FILE = "ig_booster.db"
COIN_PER_FOLLOW = 10
PRICE_1000_FOLLOWERS = 10000
CHANNEL_URL = "https://t.me/+EmbyFjOhmPgyOWI1"
GROUP_URL = "https://t.me/+Gx211WaaAmIwZDc1"

# ===== DATABASE =====
def db(q,p=()): conn=sqlite3.connect(DB_FILE);c=conn.cursor();c.execute(q,p);conn.commit();conn.close()
def dbf(q,p=()): conn=sqlite3.connect(DB_FILE);c=conn.cursor();c.execute(q,p);r=c.fetchall();conn.close();return r

def init_db():
    db("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, ig_link TEXT, coins INTEGER DEFAULT 0, balance REAL DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ig_link TEXT, amount INTEGER, done INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS earn_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, ig_link TEXT, owner_id INTEGER, claimed_by INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, amount INTEGER, used INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

def get_user(uid): db("INSERT OR IGNORE INTO users (user_id) VALUES (?)",(uid,)); return dbf("SELECT ig_link, coins, balance FROM users WHERE user_id=?",(uid,))[0]
def add_coins(uid, amt): db("UPDATE users SET coins = coins +? WHERE user_id=?",(amt,uid))

# ===== USER COMMANDS =====
def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("💰 Earn Coins", callback_data="earn")],
        [InlineKeyboardButton("📦 Order Followers", callback_data="order")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("👥 Community", callback_data="community")]
    ]
    update.message.reply_text(f"**🔥 WELCOME TO IG BOOSTER BOT 🔥**\n\nHey {update.effective_user.first_name}!\n\n**Kaise kaam karta hai:**\n1. `/profile <ig_link>` se 300 Free Coins lo\n2. `/earncoin` se logo ko follow karke coins kamao\n3. Coins se `/order` laga kar followers lo\n`/help` for all commands", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

def help_cmd(update: Update, context: CallbackContext):
    text = """**📖 ALL COMMANDS**
**USER:**
`/profile <ig_link>` - IG Add + 300 Free Coins
`/earncoin` - Follow karke coins kamao
`/order <ig_link> <amount>` - Followers Order
`/growing` - Coins Buy Kare
`/addbal` - Balance Add Kare
`/balance` - Balance & Coins Check
`/redeem <code>` - Redeem Code Use
`/community` - Join Our Channel & Group

**ADMIN:**
`/setqr` - QR Photo Reply me bhejo
`/created <amount> <code>` - Redeem Code Banaye
`/broadcast` - Photo/Text Reply me bhejo"""
    update.message.reply_text(text, parse_mode='Markdown')

def profile(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    ig_link, coins, bal = get_user(uid)
    if not context.args:
        update.message.reply_text(f"**👤 YOUR PROFILE**\n\nIG Link: `{ig_link if ig_link else 'Not Set'}`\n**Coins:** `{coins}`\n**Balance:** `{bal}₹`\n\nSet: `/profile https://instagram.com/yourid`", parse_mode='Markdown'); return
    new_ig = context.args[0]
    if not ig_link:
        db("UPDATE users SET ig_link=?, coins = coins + 300 WHERE user_id=?",(new_ig, uid))
        update.message.reply_text(f"✅ IG Account Saved: `{new_ig}`\n\n🎁 **Welcome Bonus: +300 Coins Credited!**", parse_mode='Markdown')
    else:
        db("UPDATE users SET ig_link=? WHERE user_id=?",(new_ig, uid))
        update.message.reply_text(f"✅ IG Account Updated: `{new_ig}`", parse_mode='Markdown')

def earncoin(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if 'current_earn' in context.user_data:
        old = context.user_data['current_earn']
        db("UPDATE earn_queue SET claimed_by=0 WHERE id=?",(old,))
    order = dbf("SELECT id, ig_link, owner_id FROM earn_queue WHERE claimed_by=0 LIMIT 1")
    if not order: update.message.reply_text("❌ Abhi koi order nahi hai. Thodi der baad try karo."); return
    oid, ig_link, owner = order[0]
    db("UPDATE earn_queue SET claimed_by=? WHERE id=?",(uid, oid))
    context.user_data['current_earn'] = oid
    keyboard = [[InlineKeyboardButton("✅ I FOLLOWED", callback_data="followed")],[InlineKeyboardButton("OPEN IG", url=ig_link)]]
    update.message.reply_text(f"**FOLLOW THIS PROFILE**\n\nFollow karke `I FOLLOWED` button dabao\nAapko `{COIN_PER_FOLLOW} Coins` milenge\n\nLink: `{ig_link}`", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

def order(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if len(context.args) < 2: update.message.reply_text("Use: `/order <ig_link> <amount>`", parse_mode='Markdown'); return
    ig_link, amount = context.args[0], int(context.args[1])
    if amount < 100 or amount > 1000000: update.message.reply_text("❌ Min 100, Max 1000000 followers"); return
    cost = int((amount / 1000) * PRICE_1000_FOLLOWERS)
    coins = get_user(uid)[1]
    if coins < cost: update.message.reply_text(f"❌ {cost} Coins chahiye. Aapke paas `{coins}` hai.\n`/growing` se coins buy karo"); return
    db("UPDATE users SET coins = coins -? WHERE user_id=?",(cost, uid))
    db("INSERT INTO orders (user_id, ig_link, amount) VALUES (?,?,?)",(uid, ig_link, amount))
    for i in range(amount): db("INSERT INTO earn_queue (ig_link, owner_id) VALUES (?,?)",(ig_link, uid))
    update.message.reply_text(f"✅ Order Placed!\n\n**IG:** `{ig_link}`\n**Amount:** `{amount}`\n**Cost:** `{cost} Coins`", parse_mode='Markdown')

def growing(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("10000 Coins - 30₹", callback_data="buy_10000")],
        [InlineKeyboardButton("20000 Coins - 55₹", callback_data="buy_20000")],
        [InlineKeyboardButton("100000 Coins - 150₹", callback_data="buy_100000")],
        [InlineKeyboardButton("1000000 Coins - 300₹", callback_data="buy_1000000")]
    ]
    update.message.reply_text("**💎 BUY COINS**\n\nPehle `/addbal` se balance add karo", reply_markup=InlineKeyboardMarkup(keyboard))

def addbal(update: Update, context: CallbackContext):
    qr = dbf("SELECT value FROM settings WHERE key='qr'")
    if not qr or not qr[0][0]: update.message.reply_text("❌ Admin ne abhi QR set nahi kiya"); return
    update.message.reply_photo(qr[0][0], caption="**Scan & Pay Here**\n\nPayment ke baad Screenshot @OwnerSween ko bhej do")

def balance(update: Update, context: CallbackContext):
    uid = update.effective_user.id; ig, coins, bal = get_user(uid)
    update.message.reply_text(f"**💰 YOUR BALANCE**\n\n**Coins:** `{coins}`\n**Wallet Balance:** `{bal}₹`", parse_mode='Markdown')

def redeem(update: Update, context: CallbackContext):
    uid = update.effective_user.id; code = context.args[0]
    res = dbf("SELECT amount, used FROM redeem_codes WHERE code=?",(code,))
    if not res: update.message.reply_text("❌ Invalid Code"); return
    amount, used = res[0]
    if used: update.message.reply_text("❌ Code already used"); return
    db("UPDATE redeem_codes SET used=1 WHERE code=?",(code,)); add_coins(uid, amount)
    update.message.reply_text(f"✅ Redeemed! +{amount} Coins Added")

def community(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("📢 Channel", url=CHANNEL_URL), InlineKeyboardButton("💬 Group", url=GROUP_URL)]]
    caption = """**👥 COME TO YOUR COMMUNITY** 👥

**Join karne ke reason:**
1. 🎁 **Redeem Code** - Yaha daily free codes milte hai
2. 📢 **Updates** - Bot ki nayi update sabse pehle yaha
3. 🛡️ **Support** - Koi problem ho to direct admin se baat"""
    update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ===== ADMIN COMMANDS =====
def created(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    amount, code = int(context.args[0]), context.args[1]
    db("INSERT OR REPLACE INTO redeem_codes VALUES (?,?,0)",(code, amount))
    update.message.reply_text(f"✅ Redeem Code Created\nCode: `{code}`\nAmount: `{amount} Coins`", parse_mode='Markdown')

def setqr(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    if not update.message.reply_to_message.photo: return
    file_id = update.message.reply_to_message.photo[-1].file_id
    db("INSERT OR REPLACE INTO settings VALUES ('qr',?)",(file_id,))
    update.message.reply_text("✅ QR Set Ho Gaya")

def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    users = dbf("SELECT user_id FROM users"); msg = update.message.reply_to_message
    for u in users:
        try:
            if msg.photo: context.bot.send_photo(u[0], msg.photo[-1].file_id, caption=msg.caption)
            elif msg.text: context.bot.send_message(u[0], msg.text)
        except: pass
    update.message.reply_text(f"✅ Broadcast sent to {len(users)} users")

def button(update: Update, context: CallbackContext):
    q = update.callback_query; q.answer()
    uid = q.from_user.id
    if q.data == "followed":
        if 'current_earn' not in context.user_data: return
        oid = context.user_data['current_earn']
        add_coins(uid, COIN_PER_FOLLOW)
        db("DELETE FROM earn_queue WHERE id=?",(oid,))
        context.user_data.pop('current_earn')
        coins = get_user(uid)[1]
        q.edit_message_text(f"✅ Verified! +{COIN_PER_FOLLOW} Coins\n\n**Total Coins:** `{coins}`", parse_mode='Markdown')
    if q.data == "earn": earncoin(q.message, context)
    if q.data == "order": q.message.reply_text("Use: `/order <ig_link> <amount>`", parse_mode='Markdown')
    if q.data == "profile": profile(q.message, context)
    if q.data == "community": community(q.message, context)
    if q.data.startswith("buy_"):
        amount = int(q.data.split("_")[1]); price = {10000:30, 20000:55, 100000:150, 1000000:300}[amount]
        bal = get_user(uid)[2]
        if bal < price: q.edit_message_text("❌ Balance kam hai. `/addbal`"); return
        db("UPDATE users SET balance = balance -?, coins = coins +? WHERE user_id=?",(price, amount, uid))
        q.edit_message_text(f"✅ {amount} Coins Buy Kiye! -{price}₹")

def main():
    init_db(); up=Updater(TOKEN,use_context=True); dp=up.dispatcher
    dp.add_handler(CommandHandler("start",start)); dp.add_handler(CommandHandler("help",help_cmd))
    dp.add_handler(CommandHandler("profile",profile)); dp.add_handler(CommandHandler("earncoin",earncoin))
    dp.add_handler(CommandHandler("order",order)); dp.add_handler(CommandHandler("growing",growing))
    dp.add_handler(CommandHandler("addbal",addbal)); dp.add_handler(CommandHandler("balance",balance))
    dp.add_handler(CommandHandler("created",created)); dp.add_handler(CommandHandler("redeem",redeem))
    dp.add_handler(CommandHandler("setqr",setqr)); dp.add_handler(CommandHandler("broadcast",broadcast))
    dp.add_handler(CommandHandler("community",community))
    dp.add_handler(CallbackQueryHandler(button))
    up.start_polling(); print("✅ IG BOOSTER BOT v1.2 RUNNING - ALL COMMANDS"); up.idle()
if __name__=='__main__': main()
