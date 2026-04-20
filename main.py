import os
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import get_user_data, update_user_balance
import time

app = FastAPI()

# CORS সেটআপ (যাতে অন্য ডোমেইন থেকেও এপিআই কল করা যায়)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ১. Static ফাইল মাউন্ট করা (HTML, CSS, JS ফাইলগুলো এখান থেকে লোড হবে)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ২. গেমের মেইন পেজ লোড করা
@app.get("/")
async def read_index():
    return FileResponse('static/index.html')

# ৩. ডাটা মডেল (ইউজার যখন সিঙ্ক করবে তখন এই ফরম্যাটে ডাটা আসবে)
class SyncData(BaseModel):
    user_id: int
    taps: int
    energy: int

# ৪. এপিআই: ইউজারের ডাটা লোড করা
@app.get("/api/user/{user_id}")
async def fetch_user(user_id: int):
    try:
        user_data = await get_user_data(user_id)
        # ডাটাবেসের অবজেক্ট আইডি সরিয়ে শুধু প্রয়োজনীয় ডাটা পাঠানো
        return {
            "balance": user_data["balance"],
            "energy": user_data["energy"],
            "max_energy": user_data["max_energy"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ৫. এপিআই: আল্ট্রা-ফাস্ট সিঙ্ক (ডাটা সেভ করা)
# এখানে সার্ভার সাইড এন্টি-চিট লজিক আছে
last_sync_time = {}

@app.post("/api/sync")
async def sync_data(data: SyncData):
    now = time.time()
    user_id = data.user_id
    
    # --- 🛡️ SERVER-SIDE ANTI-CHEAT ---
    if user_id in last_sync_time:
        time_diff = now - last_sync_time[user_id]
        # যদি ১ সেকেন্ডে ৩০টার বেশি ট্যাপ আসে, তবে ওটা চিটিং
        max_allowed_taps = time_diff * 30 
        if data.taps > max_allowed_taps + 5: # ৫ ট্যাপ গ্রেস পিরিয়ড
            return {"status": "error", "message": "Too many taps! Slow down."}
    
    last_sync_time[user_id] = now

    try:
        # ডাটাবেসে সেভ করা
        await update_user_balance(user_id, data.taps, data.energy)
        return {"status": "success"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# সার্ভার রান করার কমান্ড (লোকাল টেস্টের জন্য)
# uvicorn main:app --reload