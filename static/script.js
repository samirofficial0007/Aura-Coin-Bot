// ১. টেলিগ্রাম ওয়েব অ্যাপ সেটআপ
const tele = window.Telegram.WebApp;
tele.expand();

const userId = tele.initDataUnsafe?.user?.id || 12345678;
const username = tele.initDataUnsafe?.user?.username || "Aura_Player";

// ২. গেম ভ্যারিয়েবলস
let balance = 0;
let energy = 1000;
let maxEnergy = 1000;
let userLevel = 1;
let tapsToSync = 0;

// ৩. DOM এলিমেন্ট সিলেকশন
const balanceEl = document.getElementById('balance');
const energyEl = document.getElementById('energy');
const energyBar = document.getElementById('energy-bar');
const coin = document.getElementById('coin');
const levelEl = document.getElementById('user-level'); // HTML এ এই আইডিটা থাকতে হবে
const tapValueEl = document.getElementById('tap-value'); // HTML এ এই আইডিটা থাকতে হবে

// ৪. ট্যাব নেভিগেশন লজিক
function showSection(sectionId) {
    // সব সেকশন হাইড করা
    document.querySelectorAll('.game-section').forEach(s => s.style.display = 'none');
    // টার্গেট সেকশন শো করা
    document.getElementById(sectionId).style.display = 'flex';
    
    // যদি লিডারবোর্ড বা টাস্ক সেকশন হয়, তবে ডাটা ফেচ করা
    if (sectionId === 'stats-section') fetchLeaderboard();
    if (sectionId === 'tasks-section') fetchTasks();
}

// ৫. ডাটাবেস থেকে ইউজারের তথ্য আনা
async function fetchUserData() {
    try {
        const response = await fetch(`/api/user/${userId}`);
        const data = await response.json();
        if (data.status === "success" || data.user_id) {
            balance = data.balance;
            energy = data.energy;
            maxEnergy = data.max_energy;
            userLevel = data.level || 1;
            updateUI();
        }
    } catch (err) {
        console.error("Fetch User Error:", err);
    }
}

// ৬. UI আপডেট করা
function updateUI() {
    balanceEl.innerText = Math.floor(balance).toLocaleString();
    energyEl.innerText = energy;
    if (levelEl) levelEl.innerText = `Level ${userLevel}`;
    if (tapValueEl) tapValueEl.innerText = `+${userLevel} / Tap`;
    
    const energyPercent = (energy / maxEnergy) * 100;
    energyBar.style.width = `${energyPercent}%`;
}

// ৭. কয়েন ট্যাপ ইভেন্ট (লেভেল অনুযায়ী পয়েন্ট বাড়বে)
coin.addEventListener('click', (e) => {
    if (energy >= userLevel) {
        // লজিক: ১ লেভেলে ১ পয়েন্ট, ২ লেভেলে ২ পয়েন্ট...
        balance += userLevel;
        energy -= userLevel;
        tapsToSync += 1; // এটা সার্ভারে ১টা রিকোয়েস্ট হিসেবে যাবে
        
        updateUI();
        if (tele.HapticFeedback) tele.HapticFeedback.impactOccurred('light');
        createClickAnimation(e, `+${userLevel}`);
    } else {
        coin.classList.add('no-energy');
        setTimeout(() => coin.classList.remove('no-energy'), 300);
    }
});

function createClickAnimation(e, text) {
    const anim = document.createElement('div');
    anim.innerText = text;
    anim.className = 'click-animation';
    anim.style.left = `${e.clientX}px`;
    anim.style.top = `${e.clientY}px`;
    document.body.appendChild(anim);
    setTimeout(() => anim.remove(), 800);
}

// ৮. লিডারবোর্ড (র‍্যাঙ্ক) ফেচ করা
async function fetchLeaderboard() {
    const listEl = document.getElementById('leaderboard-list');
    listEl.innerHTML = "<li>Loading Ranks...</li>";
    
    try {
        const response = await fetch(`/api/leaderboard?user_id=${userId}`);
        const data = await response.json();
        
        listEl.innerHTML = "";
        data.top_100.forEach(user => {
            const li = document.createElement('li');
            li.innerHTML = `
                <span class="rank">#${user.rank}</span>
                <span class="name">${user.username}</span>
                <span class="pts">${user.balance.toLocaleString()} $AURA</span>
            `;
            if (user.username === username) li.classList.add('me');
            listEl.appendChild(li);
        });
        
        document.getElementById('my-rank').innerText = `Your Rank: #${data.user_rank}`;
    } catch (err) {
        listEl.innerHTML = "<li>Failed to load leaderboard.</li>";
    }
}

// ৯. টাস্ক সিস্টেম
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
                <button onclick="claimTask('${task.id}', '${task.link}')">Go</button>
            `;
            taskList.appendChild(div);
        });
    } catch (err) { console.log(err); }
}

async function claimTask(taskId, link) {
    window.open(link, '_blank');
    // ৫ সেকেন্ড পর ক্লেইম রিকোয়েস্ট পাঠানো
    setTimeout(async () => {
        const res = await fetch('/api/task/claim', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({user_id: userId, task_id: taskId})
        });
        const data = await res.json();
        if (data.status === "success") {
            balance += data.reward;
            updateUI();
            alert(`Claimed ${data.reward} $AURA!`);
        }
    }, 5000);
}

// ১০. লেভেল বুস্ট / আপগ্রেড
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
            alert(`Upgraded to Level ${userLevel}!`);
        } else {
            alert(data.message);
        }
    } catch (err) { console.log(err); }
}

// ১১. ডাটা সিঙ্ক (প্রতি ৩ সেকেন্ডে)
async function syncData() {
    if (tapsToSync > 0) {
        try {
            await fetch('/api/sync', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    user_id: userId,
                    taps: tapsToSync,
                    energy: energy
                })
            });
            tapsToSync = 0;
        } catch (err) { console.error("Sync Error:", err); }
    }
}

// ইন্টারভাল সেটআপ
setInterval(() => {
    if (energy < maxEnergy) {
        energy += 3; // রিফিল স্পিড
        updateUI();
    }
}, 1000);

setInterval(syncData, 3000);

// ইনিশিয়াল লোড
fetchUserData();
