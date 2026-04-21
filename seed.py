import os
import asyncio
import random
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# .env থেকে মঙ্গো লিঙ্ক লোড করা
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# ফেক ইউজারদের জন্য কিছু রিয়েলিস্টিক নাম
NAMES = [
    "Aura_Whale", "Satoshi_Fan", "Web3_King", "Dhaka_Miner", "Crypto_Pathan",
    "Tanvir_Gaming", "Abir_Official", "Tap_Master", "Gold_Digger", "Rich_Kid",
    "Sol_Degenerate", "Gem_Hunter", "Bull_Runner", "Moon_Walker", "Aura_Pro",
    "Binance_Guru", "Ether_Max", "Elon_Junior", "Cyber_Sarker", "Chittagong_Pro",
    "Sylhet_Whale", "Rajshahi_King", "Pixel_Miner", "Shadow_Tapper", "Void_Walker"
]

async def seed_fake_users():
    print("--- Connecting to MongoDB ---")
    client = AsyncIOMotorClient(MONGO_URI)
    db = client['aura_coin_db']
    users_collection = db['users']

    print("--- Cleaning old fake data (if any) ---")
    # শুধুমাত্র ফেক ইউজারদের রিমুভ করবে (যাদের user_id নেগেটিভ)
    await users_collection.delete_many({"user_id": {"$lt": 0}})

    fake_users = []

    print("--- Generating 100 Fake Billionaires ---")
    
    for i in range(1, 101):
        # র‍্যাঙ্ক অনুযায়ী পয়েন্ট ডিস্ট্রিবিউশন
        if i <= 10:
            # টপ ১০: ৫ বিলিয়ন থেকে ১৫ বিলিয়ন
            balance = random.randint(5_000_000_000, 15_000_000_000)
            level = random.randint(8, 10)
        elif i <= 40:
            # ১১ থেকে ৪০: ৫০০ মিলিয়ন থেকে ৫ বিলিয়ন
            balance = random.randint(500_000_000, 5_000_000_000)
            level = random.randint(5, 7)
        else:
            # ৪১ থেকে ১০০: ১০ মিলিয়ন থেকে ৫০০ মিলিয়ন
            balance = random.randint(10_000_000, 500_000_000)
            level = random.randint(2, 4)

        # র্যান্ডম নাম তৈরি (নাম + র্যান্ডম সংখ্যা)
        base_name = random.choice(NAMES)
        username = f"{base_name}_{random.randint(10, 999)}"
        
        fake_user = {
            "user_id": -i,  # নেগেটিভ আইডি দিচ্ছি যাতে রিয়েল ইউজারের সাথে না মিশে যায়
            "username": username,
            "first_name": username,
            "balance": balance,
            "energy": 1000,
            "max_energy": 1000,
            "level": level,
            "is_fake": True, # চিনতে পারার জন্য ফ্ল্যাগ
            "referrals": random.randint(0, 50),
            "last_refill": 0
        }
        fake_users.append(fake_user)

    # একবারে সব ডাটা ইনসার্ট করা
    if fake_users:
        await users_collection.insert_many(fake_users)
        print(f"✅ Successfully added {len(fake_users)} fake users to Leaderboard!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(seed_fake_users())
