import os
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# .env ফাইল থেকে তথ্য লোড করা
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# মঙ্গোডিবি কানেকশন সেটআপ
try:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['aura_coin_db']
    users_collection = db['users']
    logging.info("Connected to MongoDB successfully!")
except Exception as e:
    logging.error(f"MongoDB connection failed: {e}")

# --- ১. ইউজারের ডাটাবেস প্রোফাইল পাওয়া বা তৈরি করা ---
async def get_user_data(user_id: int):
    """ইউজার নতুন হলে ডিফল্ট ডাটা দিয়ে প্রোফাইল বানাবে, আর পুরনো হলে ডাটা রিড করবে।"""
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        # নতুন ইউজারের জন্য ডিফল্ট ভ্যালু
        user = {
            "user_id": user_id,
            "balance": 0,
            "energy": 1000,
            "max_energy": 1000,
            "last_refill": int(time.time()), # রিফিল টাইম ট্র্যাকিং
            "level": 1,
            "referrals": 0,
            "completed_tasks": []
        }
        await users_collection.insert_one(user)
    
    # অফলাইনে থাকাকালীন এনার্জি কতটুকু রিফিল হয়েছে তা হিসাব করা
    user = await calculate_energy(user)
    return user

# --- ২. এনার্জি রিফিল ক্যালকুলেশন লজিক ---
async def calculate_energy(user):
    """ইউজার যখন গেমে নেই, তখন প্রতি সেকেন্ডে ৩ পয়েন্ট করে এনার্জি রিফিল হবে।"""
    now = int(time.time())
    last_refill = user.get("last_refill", now)
    seconds_passed = now - last_refill
    
    # রিফিল রেট: ৩ পয়েন্ট পার সেকেন্ড (তুই চাইলে বাড়াতে পারিস)
    refill_amount = seconds_passed * 3 
    
    if refill_amount > 0:
        new_energy = min(user["max_energy"], user["energy"] + refill_amount)
        if new_energy != user["energy"]:
            user["energy"] = new_energy
            user["last_refill"] = now
            # ডাটাবেসে আপডেট করে দেওয়া
            await users_collection.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"energy": new_energy, "last_refill": now}}
            )
    return user

# --- ৩. ট্যাপ সিঙ্ক করার ফাংশন ---
async def update_user_balance(user_id: int, taps: int, current_energy: int):
    """গেম থেকে আসা ট্যাপ পয়েন্ট ব্যালেন্সের সাথে যোগ করা।"""
    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"balance": taps}, # ট্যাপ সংখ্যা ব্যালেন্সে যোগ হবে
            "$set": {
                "energy": current_energy, 
                "last_refill": int(time.time())
            }
        }
    )

# --- ৪. টাস্ক কমপ্লিট লজিক (ভবিষ্যতের জন্য) ---
async def complete_task(user_id: int, task_id: str, reward: int):
    """ইউজার টাস্ক শেষ করলে তাকে রিওয়ার্ড দেওয়া।"""
    user = await users_collection.find_one({"user_id": user_id})
    if task_id not in user.get("completed_tasks", []):
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$inc": {"balance": reward},
                "$push": {"completed_tasks": task_id}
            }
        )
        return True
    return False
