import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes
from motor.motor_asyncio import AsyncIOMotorClient

# .env ফাইল থেকে ডাটা লোড করা
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
WEBAPP_URL = os.getenv("WEBAPP_URL")

# তোর অ্যাডমিন আইডি
ADMIN_ID = 7657544184 

# ডাটাবেস সেটআপ
client = AsyncIOMotorClient(MONGO_URI)
db = client['aura_coin_db']
users_collection = db['users']

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- /start কমান্ড হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # ১. ইউজারকে ডাটাবেসে সেভ করা
    await users_collection.update_one(
        {"user_id": user.id},
        {"$set": {"username": user.username, "first_name": user.first_name}},
        upsert=True
    )

    # ২. বাম পাশের নিচে 'Play' মেনু বাটন সেট করা
    try:
        await context.bot.set_chat_menu_button(
            chat_id=chat_id,
            menu_button=MenuButtonWebApp(
                text="Play $AURA ✨",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
    except Exception as e:
        logging.error(f"Menu Button Error: {e}")

    # ৩. প্রিমিয়াম ওয়েলকাম মেসেজ
    welcome_text = (
        f"✨ *Welcome to Aura Coin, {user.first_name}!* ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 *The Fastest Tap-to-Earn Game on Telegram*\n\n"
        "Tap the Aura Coin to earn tokens, complete\n"
        "special tasks, and invite your friends to\n"
        "boost your Aura Level! 📈\n\n"
        "⚡ *0.001s Response Speed*\n"
        "🛡️ *Anti-Cheat System Active*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Start mining now and claim your $AURA!"
    )

    # ৪. ইনলাইন বাটন
    keyboard = [
        [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/SamirOfficial_News")],
        [InlineKeyboardButton("👥 Invite Friends", url=f"https://t.me/share/url?url=https://t.me/{(await context.bot.get_me()).username}?start={user.id}&text=Join%20Aura%20Coin%20and%20mine%20together!")]
    ]

    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# --- অ্যাডমিন ব্রডকাস্ট কমান্ড ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized!")
        return

    if not context.args:
        await update.message.reply_text("💡 Usage: /broadcast [Your Message]")
        return

    msg_text = " ".join(context.args)
    users = await users_collection.find().to_list(length=None)
    
    count = 0
    await update.message.reply_text(f"🚀 Broadcasting message to {len(users)} users...")

    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=msg_text)
            count += 1
        except Exception:
            pass 

    await update.message.reply_text(f"✅ Successfully sent to {count} users.")

# --- রেন্ডার সার্ভারের জন্য ব্যাকগ্রাউন্ডে রান হওয়ার ফাংশন ---
async def start_bot_async():
    """এটি main.py থেকে কল হবে"""
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))

    # পোলিং শুরু করা (এটি নন-ব্লকিং)
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logging.info("--- Aura Coin Bot is Live and Polling! ---")

# পিসিতে সরাসরি টেস্ট করার জন্য (লোকালি)
if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()
