// popup.js (v1)
const mainBtn      = document.getElementById('mainBtn');
const statusDot    = document.getElementById('statusDot');
const statusText   = document.getElementById('statusText');
const counterRow   = document.getElementById('counterRow');
const captureCount = document.getElementById('captureCount');
const delayInput   = document.getElementById('delayInput');

let isRunning = false;

function setStatus(text, type = 'idle') {
  statusText.className = 'status-text ' + type;
  statusText.textContent = text;
  statusDot.className = 'dot ' + (type === 'running' ? 'active' : '');
}

function setCount(n) {
  counterRow.style.display = 'flex';
  captureCount.textContent = n;
}

function setUiStopped() {
  isRunning = false;
  mainBtn.textContent = '▶ Bắt đầu';
  mainBtn.classList.remove('running');
  delayInput.disabled = false;
}

// Load saved delay
chrome.storage.local.get(['delay'], (data) => {
  if (data.delay) delayInput.value = data.delay;
});
delayInput.addEventListener('change', () => {
  chrome.storage.local.set({ delay: delayInput.value });
});

// Sync state on popup open
chrome.runtime.sendMessage({ type: 'GET_STATE' }, (resp) => {
  if (chrome.runtime.lastError) return;
  if (resp && resp.running) {
    isRunning = true;
    mainBtn.textContent = '⏹ Dừng lại';
    mainBtn.classList.add('running');
    delayInput.disabled = true;
    setStatus('Đang chạy...', 'running');
    if (resp.count) setCount(resp.count);
    counterRow.style.display = 'flex';
  }
});

// Listen for background messages
chrome.runtime.onMessage.addListener((msg) => {
  if (msg.type === 'STATUS_UPDATE') {
    setStatus(msg.text, msg.state || 'running');
    if (msg.count !== undefined) setCount(msg.count);
  }
  if (msg.type === 'FINISHED') {
    setUiStopped();
    setStatus(msg.text || 'Hoàn thành!', 'done');
  }
  if (msg.type === 'ERROR') {
    setUiStopped();
    setStatus('Lỗi: ' + msg.text, 'error');
  }
});

// Main button
mainBtn.addEventListener('click', async () => {
  if (isRunning) {
    chrome.runtime.sendMessage({ type: 'STOP' });
    setUiStopped();
    setStatus('Đã dừng.', 'idle');
    return;
  }

  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) {
    setStatus('Không tìm thấy tab!', 'error');
    return;
  }

  const delay = parseFloat(delayInput.value) || 2;
  isRunning = true;
  mainBtn.textContent = '⏹ Dừng lại';
  mainBtn.classList.add('running');
  delayInput.disabled = true;
  counterRow.style.display = 'flex';
  captureCount.textContent = '0';
  setStatus('Đang khởi động...', 'running');

  chrome.runtime.sendMessage({
    type: 'START',
    tabId: tab.id,
    windowId: tab.windowId,
    delay
  });
});
