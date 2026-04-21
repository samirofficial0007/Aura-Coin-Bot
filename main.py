import os
import json
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# database.py থেকে প্রয়োজনীয় ফাংশন ইমপোর্ট করা
from database import (
    get_user_data, 
    update_user_balance, 
    get_leaderboard, 
    upgrade_level, 
    complete_task
)

load_dotenv()
app = FastAPI()

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)

# স্ট্যাটিক ফাইলস (HTML, CSS, JS) সেটআপ
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 🛠 ডাটা মডেলস ---
class SyncData(BaseModel):
    user_id: int
    taps: int
    energy: int

class UpgradeRequest(BaseModel):
    user_id: int

class TaskRequest(BaseModel):
    user_id: int
    task_id: str

# --- 🌐 ROUTES (Frontend-এর জন্য) ---

@app.get("/")
@app.head("/")
async def serve_home():
    """গেমের মেইন ইন্টারফেস দেখাবে।"""
    return FileResponse("static/index.html")

@app.get("/api/user/{user_id}")
async def fetch_user(user_id: int):
    """ইউজারের প্রোফাইল, ব্যালেন্স আর লেভেল ডাটাবেস থেকে আনবে।"""
    try:
        user_data = await get_user_data(user_id)
        # ডাটাবেস অবজেক্টকে পরিষ্কার JSON হিসেবে পাঠানো
        return {
            "status": "success",
            "balance": user_data.get('balance', 0),
            "energy": user_data.get('energy', 1000),
            "max_energy": user_data.get('max_energy', 1000),
            "level": user_data.get('level', 1),
            "completed_tasks": user_data.get('completed_tasks', [])
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.post("/api/sync")
async def sync_data(data: SyncData):
    """ট্যাপ করার পর ব্যালেন্স সিঙ্ক করবে।"""
    try:
        await update_user_balance(data.user_id, data.taps, data.energy)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.get("/api/leaderboard")
async def fetch_leaderboard(user_id: int):
    """১০০ জন ফেক মেম্বার + রিয়েল মেম্বারদের মিক্সড র‍্যাঙ্ক লিস্ট।"""
    try:
        leaderboard_data = await get_leaderboard(user_id)
        return leaderboard_data
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.get("/api/tasks")
async def get_tasks_list():
    """tasks.json থেকে সব টাস্ক লোড করে ফ্রন্টএন্ডে পাঠাবে।"""
    try:
        with open("static/tasks.json", "r") as f:
            tasks = json.load(f)
        return tasks
    except Exception as e:
        return []

@app.post("/api/task/claim")
async def claim_task(data: TaskRequest):
    """ইউজার টাস্ক শেষ করলে রিওয়ার্ড দিবে।"""
    try:
        # tasks.json থেকে রিওয়ার্ডের পরিমাণ খুঁজে বের করা
        with open("static/tasks.json", "r") as f:
            tasks = json.load(f)
        
        reward = 0
        for t in tasks:
            if t['id'] == data.task_id:
                reward = t['reward']
                break
        
        success = await complete_task(data.user_id, data.task_id, reward)
        if success:
            return {"status": "success", "reward": reward}
        else:
            return {"status": "error", "message": "Already claimed or failed!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

@app.post("/api/upgrade")
async def process_upgrade(data: UpgradeRequest):
    """ইউজার কয়েন খরচ করে লেভেল আপডেট করবে।"""
    try:
        success, new_level, cost = await upgrade_level(data.user_id)
        if success:
            return {"status": "success", "new_level": new_level, "cost": cost}
        else:
            return {"status": "error", "message": "Insufficient Balance!"}
    except Exception as e:
        return JSONResponse(status_code=500, content={"message": str(e)})

# রেন্ডার সার্ভার রান করার জন্য
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
