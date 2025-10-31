// background.js (已适配 DashScope OpenAI-compatible chat/completions)
// 可选方式：将 API Key / base url 放入 chrome.storage.sync（推荐），若未填则使用下面的 FALLBACK 常量。

const FALLBACK_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"; // 你给的 Base URL（中国北京区）
const FALLBACK_MODEL = "qwen3-max"; // 你要使用的模型名
const FALLBACK_API_KEY = "sk-57e009fff2f04016bb0fe40de83ade89"; // 你给的 API Key（注意安全风险）

// background service worker listener：接收 content script 的消息，调用 DashScope/OpenAI-compatible API 并返回结果
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'askAi') {
    handleAskAi(message.question).then(result => {
      sendResponse({ ok: true, result });
    }).catch(err => {
      console.error('AI 请求失败', err);
      sendResponse({ ok: false, error: String(err) });
    });
    return true; // 表示异步 sendResponse
  }
});

async function handleAskAi(question) {
  // 读取用户配置（优先）
  const cfg = await getStorage(['apiUrl','apiKey','payloadTemplate','model']);
  const baseUrl = (cfg.apiUrl && cfg.apiUrl.trim()) ? cfg.apiUrl.trim() : FALLBACK_BASE_URL;
  const apiKey = (cfg.apiKey && cfg.apiKey.trim()) ? cfg.apiKey.trim() : FALLBACK_API_KEY;
  const model = (cfg.model && cfg.model.trim()) ? cfg.model.trim() : FALLBACK_MODEL;

  if (!baseUrl) throw new Error('未配置 Base URL（请在扩展设置中填写）');
  if (!apiKey) throw new Error('未配置 API Key（请在扩展设置中填写）');

  // 构建请求 body（遵循 OpenAI-compatible chat/completions）
  const messages = [
    { role: "system", content: "You are a helpful assistant. Answer concisely and clearly." },
    { role: "user", content: question }
  ];

  // 如果用户在 popup 配置了 payloadTemplate（JSON 模板），优先使用其解析（带 {{question}} 占位替换）
  let requestBody = { model, messages };

  if (cfg.payloadTemplate && cfg.payloadTemplate.trim()) {
    // 简单模板替换：将 {{question}} 替换为 question 的 JSON 字符串值
    try {
      const replaced = cfg.payloadTemplate.replace(/\{\{\s*question\s*\}\}/g, question);
      // 允许用户在模板里保留其他字段（例如 "extra_body": {...}），我们尝试解析 JSON
      const parsed = JSON.parse(replaced);
      // 如果用户在模板里提供 messages / model 等，则使用用户指定的字段；否则回退到默认
      requestBody = Object.assign({}, requestBody, parsed);
    } catch (e) {
      // 解析失败：继续使用默认 body（但提示错误）
      console.warn('payloadTemplate 解析失败，已忽略 template（请确认为有效 JSON 且含 {{question}} 占位）', e);
    }
  }

  const url = baseUrl.replace(/\/+$/, '') + '/chat/completions';

  const headers = {
    'Content-Type': 'application/json',
    // 按阿里 DashScope OpenAI-compatible 文档：使用 Authorization Bearer
    'Authorization': `Bearer ${apiKey}`
    // 若你的 DashScope service 要求其他头，可在 popup 中扩展支持（例如 X-DashScope-API-Key），此处仅使用 Bearer。
  };

  const resp = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(requestBody),
  });

  if (!resp.ok) {
    const text = await resp.text().catch(()=> '');
    throw new Error(`请求失败：${resp.status} ${resp.statusText} ${text ? '- ' + text : ''}`);
  }

  const contentType = (resp.headers.get('content-type') || '');
  let data;
  if (contentType.includes('application/json')) {
    data = await resp.json();
  } else {
    data = await resp.text();
    return data; // 非 JSON 情况直接返回文本
  }

  // OpenAI-compatible 返回格式解析：choices[0].message.content
  try {
    if (data.choices && data.choices.length > 0) {
      // 可能多条 choices，优先取第一个
      const ch = data.choices[0];
      // 有些实现把 message 放在 choices[0].message；也有可能是 choices[0].text（兼容 older）
      const content = (ch.message && (ch.message.content || (typeof ch.message === 'string' ? ch.message : null)))
                    || ch.text
                    || (typeof ch === 'string' ? ch : null);
      if (content === null || content === undefined) {
        // 作为 fallback 返回整个 choices
        return data;
      }
      return content;
    } else if (data.output_text) {
      // 某些兼容层返回 output_text
      return data.output_text;
    } else {
      // fallback：返回完整响应对象
      return data;
    }
  } catch (e) {
    // 解析异常 -> 返回整个对象以便 content script 做展示
    return data;
  }
}

function getStorage(keys) {
  return new Promise(resolve => chrome.storage.sync.get(keys, resolve));
}
