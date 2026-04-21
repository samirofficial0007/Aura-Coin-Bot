import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes

# database.py থেকে প্রয়োজনীয় ফাংশন ইমপোর্ট করা
from database import get_user_data

# .env ফাইল থেকে তথ্য লোড করা
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL") # এটা তোর স্ট্যাটিক সাইটের লিঙ্ক
ADMIN_ID = 7657544184 

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- 🌐 FLASK SERVER (To Keep Bot Alive on Render) ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Aura Coin Bot is Active and Mining! 🚀"

def run_flask():
    # রেন্ডার অটোমেটিক PORT এনভায়রনমেন্ট ভ্যারিয়েবল দেয়
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- 🤖 TELEGRAM BOT LOGIC ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    # ১. ডাটাবেসে ইউজার চেক করা ও ডাটা লোড করা
    # এটি database.py এর get_user_data ফাংশন কল করবে
    user_db_data = await get_user_data(user.id)

    # ২. বটের বাম পাশে নিচে 'Play' বাটন সেট করা
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

    # ৩. প্রিমিয়াম ওয়েলকাম মেসেজ
    welcome_text = (
        f"✨ *Welcome to Aura Coin, {user.first_name}!* ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 *The Ultimate Tap-to-Earn Experience*\n\n"
        "Tap the Aura Coin to earn tokens, level up,\n"
        "and invite friends to multiply your earnings! 📈\n\n"
        f"💰 *Current Balance:* {user_db_data['balance']} $AURA\n"
        f"⚡ *Energy:* {user_db_data['energy']}/{user_db_data['max_energy']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Tap the button below to start mining!"
    )

    # ৪. গেম খেলার জন্য ইনলাইন বাটন
    keyboard = [
        [InlineKeyboardButton("🎮 Play Aura Coin", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📢 Join News Channel", url="https://t.me/SamirOfficial_News")],
        [InlineKeyboardButton("👥 Invite Friends", url=f"https://t.me/share/url?url=https://t.me/{(await context.bot.get_me()).username}?start={user.id}&text=Join%20Aura%20Coin%20and%20mine%20together!")]
    ]

    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# --- 🚀 MAIN EXECUTION ---

def main():
    # ১. ফ্লাস্ক সার্ভার আলাদা থ্রেডে চালু করা (যাতে রেন্ডার ঘুমিয়ে না পড়ে)
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # ২. টেলিগ্রাম বট অ্যাপ্লিকেশন তৈরি
    application = Application.builder().token(TOKEN).build()

    # ৩. কমান্ড হ্যান্ডলার যোগ করা
    application.add_handler(CommandHandler("start", start))

    print("--- Aura Coin Bot is Live with Flask Keep-Alive! ---")
    
    # ৪. পোলিং শুরু করা
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
