// background.js — Service Worker (v1)

let state = {
  running: false,
  count: 0,
  tabId: null,
  windowId: null
};

function broadcast(msg) {
  chrome.runtime.sendMessage(msg).catch(() => {});
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === 'GET_STATE') {
    sendResponse({ running: state.running, count: state.count });
    return true;
  }
  if (msg.type === 'STOP') {
    state.running = false;
    return;
  }
  if (msg.type === 'START') {
    state.running  = true;
    state.count    = 0;
    state.tabId    = msg.tabId;
    state.windowId = msg.windowId;
    runCapture(msg.tabId, msg.delay);
    return;
  }
});

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

async function runInPage(tabId, func, args = []) {
  try {
    const results = await chrome.scripting.executeScript({
      target: { tabId },
      func,
      args
    });
    return results?.[0]?.result ?? null;
  } catch (e) {
    console.error('[runInPage error]', e.message);
    return null;
  }
}

// Find "N / N" label — regex only, no complex CSS selectors
function getPageLabelFn() {
  const allP = document.querySelectorAll('p');
  for (const p of allP) {
    const txt = p.textContent.trim();
    if (/^\d+\s*\/\s*\d+$/.test(txt)) return txt;
  }
  // Wider fallback: any element
  const all = document.querySelectorAll('[class*="bottom"]');
  for (const el of all) {
    const txt = el.textContent.trim();
    if (/^\d+\s*\/\s*\d+$/.test(txt)) return txt;
  }
  return null;
}

async function waitForLabelChange(tabId, oldLabel, delaySec) {
  const maxMs = Math.max(delaySec * 1000 + 4000, 6000);
  const start = Date.now();

  while (Date.now() - start < maxMs) {
    if (!state.running) return false;
    await sleep(300);

    const newLabel = await runInPage(tabId, getPageLabelFn);
    if (newLabel && newLabel !== oldLabel) {
      await sleep(500); // let content finish rendering
      return true;
    }
  }
  return false;
}

async function runCapture(tabId, delay) {
  const MAX = 500;
  let loop = 0;

  while (state.running && loop < MAX) {
    loop++;

    // 1. Get page label
    const pageLabel = await runInPage(tabId, getPageLabelFn);

    if (!pageLabel) {
      state.running = false;
      broadcast({
        type: 'FINISHED',
        text: '❌ Không tìm thấy thẻ số trang (N / N). Hãy chắc chắn đang ở đúng trang.'
      });
      return;
    }

    // Safe filename: "3 / 10" → "3_10"
    const safeName = pageLabel.replace(/\s*\/\s*/g, '_').replace(/[^\w\-]/g, '');

    broadcast({
      type: 'STATUS_UPDATE',
      text: `📸 Chụp trang ${pageLabel}...`,
      state: 'running',
      count: state.count
    });

    // 2. Capture screenshot
    let dataUrl;
    try {
      dataUrl = await chrome.tabs.captureVisibleTab(state.windowId, { format: 'png' });
    } catch (e) {
      try {
        // Fallback: no windowId
        dataUrl = await chrome.tabs.captureVisibleTab(undefined, { format: 'png' });
      } catch (e2) {
        state.running = false;
        broadcast({
          type: 'FINISHED',
          text: `❌ Lỗi chụp màn hình: ${e2.message}`
        });
        return;
      }
    }

    // 3. Download PNG
    await chrome.downloads.download({
      url: dataUrl,
      filename: `captures/${safeName}.png`,
      saveAs: false
    });

    state.count++;
    broadcast({
      type: 'STATUS_UPDATE',
      text: `✓ Đã lưu trang ${pageLabel}`,
      state: 'running',
      count: state.count
    });

    // 4. Check if Next is disabled (last page)
    const nextInfo = await runInPage(tabId, () => {
      const btn = document.querySelector('button[aria-label="次のページ"]');
      if (!btn) return { found: false };
      return { found: true, disabled: btn.disabled || btn.getAttribute('disabled') !== null };
    });

    if (!nextInfo?.found || nextInfo.disabled) {
      state.running = false;
      broadcast({
        type: 'FINISHED',
        text: `✅ Hoàn thành! Đã chụp ${state.count} ảnh vào Downloads/captures/`
      });
      return;
    }

    // 5. Click Next
    await runInPage(tabId, () => {
      const btn = document.querySelector('button[aria-label="次のページ"]');
      if (btn) btn.click();
    });

    // 6. Wait for page label to change
    const changed = await waitForLabelChange(tabId, pageLabel, delay);
    if (!changed || !state.running) {
      state.running = false;
      broadcast({
        type: 'FINISHED',
        text: `✅ Xong! Đã chụp ${state.count} ảnh.`
      });
      return;
    }
  }

  state.running = false;
  broadcast({
    type: 'FINISHED',
    text: `✅ Hoàn thành! Đã chụp ${state.count} ảnh.`
  });
}
