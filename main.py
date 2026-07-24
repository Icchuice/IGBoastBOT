from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
import random

TOKEN = "8683534945:AAEk_LcMWJmI0oMIbejGxtbpVM-1QAapGV4"

rooms = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎭 Welcome to Sween Spy Game Bot!\n\n"
        "1. Sab log bot ko private me /start karein\n"
        "2. Group me /room 4 likh ke game start karein"
    )

# /room
async def room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        size = int(context.args[0])
        if size < 4 or size > 8:
            return await update.message.reply_text("Room size 4-8 hona chahiye!")

        room_id = update.effective_chat.id

        rooms[room_id] = {
            "players": [],
            "size": size,
            "started": False,
            "spy": None,
            "votes": {}
        }

        button = [[InlineKeyboardButton("Join Game", callback_data="join")]]

        await update.message.reply_text(
            f"🎮 Room created for {size} players!\nClick to join",
            reply_markup=InlineKeyboardMarkup(button)
        )

    except:
        await update.message.reply_text("Use: /room 4")

# Join button
async def join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    room = rooms.get(query.message.chat.id)

    if not room:
        return

    if room["started"]:
        await query.answer("Game already started!")
        return

    if user.id in room["players"]:
        await query.answer("Already joined!")
        return

    room["players"].append(user.id)
    await query.answer(f"Joined! ({len(room['players'])}/{room['size']})")

    await query.message.reply_text(
        f"✅ {user.first_name} joined! ({len(room['players'])}/{room['size']})"
    )

    # Start game when full
    if len(room["players"]) == room["size"]:
        await start_game(query, context)

# Game start
async def start_game(query, context):
    room = rooms[query.message.chat.id]
    players = room["players"]

    words = ["Pizza", "Burger", "Train", "Car", "School", "Hospital", "Beach", "Cinema"]

    word = random.choice(words)
    spy_word = random.choice([w for w in words if w != word])

    spy = random.choice(players)

    room["spy"] = spy
    room["started"] = True

    # Send DM to each player
    for p in players:
        try:
            if p == spy:
                await context.bot.send_message(p, f"🕵️ Tum SPY ho!\nTumhara word: {spy_word}")
            else:
                await context.bot.send_message(p, f"👤 Tum Villager ho!\nTumhara word: {word}")
        except:
            pass

    await query.message.reply_text(
        "🎯 Game Started!\n"
        "Sab apas mein baat karo aur spy dhundho.\n\n"
        "Vote karne ke liye: /vote <user_id>"
    )

# /vote
async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE):
    room_id = update.effective_chat.id
    room = rooms.get(room_id)

    if not room or not room["started"]:
        return await update.message.reply_text("Game nahi chal raha!")

    try:
        voted_id = int(context.args[0])
    except:
        return await update.message.reply_text("Use: /vote user_id")

    voter = update.effective_user.id

    if voter not in room["players"]:
        return await update.message.reply_text("Tum game mein nahi ho!")

    room["votes"][voter] = voted_id
    await update.message.reply_text("✅ Vote record ho gaya!")

    # Check if all voted
    if len(room["votes"]) == len(room["players"]):
        await end_game(update, context)

# End game
async def end_game(update, context):
    room_id = update.effective_chat.id
    room = rooms.get(room_id)

    vote_count = {}
    for v in room["votes"].values():
        vote_count[v] = vote_count.get(v, 0) + 1

    accused = max(vote_count, key=vote_count.get)
    spy = room["spy"]

    if accused == spy:
        result = "🎉 Spy pakda gaya! Villagers jeet gaye!"
    else:
        result = "😈 Spy bach gaya! Spy jeet gaya!"

    await update.message.reply_text(
        f"{result}\n\nSpy tha: {spy}"
    )

    rooms.pop(room_id, None)

# App start
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("room", room))
app.add_handler(CommandHandler("vote", vote))
app.add_handler(CallbackQueryHandler(join, pattern="^join$"))

print("Bot chal raha hai...")
app.run_polling()