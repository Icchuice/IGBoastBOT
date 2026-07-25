import sqlite3, os, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, CallbackQueryHandler

# ===== YOUR BOT DETAILS =====
TOKEN = "8751945163:AAF2qWjadfyTtF9Fe4BNAUG6VhDbaITUhyk"
ADMIN_ID = 7088023034
# ============================

DB_FILE = "ig_booster.db"
COIN_PER_FOLLOW = 10
PRICE_1000_FOLLOWERS = 10000
CHANNEL_URL = "https://t.me/+EmbyFjOhmPgyOWI1"
GROUP_URL = "https://t.me/+Gx211WaaAmIwZDc1"

def db(q,p=()):
    conn=sqlite3.connect(DB_FILE);c=conn.cursor();c.execute(q,p);conn.commit();conn.close()
def dbf(q,p=()):
    conn=sqlite3.connect(DB_FILE);c=conn.cursor();c.execute(q,p);r=c.fetchall();conn.close();return r

def init_db():
    db("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, ig_link TEXT, coins INTEGER DEFAULT 0, balance REAL DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS orders (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, ig_link TEXT, amount INTEGER, done INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS earn_queue (id INTEGER PRIMARY KEY AUTOINCREMENT, ig_link TEXT, owner_id INTEGER, claimed_by INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS redeem_codes (code TEXT PRIMARY KEY, amount INTEGER, used INTEGER DEFAULT 0)")
    db("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")

def get_user(uid):
    db("INSERT OR IGNORE INTO users (user_id) VALUES (?)",(uid,));
    return dbf("SELECT ig_link, coins, balance FROM users WHERE user_id=?",(uid,))[0]
def add_coins(uid, amt):
    db("UPDATE users SET coins = coins +? WHERE user_id=?",(amt,uid))

# ===== USER COMMANDS =====
async def start(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("💰 Earn Coins", callback_data="earn")],
        [InlineKeyboardButton("📦 Order Followers", callback_data="order")],
        [InlineKeyboardButton("👤 Profile", callback_data="profile")],
        [InlineKeyboardButton("👥 Community", callback_data="community")]
    ]
    await update.message.reply_text(
        f"**🔥 WELCOME TO IG BOOSTER BOT 🔥**\n\nHey {update.effective_user.first_name}!\n\n"
        f"**How it works:**\n1. `/profile <ig_link>` to get 300 Free Coins\n"
        f"2. `/earncoin` to earn coins by following\n"
        f"3. Use coins to `/order` followers\n"
        f"Type `/help` for all commands",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def help_cmd(update: Update, context: CallbackContext):
    text = """**📖 ALL COMMANDS**

**USER COMMANDS:**
`/profile <ig_link>` - Add IG + Get 300 Free Coins
`/earncoin` - Earn coins by following others
`/order <ig_link> <amount>` - Place order for followers
`/growing` - Buy Coins with Balance
`/addbal` - Add Balance via QR
`/balance` - Check Coins & Balance
`/redeem <code>` - Use Redeem Code
`/community` - Join Channel & Group

**ADMIN COMMANDS:**
`/setqr` - Reply to QR Photo to set payment QR
`/created <amount> <code>` - Create Redeem Code
`/broadcast` - Reply to any message/photo to broadcast"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def profile(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    ig_link, coins, bal = get_user(uid)
    if not context.args:
        await update.message.reply_text(
            f"**👤 YOUR PROFILE**\n\n"
            f"**IG Link:** `{ig_link if ig_link else 'Not Set'}`\n"
            f"**Coins:** `{coins}`\n"
            f"**Balance:** `{bal}₹`\n\n"
            f"Set/Update IG: `/profile https://instagram.com/yourid`",
            parse_mode='Markdown'
        ); return

    new_ig = context.args[0]
    if not ig_link: # FIRST TIME BONUS
        db("UPDATE users SET ig_link=?, coins = coins + 300 WHERE user_id=?",(new_ig, uid))
        await update.message.reply_text(
            f"✅ IG Account Saved: `{new_ig}`\n\n"
            f"🎁 **Welcome Bonus: +300 Coins Credited!**\n\n"
            f"Now use `/earncoin` to earn more coins",
            parse_mode='Markdown'
        )
    else:
        db("UPDATE users SET ig_link=? WHERE user_id=?",(new_ig, uid))
        await update.message.reply_text(f"✅ IG Account Updated: `{new_ig}`", parse_mode='Markdown')

async def earncoin(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    # Release previous task if any
    if 'current_earn' in context.user_data:
        db("UPDATE earn_queue SET claimed_by=0 WHERE id=?",(context.user_data['current_earn'],))

    order = dbf("SELECT id, ig_link, owner_id FROM earn_queue WHERE claimed_by=0 LIMIT 1")
    if not order:
        await update.message.reply_text("❌ No orders available right now. Try again later."); return

    oid, ig_link, owner = order[0]
    db("UPDATE earn_queue SET claimed_by=? WHERE id=?",(uid, oid))
    context.user_data['current_earn'] = oid

    keyboard = [
        [InlineKeyboardButton("✅ I FOLLOWED", callback_data="followed")],
        [InlineKeyboardButton("OPEN IG", url=ig_link)]
    ]
    await update.message.reply_text(
        f"**FOLLOW THIS PROFILE**\n\n"
        f"Follow and click `I FOLLOWED` button\n"
        f"You will get `{COIN_PER_FOLLOW} Coins`\n\n"
        f"Link: `{ig_link}`",
        reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown'
    )

async def order(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/order <ig_link> <amount>`\nEx: `/order https://instagram.com/xxx 100`", parse_mode='Markdown'); return

    ig_link, amount = context.args[0], int(context.args[1])
    if amount < 100 or amount > 1000000:
        await update.message.reply_text("❌ Minimum 100, Maximum 1,000,000 followers"); return

    cost = int((amount / 1000) * PRICE_1000_FOLLOWERS)
    coins = get_user(uid)[1]
    if coins < cost:
        await update.message.reply_text(f"❌ You need `{cost}` Coins. You have `{coins}`.\nUse `/growing` to buy coins"); return

    db("UPDATE users SET coins = coins -? WHERE user_id=?",(cost, uid))
    db("INSERT INTO orders (user_id, ig_link, amount) VALUES (?,?,?)",(uid, ig_link, amount))

    # Add to queue
    for i in range(amount):
        db("INSERT INTO earn_queue (ig_link, owner_id) VALUES (?,?)",(ig_link, uid))

    await update.message.reply_text(
        f"✅ **Order Placed Successfully!**\n\n"
        f"**IG:** `{ig_link}`\n"
        f"**Amount:** `{amount}` Followers\n"
        f"**Cost:** `{cost} Coins`\n\n"
        f"Followers will be delivered slowly",
        parse_mode='Markdown'
    )

async def growing(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("10000 Coins - 30₹", callback_data="buy_10000")],
        [InlineKeyboardButton("20000 Coins - 55₹", callback_data="buy_20000")],
        [InlineKeyboardButton("100000 Coins - 150₹", callback_data="buy_100000")],
        [InlineKeyboardButton("1000000 Coins - 300₹", callback_data="buy_1000000")]
    ]
    await update.message.reply_text(
        "**💎 BUY COINS**\n\nFirst add balance using `/addbal`",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def addbal(update: Update, context: CallbackContext):
    qr = dbf("SELECT value FROM settings WHERE key='qr'")
    if not qr or not qr[0][0]:
        await update.message.reply_text("❌ Admin has not set QR yet. Contact @OwnerSween"); return

    await update.message.reply_photo(
        qr[0][0],
        caption="**Scan & Pay Here**\n\nAfter payment send screenshot to @OwnerSween\nBalance will be added manually"
    )

async def balance(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    ig, coins, bal = get_user(uid)
    await update.message.reply_text(
        f"**💰 YOUR BALANCE**\n\n"
        f"**Coins:** `{coins}`\n"
        f"**Wallet Balance:** `{bal}₹`",
        parse_mode='Markdown'
    )

async def redeem(update: Update, context: CallbackContext):
    uid = update.effective_user.id
    if not context.args:
        await update.message.reply_text("Usage: `/redeem CODE123`"); return

    code = context.args[0]
    res = dbf("SELECT amount, used FROM redeem_codes WHERE code=?",(code,))
    if not res:
        await update.message.reply_text("❌ Invalid Code"); return

    amount, used = res[0]
    if used:
        await update.message.reply_text("❌ Code already used"); return

    db("UPDATE redeem_codes SET used=1 WHERE code=?",(code,))
    add_coins(uid, amount)
    await update.message.reply_text(f"✅ **Redeemed Successfully!**\n+{amount} Coins Added to your account")

async def community(update: Update, context: CallbackContext):
    keyboard = [
        [InlineKeyboardButton("📢 Channel", url=CHANNEL_URL), InlineKeyboardButton("💬 Group", url=GROUP_URL)]
    ]
    caption = """**👥 COME TO YOUR COMMUNITY** 👥

**Reasons to Join:**
1. 🎁 **Redeem Codes** - Get daily free codes
2. 📢 **Updates** - Get latest bot updates first
3. 🛡️ **Support** - Talk to admin directly if you have any problem"""
    await update.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

# ===== ADMIN COMMANDS =====
async def created(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/created <amount> <code>`\nEx: `/created 500 WELCOME500`"); return

    amount, code = int(context.args[0]), context.args[1]
    db("INSERT OR REPLACE INTO redeem_codes VALUES (?,?,0)",(code, amount))
    await update.message.reply_text(
        f"✅ **Redeem Code Created**\n"
        f"**Code:** `{code}`\n"
        f"**Amount:** `{amount} Coins`",
        parse_mode='Markdown'
    )

async def setqr(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text("Reply to a QR photo with `/setqr`"); return

    file_id = update.message.reply_to_message.photo[-1].file_id
    db("INSERT OR REPLACE INTO settings VALUES ('qr',?)",(file_id,))
    await update.message.reply_text("✅ **QR Code Set Successfully**")

async def broadcast(update: Update, context: CallbackContext):
    if update.effective_user.id!= ADMIN_ID: return
    if not update.message.reply_to_message:
        await update.message.reply_text("Reply to a message/photo with `/broadcast`"); return

    users = dbf("SELECT user_id FROM users")
    msg = update.message.reply_to_message
    count = 0
    for u in users:
        try:
            if msg.photo:
                await context.bot.send_photo(u[0], msg.photo[-1].file_id, caption=msg.caption)
            elif msg.text:
                await context.bot.send_message(u[0], msg.text)
            count += 1
        except: pass

    await update.message.reply_text(f"✅ **Broadcast sent to {count} users**")

# ===== BUTTON HANDLER =====
async def button(update: Update, context: CallbackContext):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id

    if q.data == "followed":
        if 'current_earn' not in context.user_data: return
        oid = context.user_data['current_earn']
        add_coins(uid, COIN_PER_FOLLOW)
        db("DELETE FROM earn_queue WHERE id=?",(oid,))
        context.user_data.pop('current_earn')
        coins = get_user(uid)[1]
        await q.edit_message_text(
            f"✅ **Verified!**\n+{COIN_PER_FOLLOW} Coins Added\n"
            f"**Total Coins:** `{coins}`\n\n"
            f"Use `/earncoin` for next task",
            parse_mode='Markdown'
        )

    elif q.data == "earn": await earncoin(q.message, context)
    elif q.data == "order": await q.message.reply_text("Usage: `/order <ig_link> <amount>`", parse_mode='Markdown')
    elif q.data == "profile": await profile(q.message, context)
    elif q.data == "community": await community(q.message, context)

    elif q.data.startswith("buy_"):
        amount = int(q.data.split("_")[1])
        price = {10000:30, 20000:55, 100000:150, 1000000:300}[amount]
        bal = get_user(uid)[2]
        if bal < price:
            await q.edit_message_text("❌ Low balance. Use `/addbal` to add balance"); return

        db("UPDATE users SET balance = balance -?, coins = coins +? WHERE user_id=?",(price, amount, uid))
        await q.edit_message_text(f"✅ **Purchase Successful!**\nBought `{amount}` Coins\n- `{price}₹` Deducted")

# ===== MAIN =====
async def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # All Commands Registered
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("earncoin", earncoin))
    app.add_handler(CommandHandler("order", order))
    app.add_handler(CommandHandler("growing", growing))
    app.add_handler(CommandHandler("addbal", addbal))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("created", created))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CommandHandler("setqr", setqr))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("community", community))
    app.add_handler(CallbackQueryHandler(button))

    print("✅ IG BOOSTER BOT v1.4 RUNNING - ALL COMMANDS ACTIVE")
    await app.run_polling()

if __name__=='__main__':
    asyncio.run(main())
