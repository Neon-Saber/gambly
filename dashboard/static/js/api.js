function toast(msg, kind) {
  const root = document.getElementById('toasts');
  if (!root) return;
  const el = document.createElement('div');
  el.className = 'toast' + (kind ? ' ' + kind : '');
  el.setAttribute('role', kind === 'error' ? 'alert' : 'status');
  const text = document.createElement('span');
  text.textContent = msg;
  const close = document.createElement('button');
  close.type = 'button';
  close.setAttribute('aria-label', 'dismiss');
  close.textContent = '×';
  close.onclick = () => el.remove();
  el.append(text, close);
  root.appendChild(el);
  setTimeout(() => el.remove(), kind === 'error' ? 7000 : 3600);
}

async function api(path, opts) {
  opts = opts || {};
  const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
  let res;
  try {
    res = await fetch(path, Object.assign({}, opts, { headers }));
  } catch (e) {
    toast("can't reach the dashboard, check your connection", 'error');
    return null;
  }
  if (res.status === 401) { window.location.href = '/login'; return null; }
  let body = null;
  try { body = await res.json(); } catch (e) { body = null; }
  if (!res.ok) {
    const fallback = res.status === 403 ? "you don't have access to that" : res.status >= 500 ? 'the server tripped up, try again in a sec' : "that didn't work";
    toast((body && body.error) || fallback, 'error');
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
  return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function ic(name, extra) {
  return `<svg class="ic" ${extra || ''} aria-hidden="true"><use href="#i-${name}"/></svg>`;
}

function chipSvg(color, cls) {
  let notches = '';
  for (let a = 0; a < 360; a += 45) notches += `<rect x="28.5" y="2" width="7" height="11" rx="1.5" transform="rotate(${a} 32 32)"/>`;
  return `<svg class="${cls || 'chip-svg'}" viewBox="0 0 64 64" aria-hidden="true"><circle cx="32" cy="32" r="30" fill="${color}"/><g fill="#f4ecd8">${notches}</g><circle cx="32" cy="32" r="18" fill="#f4ecd8"/><circle cx="32" cy="32" r="14" fill="none" stroke="${color}" stroke-width="2" stroke-dasharray="3 3"/></svg>`;
}

async function withBusy(btn, fn) {
  if (btn) btn.classList.add('busy');
  try { return await fn(); } finally { if (btn) btn.classList.remove('busy'); }
}
