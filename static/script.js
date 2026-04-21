// ১. টেলিগ্রাম ওয়েব অ্যাপ সেটআপ
const tele = window.Telegram.WebApp;
tele.expand();

// ইউজার আইডি সংগ্রহ (টেলিগ্রাম থেকে না পেলে ডামি আইডি ব্যবহার করবে)
const userId = tele.initDataUnsafe?.user?.id || 12345678;
const username = tele.initDataUnsafe?.user?.username || "Aura_Player";

// ২. গেম ভ্যারিয়েবলস
let balance = 0;
let energy = 1000;
let maxEnergy = 1000;
let userLevel = 1;
let tapsToSync = 0;
let isSyncing = false; // ডুপ্লিকেট সিঙ্ক রোধ করতে

// ৩. DOM এলিমেন্ট সিলেকশন
const balanceEl = document.getElementById('balance');
const energyEl = document.getElementById('energy');
const energyBar = document.getElementById('energy-bar');
const coin = document.getElementById('coin');
const levelEl = document.getElementById('user-level');
const tapValueEl = document.getElementById('tap-value');

// ৪. ট্যাব নেভিগেশন (Stats বদলে Leaderboard করা হয়েছে)
function showSection(sectionId) {
    document.querySelectorAll('.game-section').forEach(s => s.style.display = 'none');
    document.getElementById(sectionId).style.display = 'flex';
    
    // সেকশন অনুযায়ী ডাটা লোড
    if (sectionId === 'stats-section') fetchLeaderboard();
    if (sectionId === 'tasks-section') fetchTasks();
    
    // ভাইব্রেশন ফিডব্যাক
    if (tele.HapticFeedback) tele.HapticFeedback.impactOccurred('light');
}

// ৫. ডাটাবেস থেকে ইউজারের তথ্য আনা (সবচেয়ে গুরুত্বপূর্ণ)
async function fetchUserData() {
    try {
        const response = await fetch(`/api/user/${userId}`);
        const data = await response.json();
        
        if (data.status === "success" || data.balance !== undefined) {
            balance = data.balance;
            energy = data.energy;
            maxEnergy = data.max_energy;
            userLevel = data.level || 1;
            updateUI();
            console.log("User Data Loaded:", data);
        }
    } catch (err) {
        console.error("User Fetch Error:", err);
    }
}

// ৬. UI আপডেট করা
function updateUI() {
    if (balanceEl) balanceEl.innerText = Math.floor(balance).toLocaleString();
    if (energyEl) energyEl.innerText = energy;
    if (levelEl) levelEl.innerText = `Level ${userLevel}`;
    if (tapValueEl) tapValueEl.innerText = `+${userLevel} / Tap`;
    
    const energyPercent = (energy / maxEnergy) * 100;
    if (energyBar) energyBar.style.width = `${energyPercent}%`;
}

// ৭. কয়েন ট্যাপ ইভেন্ট
coin.addEventListener('click', (e) => {
    if (energy >= userLevel) {
        // লেভেল অনুযায়ী ব্যালেন্স বাড়ানো
        balance += userLevel;
        energy -= userLevel;
        tapsToSync += 1; // এটা সার্ভারে ট্যাপের সংখ্যা পাঠাবে
        
        updateUI();
        
        // ভাইব্রেশন ইফেক্ট
        if (tele.HapticFeedback) tele.HapticFeedback.impactOccurred('medium');
        
        // ট্যাপ অ্যানিমেশন
        createClickAnimation(e, `+${userLevel}`);
    } else {
        // এনার্জি না থাকলে কয়েন কাঁপবে
        coin.classList.add('no-energy');
        setTimeout(() => coin.classList.remove('no-energy'), 300);
    }
});

function createClickAnimation(e, text) {
    const anim = document.createElement('div');
    anim.innerText = text;
    anim.className = 'click-animation';
    // মাউস বা ট্যাপের পজিশন অনুযায়ী অ্যানিমেশন
    anim.style.left = `${e.clientX}px`;
    anim.style.top = `${e.clientY}px`;
    document.body.appendChild(anim);
    setTimeout(() => anim.remove(), 800);
}

// ৮. কয়েন সেভ করা (Sync Logic) - এটা এখন আরও মজবুত
async function syncData() {
    if (tapsToSync > 0 && !isSyncing) {
        isSyncing = true;
        const currentTaps = tapsToSync; // ব্যাকআপ রাখা
        
        try {
            const response = await fetch('/api/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_id: userId,
                    taps: currentTaps,
                    energy: energy
                })
            });
            
            const result = await response.json();
            if (result.status === "success") {
                tapsToSync -= currentTaps; // সফল হলে ট্যাপ কাউন্ট কমানো
                console.log("Coins Synced Successfully!");
            }
        } catch (err) {
            console.error("Sync Failed:", err);
        } finally {
            isSyncing = false;
        }
    }
}

// ৯. লিডারবোর্ড সিস্টেম
async function fetchLeaderboard() {
    const listEl = document.getElementById('leaderboard-list');
    listEl.innerHTML = "<li style='justify-content:center;'>Loading Leaderboard...</li>";
    
    try {
        const response = await fetch(`/api/leaderboard?user_id=${userId}`);
        const data = await response.json();
        
        listEl.innerHTML = "";
        data.top_100.forEach(user => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="rank">#${user.rank}</span>
                <span class="name">${user.username}</span>
                <span class="pts">${user.balance.toLocaleString()}</span>
            `;
            // নিজের আইডি হলে হাইলাইট করা
            if (user.username === username) li.classList.add('me');
            listEl.appendChild(li);
        });
        
        const myRankEl = document.getElementById('my-rank');
        if (myRankEl) myRankEl.innerText = `Your Position: #${data.user_rank}`;
    } catch (err) {
        listEl.innerHTML = "<li>Error loading rankings.</li>";
    }
}

// ১০. টাস্ক সিস্টেম
async function fetchTasks() {
    const taskList = document.getElementById('task-list');
    try {
        const response = await fetch('/api/tasks');
        const tasks = await response.json();
        
        taskList.innerHTML = "";
        tasks.forEach(task => {
            const div = document.createElement('div');
            div.className = 'task-item';
            div.innerHTML = `
                <span>${task.icon} ${task.title} (+${task.reward})</span>
                <button onclick="claimTask('${task.id}', '${task.link}')">Join</button>
            `;
            taskList.appendChild(div);
        });
    } catch (err) { console.log("Task Error:", err); }
}

async function claimTask(taskId, link) {
    window.open(link, '_blank');
    // ৫ সেকেন্ড পর রিওয়ার্ড চেক
    setTimeout(async () => {
        try {
            const res = await fetch('/api/task/claim', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({user_id: userId, task_id: taskId})
            });
            const data = await res.json();
            if (data.status === "success") {
                balance += data.reward;
                updateUI();
                alert(`Reward Claimed: ${data.reward} $AURA!`);
            }
        } catch (err) { console.log(err); }
    }, 5000);
}

// ১১. লেভেল আপগ্রেড
async function upgradeLevel() {
    try {
        const res = await fetch('/api/upgrade', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: userId})
        });
        const data = await res.json();
        
        if (data.status === "success") {
            userLevel = data.new_level;
            balance -= data.cost;
            updateUI();
            alert(`Boom! You are now Level ${userLevel}`);
        } else {
            alert("Not enough $AURA!");
        }
    } catch (err) { console.log("Upgrade Error:", err); }
}

// ১২. টাইম-বেসড ইন্টারভালস
// এনার্জি রিফিল (প্রতি সেকেন্ডে ৩ করে)
setInterval(() => {
    if (energy < maxEnergy) {
        energy = Math.min(maxEnergy, energy + 3);
        updateUI();
    }
}, 1000);

// ডাটা সিঙ্ক (প্রতি ৩ সেকেন্ডে সার্ভারে ডাটা পাঠাবে)
setInterval(syncData, 3000);

// শুরুতে সব ডাটা লোড করা
fetchUserData();
