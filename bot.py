import os
import logging
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, MenuButtonWebApp
from telegram.ext import Application, CommandHandler, ContextTypes

# .env ফাইল থেকে টোকেন লোড করা
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
# তোর গেমের লিঙ্ক (রেন্ডারে হোস্ট করার পর যেটা পাবি)
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-app.onrender.com") 

# তোর অ্যাডমিন আইডি
ADMIN_ID = 7657544184 

# লগিং সেটআপ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)

# --- /start কমান্ড হ্যান্ডলার ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name

    # ১. বাম পাশের নিচে 'Play' মেনু বাটন সেট করা (যাতে ইউজার সবসময় গেমটি পায়)
    try:
        await context.bot.set_chat_menu_button(
            chat_id=update.effective_chat.id,
            menu_button=MenuButtonWebApp(
                text="Play $AURA ✨",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )
        )
    except Exception as e:
        logging.error(f"Menu Button Error: {e}")

    # ২. প্রিমিয়াম ওয়েলকাম মেসেজ
    welcome_text = (
        f"✨ *Welcome to Aura Coin, {user_name}!* ✨\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 *The Fastest Tap-to-Earn Game*\n\n"
        "Tap the Aura Coin to earn tokens, complete\n"
        "tasks, and invite friends to boost your\n"
        "Aura Level!\n\n"
        "⚡ *0.001s Response Speed*\n"
        "🛡️ *Anti-Cheat System Active*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Start mining now and earn your $AURA!"
    )

    # ৩. ইনলাইন বাটন (Play Button)
    keyboard = [
        [InlineKeyboardButton("🎮 Play Now", web_app=WebAppInfo(url=WEBAPP_URL))],
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/your_channel")], # তোর চ্যানেল লিঙ্ক দিস
        [InlineKeyboardButton("👥 Invite Friends", url=f"https://t.me/share/url?url=https://t.me/{(await context.bot.get_me()).username}?start={user.id}&text=Join%20Aura%20Coin%20and%20mine%20together!")]
    ]

    await update.message.reply_text(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

# --- অ্যাডমিন ব্রডকাস্ট কমান্ড (ঐচ্ছিক) ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    # তোর আগের ব্রডকাস্ট লজিক এখানে অ্যাড করতে পারিস পরে

def main():
    # বট অ্যাপ্লিকেশন তৈরি
    app = Application.builder().token(TOKEN).build()

    # কমান্ড হ্যান্ডলার যোগ করা
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))

    print("--- Aura Coin Bot is Live! ---")
    app.run_polling(drop_pending_updates=True)

if __name__ == '__main__':
    main()