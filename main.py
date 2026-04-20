import os
import asyncio
import logging
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# আমাদের অন্য ফাইলগুলো থেকে ফাংশন ইমপোর্ট করা
from database import get_user_data, update_user_balance
from bot import main as start_bot_logic

# .env ফাইল লোড করা
load_dotenv()

app = FastAPI()

# --- 📂 Static Files Setup ---
# এটি তোর HTML, CSS এবং JS ফাইলগুলোকে সার্ভারে এক্সেসযোগ্য করবে
app.mount("/static", StaticFiles(directory="static"), name="static")

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)

# --- 🛠 ডাটা মডেল (API এর জন্য) ---
class SyncData(BaseModel):
    user_id: int
    taps: int
    energy: int

# --- 🌐 Routes (Frontend-এর জন্য) ---

@app.get("/")
async def serve_home():
    """ইউজার যখন লিঙ্কে ঢুকবে তখন index.html ফাইলটি দেখাবে।"""
    return FileResponse("static/index.html")

@app.get("/api/user/{user_id}")
async def fetch_user(user_id: int):
    """ইউজার যখন গেম ওপেন করবে তখন তার ব্যালেন্স আর এনার্জি ডাটাবেস থেকে আনবে।"""
    try:
        user_data = await get_user_data(user_id)
        # ডাটাবেস অবজেক্টকে JSON ফরম্যাটে পাঠানো
        return {
            "status": "success",
            "balance": user_data['balance'],
            "energy": user_data['energy'],
            "max_energy": user_data['max_energy']
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/sync")
async def sync_data(data: SyncData):
    """ইউজার যখন ট্যাপ থামাবে তখন ডাটাবেসে সেই ট্যাপ আর এনার্জি সেভ করবে।"""
    try:
        await update_user_balance(data.user_id, data.taps, data.energy)
        return {"status": "success", "message": "Data synced successfully!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# --- 🤖 Telegram Bot Integration (For Render) ---

@app.on_event("startup")
async def startup_event():
    """রেন্ডারে সার্ভার চালু হওয়ার সাথে সাথে টেলিগ্রাম বটকেও ব্যাকগ্রাউন্ডে চালু করবে।"""
    logging.info("--- Starting Aura Coin API & Bot ---")
    
    # বটকে আলাদা একটি ব্যাকগ্রাউন্ড টাস্ক হিসেবে রান করানো
    # এতে গেমের ওয়েবসাইট আর বট একই সাথে চলবে
    asyncio.create_task(run_telegram_bot())

async def run_telegram_bot():
    try:
        # bot.py এর মেইন ফাংশনটি কল করা
        # এটি যেন ব্লকিং না হয় সেজন্য run_polling(drop_pending_updates=True) bot.py-তে থাকা উচিত
        await start_bot_logic() 
    except Exception as e:
        logging.error(f"Bot failed to start: {e}")

# রেন্ডার পোর্ট সেটআপ
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
