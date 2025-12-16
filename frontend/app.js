/**
 * VFS Visa Checker - Frontend Application
 */

let ws = null;
let isScanning = false;
let startTime = null;
let uptimeInterval = null;
let checkCount = 0;
let foundCount = 0;
let errorCount = 0;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    connectWebSocket();
    setupOTPInputs();
    loadSavedConfig();
});

// WebSocket Connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
    
    ws.onopen = () => {
        updateStatus('connected', 'Bağlandı');
        addLog('success', 'WebSocket bağlantısı kuruldu');
    };
    
    ws.onclose = () => {
        updateStatus('disconnected', 'Bağlantı kesildi');
        setTimeout(connectWebSocket, 3000);
    };
    
    ws.onerror = () => {
        updateStatus('error', 'Bağlantı hatası');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };
}

function handleMessage(data) {
    switch(data.type) {
        case 'log':
            addLog(data.data.level, data.data.message);
            if (data.data.level === 'error') errorCount++;
            break;
        case 'otp_required':
            showOTPModal();
            break;
        case 'appointment_found':
            foundCount++;
            document.getElementById('foundCount').textContent = foundCount;
            showToast('success', 'Randevu bulundu!');
            playNotificationSound();
            break;
        case 'stats_update':
            if (data.data.check_count) {
                checkCount = data.data.check_count;
                document.getElementById('checkCount').textContent = checkCount;
            }
            break;
    }
    document.getElementById('errorCount').textContent = errorCount;
}

// Scanning Controls
async function startScan() {
    const config = {
        email: document.getElementById('email').value,
        password: document.getElementById('password').value,
        country_code: document.getElementById('country').value,
        mission_code: document.getElementById('mission').value,
        center_code: document.getElementById('center').value,
        check_interval: parseInt(document.getElementById('interval').value)
    };
    
    if (!config.email || !config.password) {
        showToast('error', 'Email ve şifre gerekli');
        return;
    }
    
    saveConfig(config);
    
    try {
        const response = await fetch('/api/scan/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            isScanning = true;
            startTime = Date.now();
            startUptimeTimer();
            updateButtons();
            showToast('success', 'Tarama başlatıldı');
        } else {
            const error = await response.json();
            showToast('error', error.detail);
        }
    } catch (e) {
        showToast('error', 'Bağlantı hatası');
    }
}

async function stopScan() {
    try {
        const response = await fetch('/api/scan/stop', {method: 'POST'});
        if (response.ok) {
            isScanning = false;
            stopUptimeTimer();
            updateButtons();
            showToast('info', 'Tarama durduruldu');
        }
    } catch (e) {
        showToast('error', 'Durdurma hatası');
    }
}

function updateButtons() {
    document.getElementById('startBtn').style.display = isScanning ? 'none' : 'block';
    document.getElementById('stopBtn').style.display = isScanning ? 'block' : 'none';
}

// Timer
function startUptimeTimer() {
    uptimeInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        const mins = Math.floor(elapsed / 60).toString().padStart(2, '0');
        const secs = (elapsed % 60).toString().padStart(2, '0');
        document.getElementById('uptime').textContent = `${mins}:${secs}`;
    }, 1000);
}

function stopUptimeTimer() {
    if (uptimeInterval) clearInterval(uptimeInterval);
}

// Status
function updateStatus(status, text) {
    const dot = document.getElementById('statusDot');
    dot.className = 'status-dot';
    if (status === 'connected') dot.classList.add('active');
    else if (status === 'error') dot.classList.add('error');
    else dot.classList.add('inactive');
    document.getElementById('statusText').textContent = text;
}

// Logging
function addLog(level, message) {
    const container = document.getElementById('logContainer');
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="log-time">${time}</span>
        <span class="log-level ${level}">${level.toUpperCase()}</span>
        <span class="log-message">${message}</span>
    `;
    container.appendChild(entry);
    container.scrollTop = container.scrollHeight;
}

function clearLogs() {
    document.getElementById('logContainer').innerHTML = '';
}

// OTP Modal
function setupOTPInputs() {
    const inputs = document.querySelectorAll('.otp-digit');
    inputs.forEach((input, index) => {
        input.addEventListener('input', (e) => {
            if (e.target.value && index < inputs.length - 1) {
                inputs[index + 1].focus();
            }
        });
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !e.target.value && index > 0) {
                inputs[index - 1].focus();
            }
        });
    });
}

function showOTPModal() {
    document.getElementById('otpModal').classList.add('active');
    document.querySelector('.otp-digit').focus();
}

function hideOTPModal() {
    document.getElementById('otpModal').classList.remove('active');
    document.querySelectorAll('.otp-digit').forEach(i => i.value = '');
}

async function submitOTP() {
    const inputs = document.querySelectorAll('.otp-digit');
    const otp = Array.from(inputs).map(i => i.value).join('');
    
    if (otp.length !== 6) {
        showToast('error', '6 haneli kod girin');
        return;
    }
    
    try {
        await fetch('/api/otp/submit', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({otp_code: otp})
        });
        hideOTPModal();
        showToast('success', 'OTP gönderildi');
    } catch (e) {
        showToast('error', 'OTP gönderilemedi');
    }
}

// Toast Notifications
function showToast(type, message) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.remove(), 4000);
}

// Sound
function playNotificationSound() {
    const audio = new Audio('data:audio/wav;base64,UklGRl9vT19XQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YU');
    audio.play().catch(() => {});
}

// Config Storage
function saveConfig(config) {
    localStorage.setItem('vfs_config', JSON.stringify({
        email: config.email,
        country_code: config.country_code,
        mission_code: config.mission_code,
        center_code: config.center_code,
        check_interval: config.check_interval
    }));
}

function loadSavedConfig() {
    const saved = localStorage.getItem('vfs_config');
    if (saved) {
        const config = JSON.parse(saved);
        if (config.email) document.getElementById('email').value = config.email;
        if (config.country_code) document.getElementById('country').value = config.country_code;
        if (config.mission_code) document.getElementById('mission').value = config.mission_code;
        if (config.center_code) document.getElementById('center').value = config.center_code;
        if (config.check_interval) document.getElementById('interval').value = config.check_interval;
    }
}