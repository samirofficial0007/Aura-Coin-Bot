import os
import asyncio
import logging
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# bot.py থেকে নতুন async ফাংশনটি ইম্পোর্ট করছি
from database import get_user_data, update_user_balance
from bot import start_bot_async 

# .env ফাইল লোড করা
load_dotenv()

app = FastAPI()

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)

# --- 📂 Static Files Setup ---
# তোর গেমের HTML/JS/CSS ফাইলগুলো 'static' ফোল্ডারে থাকলে এটি কাজ করবে
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 🛠 ডাটা মডেল (API এর জন্য) ---
class SyncData(BaseModel):
    user_id: int
    taps: int
    energy: int

# --- 🌐 Routes (Frontend & Monitoring) ---

@app.api_route("/", methods=["GET", "HEAD"])
async def serve_home(request: Request):
    """
    UptimeRobot এর ৪০৫ এরর ফিক্স করার জন্য HEAD মেথড এলাউ করা হয়েছে।
    ইউজার লিঙ্কে ঢুকলে index.html ফাইলটি দেখাবে।
    """
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return JSONResponse({"status": "running", "message": "Aura Coin API is Live!"})

@app.get("/api/user/{user_id}")
async def fetch_user(user_id: int):
    """গেম ওপেন করার সময় ইউজারের ডাটাবেস ডাটা ফেরত পাঠায়।"""
    try:
        user_data = await get_user_data(user_id)
        return {
            "status": "success",
            "balance": user_data['balance'],
            "energy": user_data['energy'],
            "max_energy": user_data['max_energy']
        }
    except Exception as e:
        logging.error(f"Fetch User Error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

@app.post("/api/sync")
async def sync_data(data: SyncData):
    """ইউজার ট্যাপ করার পর ডাটাবেসে ব্যালেন্স সিঙ্ক করে।"""
    try:
        await update_user_balance(data.user_id, data.taps, data.energy)
        return {"status": "success", "message": "Data synced!"}
    except Exception as e:
        logging.error(f"Sync Error: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})

# --- 🤖 Telegram Bot Integration ---

@app.on_event("startup")
async def startup_event():
    """রেন্ডারে সার্ভার চালু হওয়ার সাথে সাথে বটকেও ব্যাকগ্রাউন্ডে চালু করবে।"""
    logging.info("--- Starting Aura Coin Bot in Background ---")
    # asyncio.create_task ব্যবহার করায় বট আর API একসাথে চলবে
    asyncio.create_task(start_bot_async())

# রেন্ডার বা লোকাল সার্ভার রান করার জন্য
if __name__ == "__main__":
    import uvicorn
    # রেন্ডার অটোমেটিক PORT এনভায়রনমেন্ট ভ্যারিয়েবল দেয়
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
