// ১. টেলিগ্রাম ওয়েব অ্যাপ ইনিশিয়ালাইজ করা
const tele = window.Telegram.WebApp;
tele.expand(); // গেমটা ফুল স্ক্রিন করে দিবে

const userId = tele.initDataUnsafe?.user?.id || 12345678; // ইউজার আইডি না পেলে ডামি আইডি

// ২. ভ্যারিয়েবল সেটআপ
let balance = 0;
let energy = 1000;
let maxEnergy = 1000;
let tapsToSync = 0;

// ৩. DOM এলিমেন্টগুলো ধরা
const balanceEl = document.getElementById('balance');
const energyEl = document.getElementById('energy');
const energyBar = document.getElementById('energy-bar');
const coin = document.getElementById('coin');

// ৪. ডাটাবেস থেকে ইউজারের তথ্য নিয়ে আসা
async function fetchUserData() {
    try {
        const response = await fetch(`/api/user/${userId}`);
        const data = await response.json();
        if (data.status === "success") {
            balance = data.balance;
            energy = data.energy;
            maxEnergy = data.max_energy;
            updateUI();
        }
    } catch (err) {
        console.error("User data fetch failed:", err);
    }
}

// ৫. UI আপডেট করার ফাংশন
function updateUI() {
    balanceEl.innerText = balance.toLocaleString();
    energyEl.innerText = energy;
    const energyPercent = (energy / maxEnergy) * 100;
    energyBar.style.width = `${energyPercent}%`;
}

// ৬. কয়েন ট্যাপ ইভেন্ট
coin.addEventListener('click', (e) => {
    if (energy > 0) {
        // লজিক: ব্যালেন্স বাড়ানো ও এনার্জি কমানো
        balance += 1;
        energy -= 1;
        tapsToSync += 1;
        updateUI();
        
        // ভাইব্রেট (মোবাইলে প্রিমিয়াম ফিল দিবে)
        if (tele.HapticFeedback) {
            tele.HapticFeedback.impactOccurred('medium');
        }

        // ট্যাপ অ্যানিমেশন (ফ্লোটিং নাম্বার)
        createClickAnimation(e);
    } else {
        // এনার্জি শেষ হলে কয়েন একটু লালচে হয়ে যাবে বা নড়বে
        coin.classList.add('no-energy');
        setTimeout(() => coin.classList.remove('no-energy'), 300);
    }
});

// ৭. ফ্লোটিং নাম্বার অ্যানিমেশন (+1)
function createClickAnimation(e) {
    const clickAnim = document.createElement('div');
    clickAnim.innerText = "+1";
    clickAnim.className = 'click-animation';
    clickAnim.style.left = `${e.clientX}px`;
    clickAnim.style.top = `${e.clientY}px`;
    document.body.appendChild(clickAnim);

    setTimeout(() => {
        clickAnim.remove();
    }, 1000);
}

// ৮. ডাটাবেসে সিঙ্ক করা (প্রতি ৩ সেকেন্ড পর পর একবার ডাটা সেভ হবে)
async function syncData() {
    if (tapsToSync > 0) {
        try {
            await fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    taps: tapsToSync,
                    energy: energy
                })
            });
            tapsToSync = 0; // সফলভাবে সেভ হলে জিরো করে দিবে
        } catch (err) {
            console.error("Sync failed:", err);
        }
    }
}

// ৯. এনার্জি রিফিল লজিক (প্রতি ১ সেকেন্ডে ১ করে বাড়বে)
setInterval(() => {
    if (energy < maxEnergy) {
        energy += 1;
        updateUI();
    }
}, 1000);

// ১০. সিঙ্ক ইন্টারভাল (প্রতি ৩ সেকেন্ডে সার্ভারে ডাটা পাঠাবে)
setInterval(syncData, 3000);

// শুরুতেই ডাটা লোড করা
fetchUserData();
