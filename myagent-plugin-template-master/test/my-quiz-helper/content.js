// content script：自动检测页面上的题目文本，调用 background -> AI，注入悬浮答案面板
(function () {
    // 配置（可微调）
    const DEBOUNCE_MS = 700;
    const MIN_QUESTION_LENGTH = 6;
    const MAX_QUESTION_LENGTH = 2000;
  
    // 已经注入的 panel id
    const PANEL_ID = 'quiz-helper-panel-v1';
  
    // 1) 题目抽取器：尝试按优先级找到页面上潜在题目
    function extractCandidateQuestions() {
      const results = [];
  
      // 常见选择器尝试（你可以根据目标站点扩展）
      const selectors = [
        '[class*=question]',
        '[id*=question]',
        '.qtext',
        '.question-text',
        '.problem',
        '.stem',
        'article',
        '.question',
        '.content'
      ];
  
      // 先根据 selectors 搜索并挑选明显较短/合理文本块
      selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
          const txt = cleanText(el.innerText || '');
          if (isReasonableQuestion(txt)) results.push({ el, text: txt });
        });
      });
  
      // 再用常规思路：寻找 form label / legend / strong/p 标签等
      document.querySelectorAll('label, legend, h1, h2, h3, p').forEach(el => {
        const txt = cleanText(el.innerText || '');
        if (isReasonableQuestion(txt)) results.push({ el, text: txt });
      });
  
      // 去重（按文本）
      const map = new Map();
      results.forEach(r => { if (!map.has(r.text)) map.set(r.text, r); });
      return Array.from(map.values());
    }
  
    function cleanText(s) {
      return s.replace(/\s+/g,' ').trim();
    }
  
    function isReasonableQuestion(s) {
      if (!s) return false;
      if (s.length < MIN_QUESTION_LENGTH) return false;
      if (s.length > MAX_QUESTION_LENGTH) return false;
      // 过滤掉太长的整页文本
      if (s.split(/\n/).length > 40) return false;
      // 排除包含“广告”“cookie”等无关词的块
      if (/cookie|advert|login|subscribe/i.test(s)) return false;
      return true;
    }
  
    // 2) 创建/更新面板
    function createOrUpdatePanel(targetEl, questionText, answerHtml) {
      let panel = document.getElementById(PANEL_ID);
      if (!panel) {
        panel = document.createElement('div');
        panel.id = PANEL_ID;
        panel.style.position = 'absolute';
        panel.style.zIndex = 999999;
        panel.style.maxWidth = '520px';
        panel.style.boxShadow = '0 6px 18px rgba(0,0,0,0.2)';
        panel.style.borderRadius = '8px';
        panel.style.background = '#fff';
        panel.style.padding = '10px';
        panel.style.fontSize = '13px';
        panel.style.color = '#111';
        panel.style.border = '1px solid rgba(0,0,0,0.08)';
        panel.style.transition = 'opacity 160ms ease';
        panel.style.opacity = '0';
        panel.style.backdropFilter = 'blur(4px)';
        document.body.appendChild(panel);
        // close on outside click
        document.addEventListener('click', (e) => {
          if (!panel.contains(e.target)) {
            panel.style.opacity = '0';
            setTimeout(()=> panel.remove && panel.remove(), 200);
          }
        }, true);
      }
  
      panel.innerHTML = `
        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
          <div style="font-weight:700; margin-bottom:6px;">AI 推荐答案</div>
          <div style="font-size:12px; color:#666;">由你的 AI 接口生成</div>
        </div>
        <div style="margin:6px 0; max-height:240px; overflow:auto;" id="${PANEL_ID}-content">${answerHtml}</div>
        <div style="display:flex; gap:8px; margin-top:8px;">
          <button id="${PANEL_ID}-copy">复制答案</button>
          <button id="${PANEL_ID}-insert">填写到可编辑字段</button>
          <button id="${PANEL_ID}-close">关闭</button>
        </div>
        <div style="font-size:11px; color:#666; margin-top:8px;">提示：请先核对再提交，避免违规使用。</div>
      `;
  
      // attach events
      panel.querySelector(`#${PANEL_ID}-close`).addEventListener('click', () => {
        panel.remove();
      });
      panel.querySelector(`#${PANEL_ID}-copy`).addEventListener('click', () => {
        const content = panel.querySelector(`#${PANEL_ID}-content`).innerText;
        navigator.clipboard.writeText(content).then(()=> {
          flashPanel(panel, '复制成功');
        }).catch(()=> {
          flashPanel(panel, '复制失败');
        });
      });
      panel.querySelector(`#${PANEL_ID}-insert`).addEventListener('click', () => {
        // 将答案尝试填到页面第一个可编辑输入或 textarea 或 contenteditable
        const content = panel.querySelector(`#${PANEL_ID}-content`).innerText;
        const success = tryFillEditable(content, targetEl);
        flashPanel(panel, success ? '已填写到第一个可编辑字段' : '未找到可填写字段，请手动粘贴');
      });
  
      // position near targetEl (bounding box)
      try {
        const rect = targetEl.getBoundingClientRect();
        const top = window.scrollY + rect.top;
        const left = window.scrollX + rect.right + 8; // 放在右侧
        panel.style.top = `${top}px`;
        panel.style.left = `${left}px`;
        panel.style.opacity = '1';
      } catch (e) {
        // fallback 中央
        panel.style.top = `${window.scrollY + 100}px`;
        panel.style.left = `${window.scrollX + 20}px`;
        panel.style.opacity = '1';
      }
    }
  
    function flashPanel(panel, text) {
      const el = document.createElement('div');
      el.textContent = text;
      el.style.position = 'absolute';
      el.style.right = '10px';
      el.style.top = '-26px';
      el.style.background = '#222';
      el.style.color = '#fff';
      el.style.padding = '4px 8px';
      el.style.borderRadius = '6px';
      el.style.fontSize = '12px';
      panel.appendChild(el);
      setTimeout(()=> el.remove(), 1500);
    }
  
    function tryFillEditable(text, contextEl) {
      // 优先在 contextEl 内找输入框
      const candidates = [];
      if (contextEl) {
        candidates.push(...contextEl.querySelectorAll('input[type="text"], textarea, [contenteditable="true"]'));
        candidates.push(...contextEl.querySelectorAll('input:not([type])'));
      }
      // 再全页面查找
      if (candidates.length === 0) {
        candidates.push(...document.querySelectorAll('input[type="text"], textarea, [contenteditable="true"], input:not([type])'));
      }
      for (const el of candidates) {
        try {
          if (el.contentEditable === 'true') {
            el.focus();
            document.execCommand('selectAll', false, null);
            document.execCommand('insertText', false, text);
            return true;
          } else if (el.tagName === 'TEXTAREA' || el.tagName === 'INPUT') {
            el.focus();
            el.value = text;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return true;
          }
        } catch (e) {
          // continue
        }
      }
      return false;
    }
  
    // 3) 与 background 通信的封装
    function askAi(question) {
      return new Promise((resolve, reject) => {
        chrome.runtime.sendMessage({ type: 'askAi', question }, (resp) => {
          if (!resp) return reject(new Error('没有收到 background 响应（可能权限问题）'));
          if (!resp.ok) return reject(new Error(resp.error || 'AI 请求失败'));
          resolve(resp.result);
        });
      });
    }
  
    // 4) 主逻辑：观察 DOM，抽取题目，去重，调用 AI
    let lastSentQuestions = new Set();
    let debounceTimer = null;
  
    function processPage() {
      if (debounceTimer) clearTimeout(debounceTimer);
      debounceTimer = setTimeout(async () => {
        try {
          const cands = extractCandidateQuestions();
          if (cands.length === 0) return;
          // 对每个候选：若未发送过，则触发
          for (const cand of cands.slice(0,5)) { // 限制每次最多处理几个候选
            if (lastSentQuestions.has(cand.text)) continue;
            // 标记为已发送以防重复短时间内重复请求
            lastSentQuestions.add(cand.text);
            // 触发 AI 查询（可在后续加队列/节流）
            try {
              // 临时在面板中放置 “正在获取答案...” 提示
              createOrUpdatePanel(cand.el, cand.text, '<i>正在获取答案…</i>');
              const aiResp = await askAi(cand.text);
              // 若 aiResp 是 object，尝试提取常见字段
              let answerHtml = '';
              if (typeof aiResp === 'string') {
                answerHtml = `<pre style="white-space:pre-wrap;">${escapeHtml(aiResp)}</pre>`;
              } else if (aiResp.answer) {
                answerHtml = `<pre style="white-space:pre-wrap;">${escapeHtml(aiResp.answer)}</pre>`;
              } else {
                // fallback: stringify
                answerHtml = `<pre style="white-space:pre-wrap;">${escapeHtml(JSON.stringify(aiResp, null, 2))}</pre>`;
              }
              createOrUpdatePanel(cand.el, cand.text, answerHtml);
            } catch (err) {
              createOrUpdatePanel(cand.el, cand.text, `<div style="color:#b00">调用 AI 接口失败：${escapeHtml(String(err))}</div>`);
            }
          }
  
          // 清理 lastSentQuestions（防止内存无限增长）——保留最近 200 条
          if (lastSentQuestions.size > 200) {
            const arr = Array.from(lastSentQuestions);
            lastSentQuestions = new Set(arr.slice(arr.length - 100));
          }
        } catch (e) {
          console.error('processPage error', e);
        }
      }, DEBOUNCE_MS);
    }
  
    // 辅助：转义 HTML
    function escapeHtml(s) {
      return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":"&#39;"}[m]));
    }
  
    // 观察 DOM 变化：题目往往是动态加载的（例如 SPA）
    const observer = new MutationObserver(() => processPage());
    observer.observe(document, { childList: true, subtree: true, characterData: true });
  
    // 初次运行
    processPage();
  
  })();
  