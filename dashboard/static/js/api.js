function toast(msg, kind) {
  const root = document.getElementById('toast-root');
  if (!root) return;
  const el = document.createElement('div');
  el.className = 'toast' + (kind ? ' ' + kind : '');
  el.textContent = msg;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3400);
}

async function api(path, opts) {
  opts = opts || {};
  const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  let res;
  try {
    res = await fetch(path, Object.assign({}, opts, { headers }));
  } catch (e) {
    toast("can't reach the dashboard server", 'error');
    return null;
  }
  if (res.status === 401) { window.location.href = '/login'; return null; }
  let body = null;
  try { body = await res.json(); } catch (e) { }
  if (!res.ok) {
    toast((body && body.error) || (res.status === 403 ? "you can't do that here" : 'that didn\'t work, try again'), 'error');
    return null;
  }
  return body;
}

const apiGet = (path) => api(path);
const apiPost = (path, data) => api(path, { method: 'POST', body: JSON.stringify(data || {}) });

function fmtChips(n) {
  return (Number(n) || 0).toLocaleString('en-US');
}

function escapeHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

function icons() {
  if (window.lucide) window.lucide.createIcons();
}
