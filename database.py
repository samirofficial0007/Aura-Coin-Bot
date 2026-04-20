import os
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# .env থেকে লিঙ্ক লোড করা
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# মঙ্গোডিবি ক্লায়েন্ট সেটআপ
try:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['aura_coin_db']
    users_collection = db['users']
    logging.info("Successfully connected to MongoDB Atlas!")
except Exception as e:
    logging.error(f"MongoDB Connection Error: {e}")

# --- ইউজার ডাটা পাওয়ার ফাংশন ---
async def get_user_data(user_id: int):
    """ইউজারের বর্তমান ডাটা খুঁজে বের করে, না থাকলে নতুন তৈরি করে।"""
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        # নতুন ইউজারের জন্য ডিফল্ট ডাটা
        user = {
            "user_id": user_id,
            "balance": 0,
            "energy": 1000,
            "max_energy": 1000,
            "last_refill": int(time.time()), # বর্তমান সময়
            "referrals": 0,
            "level": 1,
            "completed_tasks": [] # ইউজার কোন কোন টাস্ক শেষ করেছে তার লিস্ট
        }
        await users_collection.insert_one(user)
    
    # এনার্জি ক্যালকুলেশন (অফলাইনে থাকার সময় কতটুকু রিফিল হয়েছে)
    user = await calculate_energy(user)
    return user

# --- এনার্জি রিফিল ক্যালকুলেশন ---
async def calculate_energy(user):
    """ইউজার অফলাইনে থাকাকালীন কতটুকু এনার্জি বেড়েছে তা হিসাব করে।"""
    now = int(time.time())
    last_refill = user.get("last_refill", now)
    seconds_passed = now - last_refill
    
    # প্রতি সেকেন্ডে ৩ পয়েন্ট করে এনার্জি বাড়বে
    refill_amount = seconds_passed * 3 
    
    if refill_amount > 0:
        new_energy = min(user["max_energy"], user["energy"] + refill_amount)
        if new_energy != user["energy"]:
            user["energy"] = new_energy
            user["last_refill"] = now
            # ডাটাবেসে আপডেট
            await users_collection.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"energy": new_energy, "last_refill": now}}
            )
    return user

# --- ট্যাপ সেভ করার ফাংশন (Server Sync) ---
async def update_user_balance(user_id: int, taps: int, current_energy: int):
    """ইউজারের ট্যাপ করা পয়েন্ট আর বর্তমান এনার্জি আপডেট করে।"""
    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"balance": taps}, # ট্যাপ পয়েন্ট সরাসরি যোগ হবে
            "$set": {
                "energy": current_energy, 
                "last_refill": int(time.time())
            }
        }
    )

# --- টাস্ক কমপ্লিট করার ফাংশন ---
async def complete_task(user_id: int, task_id: str, reward: int):
    """ইউজার টাস্ক শেষ করলে রিওয়ার্ড যোগ করে এবং টাস্কটি 'Completed' হিসেবে মার্ক করে।"""
    user = await users_collection.find_one({"user_id": user_id})
    
    # চেক করা হচ্ছে ইউজার এই টাস্ক আগে করেছে কি না
    if task_id not in user.get("completed_tasks", []):
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$inc": {"balance": reward},
                "$push": {"completed_tasks": task_id} # টাস্ক আইডি লিস্টে ঢুকিয়ে দিবে
            }
        )
        return True # সফলভাবে রিওয়ার্ড পেয়েছে
    return False # অলরেডি রিওয়ার্ড নেওয়া হয়ে গেছে
