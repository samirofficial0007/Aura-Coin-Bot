// --- Telegram WebApp Initialization ---
const tele = window.Telegram.WebApp;
tele.expand(); // গেমটি ফুল স্ক্রিনে ওপেন হবে
const user_id = tele.initDataUnsafe?.user?.id || 12345678; // আইডি না পেলে ডিফল্ট আইডি (টেস্টিং এর জন্য)

// --- Aura Coin Core Logic ---
let score = 0;
let energy = 1000;
let maxEnergy = 1000;
let energyRegenRate = 3;
let tapsSinceLastSync = 0; // কতগুলো ট্যাপ হলো তা ট্র্যাক করার জন্য

// --- Anti-Cheat Variables ---
let lastTapTime = 0;
let tapIntervals = [];

// DOM Elements
const scoreEl = document.getElementById('score');
const energyBar = document.getElementById('energyBar');
const energyText = document.getElementById('energyText');
const coinBtn = document.getElementById('tapZone');

// --- 📥 গেম লোড হওয়ার সময় সার্ভার থেকে ডাটা আনা ---
async function loadUserData() {
    try {
        const response = await fetch(`/api/user/${user_id}`);
        const data = await response.json();
        if (data) {
            score = data.balance;
            energy = data.energy;
            maxEnergy = data.max_energy;
            updateUI();
        }
    } catch (error) {
        console.error("Error loading user data:", error);
    }
}

// গেম শুরুতেই ডাটা লোড হবে
loadUserData();

// --- ⚡ ট্যাপ হ্যান্ডলার (সুপার ফাস্ট রেসপন্স) ---
coinBtn.addEventListener('touchstart', (e) => {
    e.preventDefault();
    
    for (let i = 0; i < e.changedTouches.length; i++) {
        const touch = e.changedTouches[i];
        handleTap(touch.clientX, touch.clientY);
    }
});

function handleTap(x, y) {
    const now = Date.now();
    const currentInterval = now - lastTapTime;

    // --- 🛡️ ANTI-AUTO CLICKER CHECK ---
    if (currentInterval < 50 && lastTapTime !== 0) return; 

    if (tapIntervals.length > 5) {
        const isPattern = tapIntervals.every(interval => Math.abs(interval - currentInterval) < 2);
        if (isPattern) return;
        tapIntervals.shift();
    }
    tapIntervals.push(currentInterval);
    lastTapTime = now;

    // --- 💰 স্কোরের কাজ শুরু ---
    if (energy > 0) {
        score += 1;
        energy -= 1;
        tapsSinceLastSync += 1; // সিঙ্কের জন্য হিসাব রাখা
        
        updateUI();
        createTapAnimation(x, y);
        triggerHaptic();
        syncWithServer(); // ট্যাপ থামলেই সেভ হবে
    }
}

function updateUI() {
    scoreEl.innerText = score.toLocaleString();
    const energyPercent = (energy / maxEnergy) * 100;
    energyBar.style.width = energyPercent + "%";
    energyText.innerText = `${energy} / ${maxEnergy}`;
}

function createTapAnimation(x, y) {
    const el = document.createElement('div');
    el.className = 'tap-number';
    el.innerText = '+1';
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    document.body.appendChild(el);

    setTimeout(() => {
        el.remove();
    }, 600);
}

function triggerHaptic() {
    if (tele.HapticFeedback) {
        tele.HapticFeedback.impactOccurred('light'); // টেলিগ্রামের নিজস্ব ভাইব্রেশন
    } else if (window.navigator.vibrate) {
        window.navigator.vibrate(10);
    }
}

// --- ⚡ ENERGY REGEN ---
setInterval(() => {
    if (energy < maxEnergy) {
        energy = Math.min(maxEnergy, energy + energyRegenRate);
        updateUI();
    }
}, 1000);

// --- ☁️ SERVER SYNC (FastAPI Connection) ---
let syncTimeout;
function syncWithServer() {
    clearTimeout(syncTimeout);
    
    // ইউজার ট্যাপ থামানোর ২ সেকেন্ড পর ডাটাবেসে সেভ হবে
    syncTimeout = setTimeout(async () => {
        if (tapsSinceLastSync === 0) return;

        console.log("Syncing taps with server:", tapsSinceLastSync);

        try {
            const response = await fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: user_id,
                    taps: tapsSinceLastSync,
                    energy: energy
                })
            });

            const result = await response.json();
            if (result.status === "success") {
                tapsSinceLastSync = 0; // সিঙ্ক সফল হলে হিসাব শূন্য করে দাও
                console.log("Database Sync Successful!");
            } else {
                console.error("Sync error:", result.message);
            }
        } catch (error) {
            console.error("Network error during sync:", error);
        }
    }, 2000); 
}