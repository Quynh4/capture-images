// debug_page.js — Paste vào DevTools Console để kiểm tra
// Chạy file này trong Console của trang cần chụp để xem extension thấy gì

(function debugPageLabel() {
  console.group('[AutoCapture Debug]');

  // Test 1: regex trên tất cả <p>
  const allP = document.querySelectorAll('p');
  console.log(`Tổng số thẻ <p>: ${allP.length}`);
  const matches = [];
  for (const p of allP) {
    const txt = p.textContent.trim();
    if (/^\d+\s*\/\s*\d+$/.test(txt)) {
      matches.push({ txt, el: p });
      console.log('✅ Tìm thấy thẻ phù hợp:', txt, p);
    }
  }
  if (matches.length === 0) {
    console.warn('❌ Không tìm thấy thẻ <p> nào có dạng "N / N"');
    // Show all p content for debugging
    console.log('Tất cả <p> content:');
    allP.forEach((p, i) => {
      if (p.textContent.trim()) console.log(`  [${i}]`, JSON.stringify(p.textContent.trim()), p.className);
    });
  }

  // Test 2: class*="bottom"
  const bottomEls = document.querySelectorAll('[class*="bottom"]');
  console.log(`Thẻ có class "bottom": ${bottomEls.length}`);
  bottomEls.forEach(el => {
    const txt = el.textContent.trim();
    console.log(`  <${el.tagName.toLowerCase()}>`, JSON.stringify(txt), el.className.slice(0, 80));
  });

  // Test 3: nút Next
  const nextBtn = document.querySelector('button[aria-label="次のページ"]');
  if (nextBtn) {
    console.log('✅ Nút Next tìm thấy:', { disabled: nextBtn.disabled, class: nextBtn.className });
  } else {
    console.warn('❌ Không tìm thấy nút Next [aria-label="次のページ"]');
    // List all buttons
    const btns = document.querySelectorAll('button');
    console.log(`Tổng số button: ${btns.length}`);
    btns.forEach((b, i) => {
      console.log(`  [${i}] aria-label="${b.getAttribute('aria-label')}" text="${b.textContent.trim().slice(0,30)}"`);
    });
  }

  console.groupEnd();
})();
