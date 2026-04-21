import os
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# .env ফাইল লোড করা
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# মঙ্গোডিবি কানেকশন সেটআপ
try:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['aura_coin_db']
    users_collection = db['users']
    logging.info("--- Aura Database Connected Successfully! ---")
except Exception as e:
    logging.error(f"MongoDB Connection Error: {e}")

# --- ১. ইউজারের ডাটা লোড বা তৈরি করা ---
async def get_user_data(user_id: int):
    """ইউজার প্রোফাইল না থাকলে ডিফল্ট ডাটা দিয়ে তৈরি করবে।"""
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        user = {
            "user_id": user_id,
            "balance": 0,
            "energy": 1000,
            "max_energy": 1000,
            "level": 1,        # শুরুতে লেভেল ১
            "referrals": 0,
            "last_refill": int(time.time()),
            "completed_tasks": []
        }
        await users_collection.insert_one(user)
    
    # অফলাইনে থাকলে এনার্জি কতটুকু রিফিল হলো তা ক্যালকুলেট করা
    user = await calculate_energy(user)
    return user

# --- ২. ব্যাকগ্রাউন্ড এনার্জি রিফিল লজিক ---
async def calculate_energy(user):
    """ইউজার গেমের বাইরে থাকলে প্রতি সেকেন্ডে ৩ পয়েন্ট করে রিফিল হবে।"""
    now = int(time.time())
    last_refill = user.get("last_refill", now)
    seconds_passed = now - last_refill
    
    refill_amount = seconds_passed * 3 
    
    if refill_amount > 0:
        new_energy = min(user.get("max_energy", 1000), user.get("energy", 1000) + refill_amount)
        if new_energy != user.get("energy"):
            await users_collection.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"energy": new_energy, "last_refill": now}}
            )
            user["energy"] = new_energy
            user["last_refill"] = now
    return user

# --- ৩. ট্যাপ সিঙ্ক (কয়েন সেভিং ফিক্স) ---
async def update_user_balance(user_id: int, taps: int, current_energy: int):
    """ট্যাপ করার পর লেভেল অনুযায়ী কয়েন বাড়িয়ে ডাটাবেসে সেভ করা।"""
    user = await users_collection.find_one({"user_id": user_id})
    if not user: return

    level = user.get("level", 1)
    # লেভেল অনুযায়ী কয়েন ইনকাম (Level 1 = 1 coin, Level 2 = 2 coins)
    earned_coins = taps * level 

    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"balance": earned_coins},
            "$set": {
                "energy": current_energy, 
                "last_refill": int(time.time())
            }
        }
    )

# --- ৪. লেভেল আপগ্রেড সিস্টেম ---
async def upgrade_level(user_id: int):
    """কয়েন খরচ করে লেভেল বাড়ানো।"""
    user = await users_collection.find_one({"user_id": user_id})
    if not user: return False, 0, 0

    current_level = user.get("level", 1)
    upgrade_cost = current_level * 25000 # খরচ নির্ধারণ
    
    if user['balance'] >= upgrade_cost:
        new_level = current_level + 1
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$inc": {"balance": -upgrade_cost},
                "$set": {"level": new_level}
            }
        )
        return True, new_level, upgrade_cost
    return False, current_level, upgrade_cost

# --- ৫. লিডারবোর্ড (১০০ ফেক + রিয়েল মিক্সড) ---
async def get_leaderboard(user_id: int):
    """ব্যালেন্স অনুযায়ী টপ ১০০ জনের লিস্ট এবং ইউজারের বর্তমান র‍্যাঙ্ক বের করা।"""
    # ব্যালেন্সের ভিত্তিতে বড় থেকে ছোট সাজিয়ে ১০০ জনকে নেওয়া
    cursor = users_collection.find().sort("balance", -1).limit(100)
    top_users = await cursor.to_list(length=100)
    
    formatted_list = []
    for i, u in enumerate(top_users):
        formatted_list.append({
            "rank": i + 1,
            "username": u.get("username") or u.get("first_name") or "Aura Miner",
            "balance": u.get("balance", 0)
        })
    
    # ইউজারের নিজের পজিশন বের করা
    user = await users_collection.find_one({"user_id": user_id})
    if user:
        # ইউজারের চেয়ে বেশি কয়েন কয়জনের আছে তা গুনে র‍্যাঙ্ক বের করা
        user_rank = await users_collection.count_documents({"balance": {"$gt": user['balance']}}) + 1
    else:
        user_rank = "N/A"
        
    return {
        "top_100": formatted_list,
        "user_rank": user_rank
    }

# --- ৬. টাস্ক ও রেফারাল বোনাস ---
async def complete_task(user_id: int, task_id: str, reward: int):
    user = await users_collection.find_one({"user_id": user_id})
    if user and task_id not in user.get("completed_tasks", []):
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$inc": {"balance": reward},
                "$push": {"completed_tasks": task_id}
            }
        )
        return True
    return False

async def add_referral_bonus(inviter_id: int, new_user_id: int):
    """নতুন ইউজারকে রেফার করলে ইনভাইটারকে বোনাস দেওয়া।"""
    bonus = 5000 
    await users_collection.update_one(
        {"user_id": inviter_id},
        {"$inc": {"balance": bonus, "referrals": 1}}
    )
