import os
import logging
import asyncio
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes

# database.py থেকে প্রয়োজনীয় ফাংশন ইমপোর্ট করা
from database import get_user_data, add_referral_bonus, users_collection

# .env ফাইল থেকে তথ্য লোড করা
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
WEBAPP_URL = os.getenv("WEBAPP_URL") 
ADMIN_ID = 7657544184 

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- 🌐 FLASK SERVER (Keep-Alive on Render) ---
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Aura Coin Bot is Active and Mining! 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host='0.0.0.0', port=port)

# --- 🤖 TELEGRAM BOT LOGIC ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id

    # 🤝 ১. রেফারাল বোনাস চেক (নতুন ইউজার কি না তা যাচাই করে)
    if context.args:
        try:
            referrer_id = int(context.args[0])
            # নিজেকে নিজে রেফার করা যাবে না
            if referrer_id != user.id:
                # চেক করা হচ্ছে ইউজারটি ডাটাবেসে আগে থেকেই আছে কি না
                existing_user = await users_collection.find_one({"user_id": user.id})
                if not existing_user:
                    # যদি একদম নতুন হয়, তবে রেফারারকে বোনাস দাও
                    await add_referral_bonus(referrer_id, user.id)
                    logging.info(f"Referral bonus given to {referrer_id} for inviting {user.id}")
        except (ValueError, IndexError) as e:
            logging.error(f"Referral parsing error: {e}")

    # ২. ডাটাবেস থেকে ইউজারের ডাটা লোড করা (নতুন হলে তৈরি করবে)
    user_db_data = await get_user_data(user.id)

    # ৩. 'Play' মেনু বাটন সেট করা
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

    # ৪. ওয়েলকাম মেসেজ (ব্যালেন্স ও এনার্জিসহ)
    welcome_text = (
        f"✨ *Welcome to Aura Coin, {user.first_name}!* ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 *The Ultimate Tap-to-Earn Experience*\n\n"
        "Tap the Aura Coin to earn tokens, level up,\n"
        "and invite friends to multiply your earnings! 📈\n\n"
        f"💰 *Current Balance:* {user_db_data['balance']:,} $AURA\n"
        f"⚡ *Energy:* {user_db_data['energy']}/{user_db_data['max_energy']}\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Tap the button below to start mining!"
    )

    # ৫. ইনলাইন বাটন সেটআপ
    keyboard = [
        [InlineKeyboardButton("🎮 Play Aura Coin", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📢 Join Aura News", url="https://t.me/+sZp2tojdilA0ZTc1")],
        [InlineKeyboardButton("👥 Invite Friends", url=f"https://t.me/share/url?url=https://t.me/{(await context.bot.get_me()).username}?start={user.id}&text=Join%20Aura%20Coin%20and%20mine%20together!")]
    ]

    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# --- 🚀 MAIN EXECUTION ---

def main():
    # ফ্লাস্ক সার্ভার আলাদা থ্রেডে চালানো
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))

    print("--- Aura Coin Bot is Live! ---")
    application.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()
