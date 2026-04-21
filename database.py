import os
import time
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# .env ফাইল লোড করা
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# মঙ্গোডিবি কানেকশন
try:
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['aura_coin_db']
    users_collection = db['users']
    logging.info("--- Aura Database Connected! ---")
except Exception as e:
    logging.error(f"Database Error: {e}")

# --- ১. ইউজারের প্রোফাইল লোড করা ---
async def get_user_data(user_id: int):
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        # নতুন ইউজার হলে এই ডিফল্ট ডাটা সেভ হবে
        user = {
            "user_id": user_id,
            "balance": 0,
            "energy": 1000,
            "max_energy": 1000,
            "level": 1,        # ডিফল্ট ১ লেভেল
            "tap_value": 1,    # ১ লেভেলে ১ কয়েন
            "referrals": 0,
            "last_refill": int(time.time()),
            "completed_tasks": []
        }
        await users_collection.insert_one(user)
    
    # অফলাইনে থাকলে কতটুকু এনার্জি বাড়লো তা হিসাব করা
    user = await calculate_energy(user)
    return user

# --- ২. এনার্জি রিফিল ক্যালকুলেশন ---
async def calculate_energy(user):
    now = int(time.time())
    last_refill = user.get("last_refill", now)
    seconds_passed = now - last_refill
    
    # প্রতি সেকেন্ডে ৩ পয়েন্ট রিফিল
    refill_amount = seconds_passed * 3 
    
    if refill_amount > 0:
        new_energy = min(user.get("max_energy", 1000), user.get("energy", 1000) + refill_amount)
        await users_collection.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"energy": new_energy, "last_refill": now}}
        )
        user["energy"] = new_energy
    return user

# --- ৩. ট্যাপ সিঙ্ক ও লেভেল অনুযায়ী কয়েন বাড়ানো ---
async def update_user_balance(user_id: int, taps: int, current_energy: int):
    user = await users_collection.find_one({"user_id": user_id})
    level = user.get("level", 1)
    
    # আইডিয়া: লেভেল ২ হলে ১ ট্যাপে ২ কয়েন, লেভেল ৩ হলে ৩ কয়েন
    earned_coins = taps * level 

    await users_collection.update_one(
        {"user_id": user_id},
        {
            "$inc": {"balance": earned_coins},
            "$set": {"energy": current_energy, "last_refill": int(time.time())}
        }
    )

# --- ৪. লেভেল আপগ্রেড সিস্টেম (কয়েন দিয়ে কেনা) ---
async def upgrade_level(user_id: int):
    user = await users_collection.find_one({"user_id": user_id})
    current_level = user.get("level", 1)
    
    # আপগ্রেড খরচ: লেভেল ২ এর জন্য ১০,০০০, ৩ এর জন্য ৫০,০০০ (তুই চাইলে বাড়াতে পারিস)
    upgrade_cost = current_level * 25000 
    
    if user['balance'] >= upgrade_cost:
        new_level = current_level + 1
        await users_collection.update_one(
            {"user_id": user_id},
            {
                "$inc": {"balance": -upgrade_cost}, # কয়েন কেটে নিবে
                "$set": {"level": new_level}
            }
        )
        return True, new_level, upgrade_cost
    return False, current_level, upgrade_cost

# --- ৫. ডাইনামিক লিডারবোর্ড (১০০ ফেক + রিয়েল মিক্সড) ---
async def get_leaderboard(user_id: int):
    # সব ইউজার (রিয়েল ও ফেক) ব্যালেন্স অনুযায়ী সাজানো
    cursor = users_collection.find().sort("balance", -1).limit(100)
    top_users = await cursor.to_list(length=100)
    
    formatted_list = []
    for i, u in enumerate(top_users):
        formatted_list.append({
            "rank": i + 1,
            "username": u.get("username") or u.get("first_name") or "Anonymous",
            "balance": u.get("balance", 0),
            "level": u.get("level", 1)
        })
    
    # বর্তমান ইউজারের নিজের র‍্যাঙ্ক বের করা
    user = await users_collection.find_one({"user_id": user_id})
    # নিজের চেয়ে বেশি কয়েন কার কার আছে তা গুনে র‍্যাঙ্ক বের করা
    user_rank = await users_collection.count_documents({"balance": {"$gt": user['balance']}}) + 1
    
    return {
        "top_100": formatted_list,
        "user_rank": user_rank,
        "user_balance": user['balance']
    }

# --- ৬. টাস্ক ও রেফারাল বোনাস ---
async def complete_task(user_id: int, task_id: str, reward: int):
    user = await users_collection.find_one({"user_id": user_id})
    if task_id not in user.get("completed_tasks", []):
        await users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"balance": reward}, "$push": {"completed_tasks": task_id}}
        )
        return True
    return False

async def add_referral_bonus(inviter_id: int, new_user_id: int):
    """রেফারাল লিঙ্কে কেউ জয়েন করলে ইনভাইটারকে বোনাস দেওয়া"""
    # একজনকে রেফার করলে ৫০০০ কয়েন বোনাস
    bonus = 5000 
    await users_collection.update_one(
        {"user_id": inviter_id},
        {"$inc": {"balance": bonus, "referrals": 1}}
    )
