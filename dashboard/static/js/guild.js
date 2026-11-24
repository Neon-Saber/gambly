const GID = document.body.dataset.gid;
const BOT = document.body.dataset.botName || 'Gambly';
let STATE = null;
let ROLES = null;
let CHANNELS = null;
let LISTS = null;
const DIRTY = new Map();

const VIEWS = ['overview', 'players', 'bounties', 'economy', 'games', 'leveling', 'logs', 'builder', 'staff', 'rebirths', 'activity', 'personal', 'danger'];
const SERVER_ONLY = ['bounties', 'economy', 'games', 'leveling', 'logs', 'builder', 'staff', 'rebirths', 'danger'];
const TITLES = {
  overview: 'Overview', players: 'Players', bounties: 'Bounties', economy: 'House rules', games: 'Games', leveling: 'Welcome & levels',
  logs: 'Logs & tickets', builder: 'Server builder', staff: 'Staff & roles', rebirths: 'Rebirths', activity: 'Activity', personal: 'Personal app', danger: 'Danger zone',
};
const RENDER = {};
const RENDERED = new Set();
let CURRENT = null;

const $ = (id) => document.getElementById(id);
const chips = (n) => fmtChips(n);
const esc = escapeHtml;

function go(name, opts) {
  opts = opts || {};
  if (!VIEWS.includes(name) || (STATE && STATE.is_personal && SERVER_ONLY.includes(name))) name = 'overview';
  CURRENT = name;
  VIEWS.forEach((v) => $('v-' + v).classList.toggle('on', v === name));
  document.querySelectorAll('.nav-a[data-view]').forEach((b) => {
    if (b.dataset.view === name) b.setAttribute('aria-current', 'page'); else b.removeAttribute('aria-current');
  });
  if (!opts.keepHash) history.replaceState(null, '', '#' + name);
  document.title = `${TITLES[name]} · ${STATE ? STATE.name : ''} · ${BOT}`;
  if (STATE && (!RENDERED.has(name) || opts.force)) { RENDERED.add(name); RENDER[name](); }
  if (!opts.noScroll) window.scrollTo(0, 0);
}

document.querySelectorAll('.nav-a[data-view]').forEach((b) => b.addEventListener('click', () => go(b.dataset.view)));
window.addEventListener('hashchange', () => { if (STATE) go(location.hash.slice(1), { keepHash: true }); });

function head(title, sub, right) {
  return `<div class="view-head"><div><h1 class="h1">${title}</h1>${sub ? `<p>${sub}</p>` : ''}</div>${right || ''}</div>`;
}

function sw(id, on, label, attrs) {
  return `<label class="sw-row"><span class="sw"><input type="checkbox" ${id ? `id="${id}" name="${id}"` : ''} ${attrs || ''} ${on ? 'checked' : ''}><i></i></span>${label || ''}</label>`;
}

function emptyState(title, text, color) {
  return `<div class="state">${chipSvg(color || '#17432e')}<b>${title}</b>${text || ''}</div>`;
}

function errorState(el, retry) {
  el.innerHTML = `<div class="state error">${chipSvg('#c4453a')}<b>couldn't load this</b><p>the dashboard didn't get an answer. it might be waking up.</p><button class="btn sm" type="button">try again</button></div>`;
  el.querySelector('button').addEventListener('click', retry);
}

function serverOnly(el) {
  el.innerHTML = head(TITLES[CURRENT], '') + `<div class="box">${emptyState('not for the personal ledger', 'this page is only for servers.')}</div>`;
}

function loadLists() {
  if (ROLES !== null && CHANNELS !== null) return Promise.resolve();
  if (!LISTS) {
    LISTS = Promise.all([apiGet(`/api/guild/${GID}/roles`), apiGet(`/api/guild/${GID}/channels`)])
      .then(([r, c]) => { ROLES = r; CHANNELS = c; LISTS = null; });
  }
  return LISTS;
}

function pickerOptions(list, selectedId, opts) {
  opts = opts || {};
  const emptyLabel = opts.emptyLabel || 'none';
  const prefix = opts.prefix || '';
  selectedId = selectedId ? String(selectedId) : '';
  if (!list) {
    if (selectedId) return `<option value="${selectedId}" selected>couldn't load the list, keeping ${selectedId}</option>`;
    return `<option value="">couldn't load the list (bot token?)</option>`;
  }
  const known = list.some((c) => c.id === selectedId);
  const missing = selectedId && !known ? `<option value="${selectedId}" selected>missing (${selectedId}), deleted?</option>` : '';
  return `<option value="">${emptyLabel}</option>${missing}` + list.map((c) => `<option value="${c.id}" ${selectedId === c.id ? 'selected' : ''}>${prefix}${esc(c.name)}</option>`).join('');
}
const textChannels = (sel, empty) => pickerOptions(CHANNELS ? CHANNELS.text : null, sel, { prefix: '#', emptyLabel: empty || 'none' });
const roleOptions = (sel, empty) => pickerOptions(ROLES, sel, { emptyLabel: empty || 'none' });

function enhanceSelect(select) {
  if (!select) return;
  if (select.dataset.comboReady) { if (select._refresh) select._refresh(); return; }
  select.dataset.comboReady = '1';
  const carried = select.getAttribute('style') || '';
  select.hidden = true;
  const wrap = document.createElement('div');
  wrap.className = 'combo';
  if (carried) wrap.style.cssText = carried;
  const lab = select.id ? document.querySelector(`label[for="${select.id}"]`) : null;
  wrap.innerHTML = `<button type="button" class="combo-trigger" aria-haspopup="listbox" aria-expanded="false"><span class="combo-label"></span><span class="combo-caret">▼</span></button>
    <div class="combo-panel"><div class="combo-search"><input type="text" placeholder="type to search" aria-label="search options"></div><div class="combo-list" role="listbox"></div></div>`;
  select.insertAdjacentElement('afterend', wrap);
  const trigger = wrap.querySelector('.combo-trigger');
  if (lab) { lab.htmlFor = ''; lab.addEventListener('click', () => trigger.focus()); trigger.setAttribute('aria-label', lab.textContent); }
  const label = wrap.querySelector('.combo-label');
  const search = wrap.querySelector('input');
  const list = wrap.querySelector('.combo-list');
  let hi = 0;
  const current = () => { const o = select.options[select.selectedIndex]; return o ? o.textContent : ''; };
  function draw() {
    const q = search.value.trim().toLowerCase();
    const opts = Array.from(select.options).filter((o) => !q || o.textContent.toLowerCase().includes(q));
    hi = Math.min(hi, Math.max(0, opts.length - 1));
    list.innerHTML = opts.length ? opts.map((o, i) => `<div class="combo-opt${o.value === select.value ? ' sel' : ''}${i === hi ? ' hl' : ''}" role="option" aria-selected="${o.value === select.value}" data-value="${esc(o.value)}">${esc(o.textContent)}</div>`).join('')
      : `<div class="combo-empty">nothing matches</div>`;
    list.querySelectorAll('.combo-opt').forEach((r) => r.addEventListener('mousedown', (e) => { e.preventDefault(); pick(r.dataset.value); }));
    const h = list.querySelector('.hl');
    if (h) h.scrollIntoView({ block: 'nearest' });
  }
  function pick(v) {
    if (select.value !== v) { select.value = v; select.dispatchEvent(new Event('change', { bubbles: true })); }
    label.textContent = current();
    close(); trigger.focus();
  }
  function open() { wrap.classList.add('open'); trigger.setAttribute('aria-expanded', 'true'); search.value = ''; hi = Math.max(0, select.selectedIndex); draw(); setTimeout(() => search.focus(), 0); document.addEventListener('mousedown', outside); }
  function close() { wrap.classList.remove('open'); trigger.setAttribute('aria-expanded', 'false'); document.removeEventListener('mousedown', outside); }
  function outside(e) { if (!wrap.contains(e.target)) close(); }
  trigger.addEventListener('click', () => (wrap.classList.contains('open') ? close() : open()));
  trigger.addEventListener('keydown', (e) => { if (e.key === 'ArrowDown') { e.preventDefault(); open(); } });
  search.addEventListener('input', () => { hi = 0; draw(); });
  search.addEventListener('keydown', (e) => {
    const n = list.querySelectorAll('.combo-opt').length;
    if (e.key === 'Escape') { e.preventDefault(); close(); trigger.focus(); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); hi = Math.min(n - 1, hi + 1); draw(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); hi = Math.max(0, hi - 1); draw(); }
    else if (e.key === 'Enter') { e.preventDefault(); const h = list.querySelector('.combo-opt.hl'); if (h) pick(h.dataset.value); }
    else if (e.key === 'Tab') close();
  });
  label.textContent = current();
  select._refresh = () => { label.textContent = current(); };
}

function trig(id) {
  const s = $(id);
  return (s && s.parentElement.querySelector('.combo-trigger')) || s;
}

function fillSelect(id, html) {
  const s = $(id);
  if (!s) return;
  s.innerHTML = html;
  enhanceSelect(s);
}

function setErr(input, msg) {
  const field = input.closest('.field') || input.parentElement;
  let el = field.querySelector('.err-msg');
  if (!el) { el = document.createElement('span'); el.className = 'err-msg'; field.appendChild(el); }
  if (!el.id) el.id = 'err-' + Math.random().toString(36).slice(2, 8);
  if (msg) { input.setAttribute('aria-invalid', 'true'); input.setAttribute('aria-describedby', el.id); el.textContent = msg; el.hidden = false; }
  else { input.removeAttribute('aria-invalid'); el.hidden = true; el.textContent = ''; }
  return !msg;
}

function numCheck(input, min, max, whole) {
  const raw = input.value.trim();
  const v = Number(raw);
  if (raw === '' || Number.isNaN(v)) return setErr(input, 'needs a number');
  if (whole && !Number.isInteger(v)) return setErr(input, 'whole numbers only');
  if (min !== null && v < min) return setErr(input, `${min} or more`);
  if (max !== null && v > max) return setErr(input, `${max} or less`);
  return setErr(input, '');
}

function bindForm(form, opts) {
  const key = opts.key;
  const mark = () => {
    if (!DIRTY.has(key)) { DIRTY.set(key, form); form.classList.add('is-dirty'); updateSavebar(); }
  };
  form.addEventListener('input', mark);
  form.addEventListener('change', mark);
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (opts.validate && !opts.validate()) {
      const bad = form.querySelector('[aria-invalid=true]');
      if (bad) bad.focus();
      toast('a few things need fixing first', 'error');
      return false;
    }
    const btn = form.querySelector('button[type=submit]');
    const ok = await withBusy(btn, opts.save);
    if (ok) { DIRTY.delete(key); form.classList.remove('is-dirty'); updateSavebar(); }
    return ok;
  });
}

function updateSavebar() {
  const bar = $('savebar');
  const n = DIRTY.size;
  bar.classList.toggle('show', n > 0);
  $('savebar-text').textContent = n === 1 ? 'you have unsaved changes' : `unsaved changes in ${n} places`;
}

$('savebar-save').addEventListener('click', () => { Array.from(DIRTY.values()).forEach((f) => f.requestSubmit()); });
$('savebar-discard').addEventListener('click', () => {
  DIRTY.clear(); updateSavebar();
  RENDERED.clear(); go(CURRENT, { force: true, keepHash: true, noScroll: true });
  toast('changes thrown out');
});
window.addEventListener('beforeunload', (e) => { if (DIRTY.size) { e.preventDefault(); e.returnValue = ''; } });

RENDER.overview = function () {
  const el = $('v-overview');
  const users = STATE.users;
  const wallet = users.reduce((s, u) => s + u.bal, 0);
  const bank = users.reduce((s, u) => s + u.bank, 0);
  const debt = users.reduce((s, u) => s + u.loan_owed, 0);
  const defaulted = users.filter((u) => u.loan_defaulted).length;
  const banned = users.filter((u) => u.is_banned).length;
  const total = wallet + bank;
  const week = STATE.week || {};
  const nameOf = (uid) => (users.find((u) => u.id === String(uid)) || {}).name || uid;
  const act = Object.entries(week.activity || {}).sort((a, b) => b[1] - a[1]);
  const played = act.reduce((s, [, n]) => s + n, 0);
  const maxAct = act.length ? act[0][1] : 1;
  const rich = users.slice().sort((a, b) => (b.bal + b.bank) - (a.bal + a.bank)).slice(0, 8);
  const maxRich = rich.length ? Math.max(1, rich[0].bal + rich[0].bank) : 1;
  const bw = week.biggest_win;
  const biggest = Math.max(wallet, bank, debt, 1);
  const stack = (v, color, label) => {
    const n = v ? Math.max(1, Math.round(13 * v / biggest)) : 0;
    return `<div class="stack" title="${label}: ${chips(v)}" style="--c:${color}">${'<span></span>'.repeat(n)}<small>${label}</small></div>`;
  };
  el.innerHTML = head(STATE.is_personal ? 'the personal ledger' : 'tonight at the table',
    STATE.is_personal ? 'everyone who plays through the personal app shares this ledger. it never touches a server\'s wallets.' : '')
    + `<section class="table-hero" aria-label="chips in play">
      <div class="hero-grid">
        <div class="stacks" aria-hidden="true">${stack(wallet, '#d6ad4c', 'wallets')}${stack(bank, '#2e7a52', 'banks')}${stack(debt, '#c4453a', 'owed')}</div>
        <div>
          <div class="pot-l">chips in play</div>
          <div class="pot-n">${chips(total)}</div>
          <div class="pot-row"><span>in wallets <b>${chips(wallet)}</b></span><span>in banks <b>${chips(bank)}</b></span><span>owed to the house <b>${chips(debt)}</b></span></div>
        </div>
      </div>
    </section>
    <div class="tiles">
      <div class="tile"><div class="n">${users.length}</div><div class="l">players on the books</div></div>
      <div class="tile good"><div class="n">${chips(played)}</div><div class="l">games this week</div></div>
      <div class="tile ${defaulted ? 'bad' : ''}"><div class="n">${defaulted}</div><div class="l">loans in default</div></div>
      <div class="tile ${banned ? 'warn' : ''}"><div class="n">${banned}</div><div class="l">banned from games</div></div>
    </div>
    <div class="cols">
      <section>
        <h2 class="sec-title">this week</h2><p class="sec-sub">resets with the weekly tournament.</p>
        ${bw ? `<div class="bigwin">${chipSvg('#d6ad4c')}<div><div class="n">+${chips(bw.amount)}</div><small>biggest single win, by ${esc(bw.name || nameOf(bw.user_id))}</small></div></div>` : ''}
        <div class="board"><div class="board-h"><span>most hands played</span><span>games</span></div>
          ${act.length ? `<ol>${act.slice(0, 8).map(([uid, n]) => `<li><span class="nm">${esc(nameOf(uid))}</span><span class="vl">${n}</span><span class="meter"><i style="width:${Math.round(100 * n / maxAct)}%"></i></span></li>`).join('')}</ol>` : '<p class="hint" style="margin:0">nobody has played this week yet.</p>'}
        </div>
      </section>
      <section>
        <h2 class="sec-title">high rollers</h2><p class="sec-sub">wallet plus bank.</p>
        <div class="board"><div class="board-h"><span>player</span><span>worth</span></div>
          ${rich.length ? `<ol>${rich.map((u) => `<li><span class="nm">${esc(u.name)}</span><span class="vl" style="color:var(--gold-hi)">${chips(u.bal + u.bank)}</span><span class="meter"><i style="width:${Math.round(100 * (u.bal + u.bank) / maxRich)}%"></i></span></li>`).join('')}</ol>` : '<p class="hint" style="margin:0">no players yet.</p>'}
        </div>
        <button class="btn quiet sm" type="button" style="margin-top:10px" onclick="go('players')">see every player ${ic('send')}</button>
      </section>
    </div>`;
};

const PLAYERS = { q: '', filter: 'all', sort: 'total', dir: -1, shown: 50 };

RENDER.players = function () {
  const el = $('v-players');
  el.innerHTML = head('players', 'edit a wallet or bank right in the ledger. rows you change get a gold edge until you save them.',
    `<a class="btn" href="/api/guild/${GID}/export.csv">${ic('download')}Export CSV</a>`)
    + `<form class="tray" id="bulk-form" novalidate>
      ${chipSvg('#d6ad4c')}
      <div>
        <div class="field"><label for="bulk-amount">give or take chips from every player here</label>
          <div class="inline"><input type="number" id="bulk-amount" placeholder="like 500, or -200 to take" step="1">
            <button class="btn gold" type="submit">${ic('send')}Apply to everyone</button></div>
          <span class="err-msg" hidden></span></div>
      </div>
    </form>
    <div class="filters" role="search">
      <label class="sr" for="p-find">search players</label>
      <input type="search" id="p-find" placeholder="search by name or id" value="${esc(PLAYERS.q)}">
      <div class="pill-set" role="group" aria-label="filter">
        ${[['all', 'everyone'], ['debt', 'in debt'], ['banned', 'banned'], ['managers', 'managers'], ['rebirthed', 'rebirthed']].map(([k, l]) => `<button type="button" data-f="${k}" aria-pressed="${PLAYERS.filter === k}">${l}</button>`).join('')}
      </div>
      <span class="count" id="p-count"></span>
    </div>
    <div class="ledger-wrap"><table class="ledger">
      <thead><tr>
        ${[['name', 'player', ''], ['bal', 'wallet', 'r'], ['bank', 'bank', 'r'], ['total', 'worth', 'r'], ['loan', 'loan', 'r'], ['rebirths', 'rebirths', 'r']].map(([k, l, c]) => `<th class="${c}" aria-sort="${PLAYERS.sort === k ? (PLAYERS.dir > 0 ? 'ascending' : 'descending') : 'none'}"><button type="button" data-sort="${k}">${l}</button></th>`).join('')}
        <th></th>
      </tr></thead>
      <tbody id="p-body"></tbody>
    </table></div>
    <div style="text-align:center;margin-top:14px"><button class="btn" type="button" id="p-more" hidden>show more</button></div>`;
  const bulk = $('bulk-form');
  bulk.addEventListener('submit', async (e) => {
    e.preventDefault();
    const inp = $('bulk-amount');
    const v = Number(inp.value);
    if (!inp.value.trim() || !Number.isInteger(v) || v === 0) { setErr(inp, 'a whole number that isn\'t 0'); inp.focus(); return; }
    setErr(inp, '');
    if (!confirm(`${v > 0 ? 'give' : 'take'} ${chips(Math.abs(v))} chips ${v > 0 ? 'to' : 'from'} all ${STATE.users.length} players?`)) return;
    const r = await withBusy(bulk.querySelector('button'), () => apiPost(`/api/guild/${GID}/bulk_grant`, { amount: v }));
    if (r) { toast(`done, ${r.affected} players changed`, 'ok'); inp.value = ''; refresh(); }
  });
  $('p-find').addEventListener('input', (e) => { PLAYERS.q = e.target.value.trim().toLowerCase(); PLAYERS.shown = 50; drawPlayers(); });
  el.querySelectorAll('[data-f]').forEach((b) => b.addEventListener('click', () => {
    PLAYERS.filter = b.dataset.f; PLAYERS.shown = 50;
    el.querySelectorAll('[data-f]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    drawPlayers();
  }));
  el.querySelectorAll('[data-sort]').forEach((b) => b.addEventListener('click', () => {
    const k = b.dataset.sort;
    PLAYERS.dir = PLAYERS.sort === k ? -PLAYERS.dir : (k === 'name' ? 1 : -1);
    PLAYERS.sort = k;
    el.querySelectorAll('th[aria-sort]').forEach((th) => th.setAttribute('aria-sort', 'none'));
    b.parentElement.setAttribute('aria-sort', PLAYERS.dir > 0 ? 'ascending' : 'descending');
    drawPlayers();
  }));
  $('p-more').addEventListener('click', () => { PLAYERS.shown += 50; drawPlayers(); });
  drawPlayers();
};

function drawPlayers() {
  const body = $('p-body');
  if (!body) return;
  const f = PLAYERS.filter;
  const keep = (u) => (f === 'all') || (f === 'debt' && u.loan_owed > 0) || (f === 'banned' && u.is_banned) || (f === 'managers' && u.is_manager) || (f === 'rebirthed' && u.rebirths > 0);
  const val = (u) => ({ name: u.name.toLowerCase(), bal: u.bal, bank: u.bank, total: u.bal + u.bank, loan: u.loan_owed, rebirths: u.rebirths }[PLAYERS.sort]);
  const list = STATE.users.filter((u) => keep(u) && (!PLAYERS.q || (u.name + ' ' + u.id).toLowerCase().includes(PLAYERS.q)))
    .sort((a, b) => (val(a) > val(b) ? 1 : val(a) < val(b) ? -1 : 0) * PLAYERS.dir);
  $('p-count').textContent = `${list.length} of ${STATE.users.length}`;
  $('p-more').hidden = list.length <= PLAYERS.shown;
  if (!STATE.users.length) { body.innerHTML = `<tr><td colspan="7">${emptyState('nobody has played here yet', 'players show up after their first command.')}</td></tr>`; return; }
  if (!list.length) { body.innerHTML = `<tr><td colspan="7">${emptyState('nobody matches', 'try another name or filter.')}</td></tr>`; return; }
  const srv = !STATE.is_personal;
  body.innerHTML = list.slice(0, PLAYERS.shown).map((u) => `
    <tr data-uid="${u.id}">
      <td class="who"><b>${esc(u.name)}</b><small>${u.id}</small>
        ${u.is_manager ? '<span class="tag gold">manager</span> ' : ''}${u.is_banned ? '<span class="tag red">banned</span> ' : ''}${u.loan_defaulted ? '<span class="tag red">defaulted</span>' : ''}</td>
      <td class="r"><label class="sr" for="w-${u.id}">wallet for ${esc(u.name)}</label><input type="number" id="w-${u.id}" value="${u.bal}" data-field="bal" min="0" step="1"></td>
      <td class="r"><label class="sr" for="k-${u.id}">bank for ${esc(u.name)}</label><input type="number" id="k-${u.id}" value="${u.bank}" data-field="bank" min="0" step="1"></td>
      <td class="r">${chips(u.bal + u.bank)}</td>
      <td class="r">${u.loan_owed ? chips(u.loan_owed) : '<span class="sub">·</span>'}</td>
      <td class="r">${u.rebirths || '<span class="sub">·</span>'}</td>
      <td><div class="acts">
        <button class="btn sm gold" type="button" data-act="save" hidden>Save</button>
        <details class="more-menu"><summary class="btn sm quiet" aria-label="more for ${esc(u.name)}">${ic('more')}</summary><div class="menu">
          ${srv ? `<button type="button" data-act="ban">${u.is_banned ? 'let them play again' : 'ban from the games'}</button>` : ''}
          ${srv ? `<button type="button" data-act="manager">${u.is_manager ? 'remove manager' : 'make manager'}</button>` : ''}
          ${u.loan_owed ? '<button type="button" data-act="forgive">forgive their loan</button>' : ''}
          <button type="button" class="red" data-act="reset">reset their account</button>
        </div></details>
      </div></td>
    </tr>`).join('');
  body.querySelectorAll('tr[data-uid]').forEach((tr) => {
    const save = tr.querySelector('[data-act=save]');
    tr.querySelectorAll('input').forEach((inp) => inp.addEventListener('input', () => {
      tr.classList.add('dirty'); save.hidden = false;
      DIRTY.set('player-' + tr.dataset.uid, { requestSubmit: () => save.click() }); updateSavebar();
    }));
    tr.querySelectorAll('[data-act]').forEach((b) => b.addEventListener('click', () => playerAction(b, tr)));
  });
}

async function playerAction(btn, row) {
  const uid = row.dataset.uid;
  const u = STATE.users.find((x) => x.id === uid);
  const act = btn.dataset.act;
  const menu = btn.closest('details');
  if (menu) menu.open = false;
  if (act === 'save') {
    const bi = row.querySelector('[data-field=bal]');
    const ki = row.querySelector('[data-field=bank]');
    const okb = numCheck(bi, 0, null, true);
    const okk = numCheck(ki, 0, null, true);
    if (!okb || !okk) { toast(`check ${u.name}'s numbers`, 'error'); return; }
    await withBusy(btn, async () => {
      let ok = true;
      if (Number(bi.value) !== u.bal) ok = ok && !!(await apiPost(`/api/guild/${GID}/balance`, { user_id: uid, balance: Number(bi.value) }));
      if (Number(ki.value) !== u.bank) ok = ok && !!(await apiPost(`/api/guild/${GID}/bank`, { user_id: uid, bank: Number(ki.value) }));
      if (ok) { DIRTY.delete('player-' + uid); updateSavebar(); toast(`saved ${u.name}`, 'ok'); await refresh(); }
    });
  } else if (act === 'ban') {
    const r = await apiPost(`/api/guild/${GID}/ban/${uid}`, { banned: !u.is_banned });
    if (r) { toast(u.is_banned ? `${u.name} can play again` : `${u.name} is banned from the games`, 'ok'); refresh(); }
  } else if (act === 'manager') {
    const r = await apiPost(`/api/guild/${GID}/manager/${uid}`, { manager: !u.is_manager });
    if (r) { toast(u.is_manager ? `${u.name} isn't a manager now` : `${u.name} is a manager now`, 'ok'); refresh(); }
  } else if (act === 'forgive') {
    if (!confirm(`wipe ${u.name}'s ${chips(u.loan_owed)} chip loan?`)) return;
    const r = await apiPost(`/api/guild/${GID}/forgive/${uid}`, {});
    if (r) { toast('loan wiped', 'ok'); refresh(); }
  } else if (act === 'reset') {
    if (!confirm(`start ${u.name} over with a brand new account? there's no undo.`)) return;
    const r = await apiPost(`/api/guild/${GID}/reset/${uid}`, {});
    if (r) { toast(`${u.name} is starting over`, 'ok'); refresh(); }
  }
}

RENDER.bounties = function () {
  const el = $('v-bounties');
  if (STATE.is_personal) return serverOnly(el);
  const list = Object.entries(STATE.bounties || {}).sort((a, b) => b[1] - a[1]);
  el.innerHTML = head('wanted', 'chips on someone\'s head. the first person to rob them collects.')
    + `<form class="box" id="b-form" novalidate>
      <div class="box-h"><h2>post a bounty</h2><span class="hint">0 takes it down</span></div>
      <div class="fields" style="grid-template-columns:2fr 1fr auto;align-items:end">
        <div class="field"><label for="b-uid">who (Discord user ID)</label><input type="text" id="b-uid" inputmode="numeric" list="b-names" placeholder="like 1013938443916689429">
          <datalist id="b-names">${STATE.users.map((u) => `<option value="${u.id}">${esc(u.name)}</option>`).join('')}</datalist></div>
        <div class="field"><label for="b-amount">chips</label><input type="number" id="b-amount" min="0" step="1" placeholder="5000"></div>
        <div class="field"><button class="btn gold" type="submit">${ic('target')}Post it</button></div>
      </div>
    </form>
    ${list.length ? `<div class="posters">${list.map(([uid, amt], i) => {
      const u = STATE.users.find((x) => x.id === uid);
      return `<article class="poster" style="--tilt:${(i % 3 - 1) * 1.2}deg"><h3>WANTED</h3><div class="nm">${esc(u ? u.name : uid)}</div><small>${uid}</small>
        <div class="amt">${chips(amt)}</div><small>chips to whoever robs them</small><button class="btn sm" type="button" data-clear="${uid}">take it down</button></article>`;
    }).join('')}</div>` : `<div class="box">${emptyState('no bounties up', 'post one above, or players can with /bounty.', '#c4453a')}</div>`}`;
  $('b-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const uidI = $('b-uid');
    const amtI = $('b-amount');
    const okU = setErr(uidI, /^\d{15,21}$/.test(uidI.value.trim()) ? '' : 'a Discord user ID is 15 to 21 digits');
    const okA = numCheck(amtI, 0, null, true);
    if (!okU || !okA) return;
    const r = await withBusy(e.target.querySelector('button'), () => apiPost(`/api/guild/${GID}/bounty`, { user_id: uidI.value.trim(), amount: Number(amtI.value) }));
    if (r) { toast(Number(amtI.value) ? 'bounty posted' : 'bounty taken down', 'ok'); await refresh(); RENDER.bounties(); }
  });
  el.querySelectorAll('[data-clear]').forEach((b) => b.addEventListener('click', async () => {
    const r = await withBusy(b, () => apiPost(`/api/guild/${GID}/bounty`, { user_id: b.dataset.clear, amount: 0 }));
    if (r) { toast('taken down', 'ok'); await refresh(); RENDER.bounties(); }
  }));
};

RENDER.economy = async function () {
  const el = $('v-economy');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('house rules', 'how the money moves in this server.')
    + `<div class="cols">
      <form class="slip" id="eco-basic" novalidate><span class="pip" aria-hidden="true">♠</span>
        <h2>the basics</h2><p class="hint">who runs the cage and how commands start.</p>
        <div class="fields" style="grid-template-columns:1fr">
          <div class="field"><label for="s-prefix">command prefix</label><input type="text" id="s-prefix" maxlength="3" value="${esc(STATE.prefix)}">
            <span class="hint">for <code>!</code> commands. 1 to 3 characters, no spaces.</span></div>
          <div class="field"><label for="s-manager-role">manager role (the older system)</label><select id="s-manager-role"></select>
            <span class="hint">people with this can manage chips. the Dealer rank on Staff &amp; roles does the same.</span></div>
        </div>
        <button class="btn gold" type="submit">Save the basics</button>
      </form>
      <form class="slip" id="eco-money" novalidate><span class="pip" aria-hidden="true">♥</span>
        <h2>the pots</h2><p class="hint">change a pot by hand, or set the tax the house takes.</p>
        <div class="fields" style="grid-template-columns:1fr 1fr">
          <div class="field"><label for="s-jackpot">slots jackpot</label><input type="number" id="s-jackpot" min="0" step="1" value="${STATE.jackpot}"></div>
          <div class="field"><label for="s-tax">tax on winnings %</label><input type="number" id="s-tax" min="0" max="100" step="1" value="${STATE.tax_pct}"></div>
          <div class="field"><label for="s-pot">server pot</label><input type="number" id="s-pot" min="0" step="1" value="${STATE.server_pot}"></div>
          <div class="field"><label for="s-lottery">lottery pot</label><input type="number" id="s-lottery" min="0" step="1" value="${STATE.lottery_pot}"></div>
        </div>
        ${sw('s-testmode', STATE.testmode, 'test mode: the owner\'s own bets always win')}
        <p class="hint" style="margin-top:-8px">leave this off on a live server. players can't tell it's on.</p>
        <button class="btn gold" type="submit">Save the pots</button>
      </form>
    </div>`;
  bindForm($('eco-basic'), {
    key: 'eco-basic',
    validate: () => setErr($('s-prefix'), /^\S{1,3}$/.test($('s-prefix').value) ? '' : '1 to 3 characters, no spaces'),
    save: async () => {
      const a = await apiPost(`/api/guild/${GID}/prefix`, { prefix: $('s-prefix').value });
      const b = a && await apiPost(`/api/guild/${GID}/manager_role`, { role_id: $('s-manager-role').value || null });
      if (a && b) { toast('basics saved', 'ok'); refresh(); return true; }
      return false;
    },
  });
  bindForm($('eco-money'), {
    key: 'eco-money',
    validate: () => [numCheck($('s-jackpot'), 0, null, true), numCheck($('s-tax'), 0, 100, true), numCheck($('s-pot'), 0, null, true), numCheck($('s-lottery'), 0, null, true)].every(Boolean),
    save: async () => {
      const r = await apiPost(`/api/guild/${GID}/config`, {
        jackpot: Number($('s-jackpot').value), tax_pct: Number($('s-tax').value), server_pot: Number($('s-pot').value),
        lottery_pot: Number($('s-lottery').value), testmode: $('s-testmode').checked,
      });
      if (r) { toast('pots saved', 'ok'); refresh(); return true; }
      return false;
    },
  });
  await loadLists();
  fillSelect('s-manager-role', roleOptions(STATE.manager_role));
};

const ROOM_LABELS = { 'card-tables': 'card tables', 'slots-and-spins': 'slots & spins', 'dice-games': 'dice games', 'crash-and-mines': 'crash & mines', 'quick-bets': 'quick bets', 'pvp-arena': 'pvp arena' };

RENDER.games = async function () {
  const el = $('v-games');
  if (STATE.is_personal) return serverOnly(el);
  const games = STATE.game_list || [];
  const roomOf = {};
  Object.entries(STATE.game_groups || {}).forEach(([g, l]) => l.forEach((x) => { roomOf[x] = g; }));
  const off = new Set(STATE.disabled_games || []);
  const rooms = {};
  games.forEach((g) => { (rooms[roomOf[g] || 'other'] = rooms[roomOf[g] || 'other'] || []).push(g); });
  el.innerHTML = head('games', `${games.length - off.size} of ${games.length} games are open. lock any game to one channel so bets stay out of chat.`)
    + `<form id="games-form" novalidate>
      <div class="filters">
        <label class="sr" for="g-find">find a game</label><input type="search" id="g-find" placeholder="find a game">
        <div class="pill-set" role="group" aria-label="show"><button type="button" data-gs="all" aria-pressed="true">all</button><button type="button" data-gs="on" aria-pressed="false">open</button><button type="button" data-gs="off" aria-pressed="false">closed</button></div>
        <button class="btn sm" type="button" id="g-all-on">open all</button><button class="btn sm" type="button" id="g-all-off">close all</button>
      </div>
      <div class="rooms">${Object.entries(rooms).map(([room, list]) => `
        <details class="room" open><summary>${chipSvg(room === 'pvp-arena' ? '#c4453a' : room === 'crash-and-mines' ? '#d6ad4c' : '#2e7a52', 'chip-svg')}${esc(ROOM_LABELS[room] || room)}<small>${list.length} games</small></summary>
          ${list.sort().map((g) => `<div class="game${off.has(g) ? ' off' : ''}" data-game="${g}">
            <span class="sw"><input type="checkbox" data-on aria-label="${g} open" ${off.has(g) ? '' : 'checked'}><i></i></span>
            <b>${esc(g)}</b>
            <select data-ch aria-label="channel for ${g}" style="width:100%"><option>loading…</option></select>
          </div>`).join('')}
        </details>`).join('')}</div>
      <div style="margin-top:16px"><button class="btn gold" type="submit">Save games</button></div>
    </form>
    <form class="box" id="env-form" novalidate style="margin-top:22px">
      <div class="box-h"><h2>server overrides</h2><span class="hint">one KEY=value per line. checked before the bot's .env for this server only.</span></div>
      <div class="field"><label class="sr" for="env-box">overrides</label><textarea id="env-box" rows="6" style="font-family:var(--mono)" placeholder="SOME_KEY=some value"></textarea></div>
      <button class="btn gold" type="submit" style="margin-top:12px">Save overrides</button>
    </form>`;
  $('env-box').value = Object.entries(STATE.custom_env || {}).map(([k, v]) => `${k}=${v}`).join('\n');
  let show = 'all';
  const filter = () => {
    const q = $('g-find').value.trim().toLowerCase();
    el.querySelectorAll('.game').forEach((r) => {
      const on = r.querySelector('[data-on]').checked;
      r.hidden = !((!q || r.dataset.game.includes(q)) && (show === 'all' || (show === 'on') === on));
    });
    el.querySelectorAll('.room').forEach((room) => { room.hidden = !room.querySelector('.game:not([hidden])'); });
  };
  $('g-find').addEventListener('input', filter);
  el.querySelectorAll('[data-gs]').forEach((b) => b.addEventListener('click', () => {
    show = b.dataset.gs; el.querySelectorAll('[data-gs]').forEach((x) => x.setAttribute('aria-pressed', String(x === b))); filter();
  }));
  el.querySelectorAll('[data-on]').forEach((c) => c.addEventListener('change', () => c.closest('.game').classList.toggle('off', !c.checked)));
  const setAll = (v) => { el.querySelectorAll('[data-on]').forEach((c) => { c.checked = v; c.closest('.game').classList.toggle('off', !v); }); $('games-form').dispatchEvent(new Event('change')); };
  $('g-all-on').addEventListener('click', () => setAll(true));
  $('g-all-off').addEventListener('click', () => setAll(false));
  bindForm($('games-form'), {
    key: 'games',
    save: async () => {
      const chans = {};
      const disabled = [];
      el.querySelectorAll('.game').forEach((r) => {
        chans[r.dataset.game] = r.querySelector('[data-ch]').value || null;
        if (!r.querySelector('[data-on]').checked) disabled.push(r.dataset.game);
      });
      const a = await apiPost(`/api/guild/${GID}/game_channels`, { game_channels: chans });
      const b = a && await apiPost(`/api/guild/${GID}/disabled_games`, { disabled_games: disabled });
      if (a && b) { toast('games saved', 'ok'); await refresh(); return true; }
      return false;
    },
  });
  bindForm($('env-form'), {
    key: 'env',
    validate: () => {
      const bad = $('env-box').value.split('\n').map((l) => l.trim()).filter((l) => l && !l.startsWith('#') && !/^[A-Za-z_][A-Za-z0-9_]*=/.test(l));
      return setErr($('env-box'), bad.length ? `these lines need KEY=value: ${bad.slice(0, 3).join(', ')}` : '');
    },
    save: async () => {
      const r = await apiPost(`/api/guild/${GID}/custom_env`, { raw: $('env-box').value });
      if (r) { toast('overrides saved', 'ok'); refresh(); return true; }
      return false;
    },
  });
  await loadLists();
  el.querySelectorAll('.game').forEach((r) => {
    const s = r.querySelector('[data-ch]');
    s.innerHTML = textChannels((STATE.game_channels || {})[r.dataset.game], 'any channel with its name');
    enhanceSelect(s);
  });
};

function previewText(tpl, kind) {
  const fill = { user: '<span class="mention">@new member</span>', username: 'new member', server: esc(STATE.name), membercount: String(STATE.users.length + 1), level: '5' };
  const def = kind === 'welcome' ? 'welcome {user} to **{server}**! you\'re member #{membercount}' : '{user} just reached **level {level}**!';
  return esc(tpl || def).replace(/\{(user|username|server|membercount|level)\}/g, (m, k) => fill[k]).replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
}

RENDER.leveling = async function () {
  const el = $('v-leveling');
  if (STATE.is_personal) return serverOnly(el);
  const pv = (id, kind, tpl) => `<div class="preview" aria-label="preview"><div class="msg"><span class="pfp">${chipSvg('#c4453a', 'chip-svg')}</span><div><span class="nm">${esc(BOT)}</span><span class="bot">APP</span><div class="emb" id="${id}">${previewText(tpl, kind)}</div></div></div></div>`;
  el.innerHTML = head('welcome & levels', 'what new people see, and how chatting turns into ranks.')
    + `<div class="cols">
      <form class="box" id="w-form" novalidate>
        <div class="box-h"><h2>welcome message</h2></div>
        ${sw('w-on', STATE.welcome_enabled, 'post a welcome when someone joins')}
        <div class="field" style="margin-bottom:14px"><label for="w-ch">channel</label><select id="w-ch"></select><span class="err-msg" hidden></span></div>
        <div class="field"><label for="w-msg">message</label><textarea id="w-msg" rows="3" placeholder="welcome {user} to {server}!">${esc(STATE.welcome_message || '')}</textarea>
          <span class="hint">use <code>{user}</code> <code>{username}</code> <code>{server}</code> <code>{membercount}</code>. blank uses the default.</span></div>
        <button class="btn gold" type="submit" style="margin-top:14px">Save welcome</button>
      </form>
      <div><h2 class="sec-title">what it looks like</h2><p class="sec-sub">updates as you type.</p>${pv('w-pv', 'welcome', STATE.welcome_message)}</div>
    </div>
    <div class="cols" style="margin-top:6px">
      <form class="box" id="l-form" novalidate>
        <div class="box-h"><h2>levels</h2></div>
        ${sw('l-on', STATE.leveling_enabled, 'give XP for chatting and post level ups')}
        <div class="field" style="margin-bottom:14px"><label for="l-ch">level up channel</label><select id="l-ch"></select><span class="hint">blank posts it where they're chatting</span></div>
        <div class="field"><label for="l-msg">level up message</label><textarea id="l-msg" rows="2" placeholder="{user} just hit level {level}!">${esc(STATE.level_message || '')}</textarea>
          <span class="hint"><code>{user}</code> <code>{username}</code> <code>{server}</code> <code>{level}</code></span></div>
        <div style="margin:14px 0">${pv('l-pv', 'level', STATE.level_message)}</div>
        <button class="btn gold" type="submit">Save levels</button>
      </form>
      <section><h2 class="sec-title">top chatters</h2><p class="sec-sub">by total XP.</p><div class="board" id="lvl-board"><span class="skel"></span></div></section>
    </div>
    <form class="box" id="lr-form" novalidate>
      <div class="box-h"><h2>level roles</h2><span class="hint">hitting a level gives every role at or below it. nothing gets taken away.</span></div>
      <div class="ledger-wrap"><table class="ledger"><thead><tr><th>level</th><th>role</th><th></th></tr></thead><tbody id="lr-rows"></tbody></table></div>
      <div class="inline" style="margin-top:12px"><button class="btn sm" type="button" id="lr-add">${ic('plus')}add a level</button><button class="btn gold" type="submit">Save level roles</button></div>
    </form>
    <form class="box" id="mc-form" novalidate>
      <div class="box-h"><h2>member counter</h2><span class="hint">renames a voice channel to the live member count, on joins and leaves and every 10 minutes.</span></div>
      ${sw('mc-on', STATE.member_count_enabled, 'keep the counter going')}
      <div class="fields">
        <div class="field"><label for="mc-ch">voice channel</label><select id="mc-ch"></select><span class="err-msg" hidden></span></div>
        <div class="field"><label for="mc-tpl">channel name</label><input type="text" id="mc-tpl" maxlength="90" value="${esc(STATE.member_count_template || '')}" placeholder="Members: {count}"><span class="hint">needs <code>{count}</code></span></div>
      </div>
      <button class="btn gold" type="submit">Save counter</button>
    </form>`;
  $('w-msg').addEventListener('input', (e) => { $('w-pv').innerHTML = previewText(e.target.value, 'welcome'); });
  $('l-msg').addEventListener('input', (e) => { $('l-pv').innerHTML = previewText(e.target.value, 'level'); });
  const needCh = (onId, chId, what) => setErr(trig(chId), $(onId).checked && !$(chId).value ? `pick a ${what} or turn it off` : '');
  bindForm($('w-form'), {
    key: 'welcome', validate: () => needCh('w-on', 'w-ch', 'channel'),
    save: async () => { const r = await apiPost(`/api/guild/${GID}/welcome_config`, { welcome_enabled: $('w-on').checked, welcome_channel_id: $('w-ch').value || null, welcome_message: $('w-msg').value }); if (r) { toast('welcome saved', 'ok'); refresh(); } return !!r; },
  });
  bindForm($('l-form'), {
    key: 'levels',
    save: async () => { const r = await apiPost(`/api/guild/${GID}/leveling_config`, { leveling_enabled: $('l-on').checked, level_channel_id: $('l-ch').value || null, level_message: $('l-msg').value }); if (r) { toast('levels saved', 'ok'); refresh(); } return !!r; },
  });
  bindForm($('mc-form'), {
    key: 'counter',
    validate: () => [needCh('mc-on', 'mc-ch', 'voice channel'), setErr($('mc-tpl'), $('mc-tpl').value && !$('mc-tpl').value.includes('{count}') ? 'add {count} somewhere' : '')].every(Boolean),
    save: async () => { const r = await apiPost(`/api/guild/${GID}/member_count_config`, { member_count_enabled: $('mc-on').checked, member_count_channel_id: $('mc-ch').value || null, member_count_template: $('mc-tpl').value }); if (r) { toast('counter saved', 'ok'); refresh(); } return !!r; },
  });
  const [board] = await Promise.all([apiGet(`/api/guild/${GID}/level_leaderboard`), loadLists()]);
  fillSelect('w-ch', textChannels(STATE.welcome_channel_id));
  fillSelect('l-ch', textChannels(STATE.level_channel_id));
  fillSelect('mc-ch', pickerOptions(CHANNELS ? CHANNELS.voice : null, STATE.member_count_channel_id));
  roleRows('lr', STATE.level_roles, 'level_roles', 'level', 0, 1000);
  $('lvl-board').innerHTML = board === null ? '<p class="hint">couldn\'t load the leaderboard</p>' : (board.length
    ? `<div class="board-h"><span>player</span><span>level · xp</span></div><ol>${board.map((e) => `<li><span class="nm">${esc(e.name)}</span><span class="vl">${e.level} · ${e.total_xp.toLocaleString()}</span></li>`).join('')}</ol>`
    : '<p class="hint" style="margin:0">nobody has XP yet.</p>');
};

function roleRows(prefix, current, key, word, min, max) {
  const body = $(prefix + '-rows');
  const form = $(prefix + '-form');
  const add = (n, rid) => {
    if (body.querySelector('.empty-row')) body.innerHTML = '';
    const tr = document.createElement('tr');
    const uid = Math.random().toString(36).slice(2, 7);
    tr.innerHTML = `<td><div class="field"><label class="sr" for="n-${uid}">${word}</label><input type="number" id="n-${uid}" class="rr-n" min="${min}" max="${max}" step="1" value="${n ?? ''}" style="width:110px"></div></td>
      <td><select class="rr-role" aria-label="role" style="min-width:240px">${roleOptions(rid, 'pick a role')}</select></td>
      <td><div class="acts"><button class="btn sm red" type="button">remove</button></div></td>`;
    tr.querySelector('.btn.red').addEventListener('click', () => { tr.remove(); form.dispatchEvent(new Event('change')); if (!body.children.length) empty(); });
    body.appendChild(tr);
    enhanceSelect(tr.querySelector('.rr-role'));
  };
  const empty = () => { body.innerHTML = `<tr class="empty-row"><td colspan="3"><p class="hint" style="margin:6px 0">no ${word} roles yet. add one, or let <code>/setup roles</code> make them.</p></td></tr>`; };
  body.innerHTML = '';
  const rows = Object.entries(current || {}).sort((a, b) => Number(a[0]) - Number(b[0]));
  if (rows.length) rows.forEach(([n, rid]) => add(n, rid)); else empty();
  $(prefix + '-add').onclick = () => { add('', ''); form.dispatchEvent(new Event('change')); };
  bindForm(form, {
    key: key,
    validate: () => {
      let ok = true;
      const seen = new Set();
      body.querySelectorAll('tr:not(.empty-row)').forEach((tr) => {
        const n = tr.querySelector('.rr-n');
        let good = numCheck(n, min, max, true);
        if (good && seen.has(n.value)) good = setErr(n, 'used twice');
        seen.add(n.value);
        if (!tr.querySelector('.rr-role').value) { good = false; setErr(n, 'pick a role for this one'); }
        ok = ok && good;
      });
      return ok;
    },
    save: async () => {
      const out = {};
      body.querySelectorAll('tr:not(.empty-row)').forEach((tr) => { out[tr.querySelector('.rr-n').value.trim()] = tr.querySelector('.rr-role').value; });
      const r = await apiPost(`/api/guild/${GID}/${key}`, { [key]: out });
      if (r) { toast(`${word} roles saved`, 'ok'); refresh(); }
      return !!r;
    },
  });
}

const LOG_TYPES = [
  ['mod', 'staff actions', 'kicks, bans, mutes, warns, purges, locks'],
  ['ticket', 'ticket transcripts', 'posted when a ticket closes'],
  ['report', 'reports', '/report and right click → Report Message'],
  ['message', 'edits & deletes', 'gets busy in an active server'],
  ['withdraw', 'withdrawals', 'bank to wallet'],
  ['deposit', 'deposits', 'wallet to bank'],
];

RENDER.logs = async function () {
  const el = $('v-logs');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('logs & tickets', 'where staff stuff gets posted, and how tickets open.')
    + `<form class="box" id="t-form" novalidate>
      <div class="box-h"><h2>tickets</h2></div>
      <div class="fields">
        <div class="field"><label for="m-staff">staff team role</label><select id="m-staff"></select><span class="hint">can see tickets. what someone can actually do comes from their rank.</span></div>
        <div class="field"><label for="m-cat">ticket category</label><select id="m-cat"></select><span class="hint">new tickets open in here</span></div>
        <div class="field"><label for="m-ping">ping on new tickets</label><select id="m-ping"></select><span class="hint">optional</span></div>
      </div>
      <button class="btn gold" type="submit">Save tickets</button>
    </form>
    <form class="box" id="log-form" novalidate>
      <div class="box-h"><h2>logs</h2><span class="hint">each one posts to its own staff channel.</span></div>
      <div class="ledger-wrap"><table class="ledger"><thead><tr><th>what</th><th>on</th><th>channel</th></tr></thead>
      <tbody>${LOG_TYPES.map(([k, l, d]) => `<tr data-log="${k}"><td class="who"><b>${l}</b><small>${d}</small></td>
        <td><span class="sw"><input type="checkbox" data-log-on aria-label="${l} on" ${STATE.logging[k].enabled ? 'checked' : ''}><i></i></span></td>
        <td><div class="field"><select data-log-ch aria-label="${l} channel" style="min-width:230px"><option>loading…</option></select></div></td></tr>`).join('')}</tbody></table></div>
      <button class="btn gold" type="submit" style="margin-top:14px">Save logs</button>
    </form>
    <form class="box" id="st-form" novalidate>
      <div class="box-h"><h2>bot status post</h2><span class="hint">one message the bot keeps editing with uptime, ping and chips. /status works anytime.</span></div>
      ${sw('st-on', STATE.status_enabled, 'keep a status post going')}
      <div class="fields"><div class="field"><label for="st-ch">channel</label><select id="st-ch"></select><span class="err-msg" hidden></span></div></div>
      <button class="btn gold" type="submit">Save status post</button>
    </form>`;
  bindForm($('t-form'), {
    key: 'tickets',
    save: async () => { const r = await apiPost(`/api/guild/${GID}/moderation_config`, { staff_role_id: $('m-staff').value || null, ticket_category_id: $('m-cat').value || null, ticket_ping_role_id: $('m-ping').value || null }); if (r) { toast('tickets saved', 'ok'); refresh(); } return !!r; },
  });
  bindForm($('log-form'), {
    key: 'logs',
    validate: () => {
      let ok = true;
      el.querySelectorAll('tr[data-log]').forEach((r) => {
        const s = r.querySelector('[data-log-ch]');
        const bad = r.querySelector('[data-log-on]').checked && !s.value;
        const trig = r.querySelector('.combo-trigger') || s;
        setErr(trig, bad ? 'pick a channel or turn it off' : '');
        if (bad) ok = false;
      });
      return ok;
    },
    save: async () => {
      const body = {};
      el.querySelectorAll('tr[data-log]').forEach((r) => { body[`log_${r.dataset.log}_enabled`] = r.querySelector('[data-log-on]').checked; body[`log_${r.dataset.log}_channel`] = r.querySelector('[data-log-ch]').value || null; });
      const r = await apiPost(`/api/guild/${GID}/moderation_config`, body);
      if (r) { toast('logs saved', 'ok'); refresh(); }
      return !!r;
    },
  });
  bindForm($('st-form'), {
    key: 'status',
    validate: () => setErr(trig('st-ch'), $('st-on').checked && !$('st-ch').value ? 'pick a channel or turn it off' : ''),
    save: async () => { const r = await apiPost(`/api/guild/${GID}/status_config`, { status_enabled: $('st-on').checked, status_channel_id: $('st-ch').value || null }); if (r) { toast('status post saved', 'ok'); refresh(); } return !!r; },
  });
  await loadLists();
  fillSelect('m-staff', roleOptions(STATE.staff_role_id));
  fillSelect('m-cat', pickerOptions(CHANNELS ? CHANNELS.categories : null, STATE.ticket_category_id));
  fillSelect('m-ping', roleOptions(STATE.ticket_ping_role_id));
  fillSelect('st-ch', textChannels(STATE.status_channel_id));
  el.querySelectorAll('tr[data-log]').forEach((r) => { const s = r.querySelector('[data-log-ch]'); s.innerHTML = textChannels(STATE.logging[r.dataset.log].channel); enhanceSelect(s); });
};

const BUILDER = { style: null, theme: null, games: 'grouped', sections: null, meta: null, pattern: '', catPattern: '', seq: 0 };
let POLL = null;

RENDER.builder = async function () {
  const el = $('v-builder');
  if (STATE.is_personal) return serverOnly(el);
  if (!BUILDER.meta) {
    BUILDER.meta = await apiGet('/api/setup/styles');
    if (!BUILDER.meta) return errorState(el, () => RENDER.builder());
    BUILDER.style = STATE.setup_style || BUILDER.meta.default_style;
    BUILDER.theme = STATE.setup_theme || BUILDER.meta.default_theme;
    BUILDER.pattern = STATE.setup_pattern || '꒰{icon}꒱{name}';
    BUILDER.catPattern = STATE.setup_cat_pattern || '⋆ {title} ⋆';
    BUILDER.sections = BUILDER.meta.sections.map((s) => s.key);
  }
  const m = BUILDER.meta;
  const counts = STATE.setup_counts || [0, 0, 0];
  el.innerHTML = head('server builder', 'every category, channel and panel in one go, named your way and hooked up. only the server owner can run it.')
    + `<div class="builder"><div>
      <section class="box"><div class="box-h"><h2>1 · frame</h2><span class="hint">how channel names are wrapped</span></div>
        <div class="picks" role="group" aria-label="divider style">${Object.entries(m.styles).map(([k, s]) => `<button type="button" class="pick" data-style="${k}" aria-pressed="${k === BUILDER.style}"><b>${esc(s.sample)}</b><small>${esc(s.label.toLowerCase())}</small></button>`).join('')}</div>
        <div class="custom-pat" id="b-custom" ${BUILDER.style === 'custom' ? '' : 'hidden'}>
          <div class="field"><label for="b-pat">channel pattern</label><input type="text" id="b-pat" maxlength="40" value="${esc(BUILDER.pattern)}"><span class="hint">needs <code>{name}</code>, can use <code>{icon}</code></span></div>
          <div class="field"><label for="b-cpat">category pattern</label><input type="text" id="b-cpat" maxlength="40" value="${esc(BUILDER.catPattern)}"><span class="hint"><code>{title}</code>, <code>{TITLE}</code> or <code>{icon}</code></span></div>
        </div></section>
      <section class="box"><div class="box-h"><h2>2 · icons</h2><span class="hint">emoji, plain symbols, a color theme or nothing</span></div>
        <div class="picks" role="group" aria-label="icons">${Object.entries(m.themes).map(([k, t]) => `<button type="button" class="pick" data-theme="${k}" aria-pressed="${k === BUILDER.theme}"><b>${esc(t.sample)}</b><small>${esc(t.label.toLowerCase())}</small></button>`).join('')}</div></section>
      <section class="box"><div class="box-h"><h2>3 · what to make</h2><span class="hint">${ic('lock', 'style="width:14px;height:14px;vertical-align:-2px"')} = staff only</span></div>
        <div class="checks">${m.sections.map((s) => `<label><span class="sw"><input type="checkbox" data-section="${s.key}" ${BUILDER.sections.includes(s.key) ? 'checked' : ''}><i></i></span>${esc(s.title)}${s.private ? ' ' + ic('lock', 'style="width:14px;height:14px"') : ''}</label>`).join('')}</div>
        <div style="margin-top:16px"><div class="hint" style="margin-bottom:6px">game channels</div>
          <div class="pill-set" role="group" aria-label="game channels">${[['grouped', '6 shared rooms'], ['per-game', 'one per game'], ['none', 'none']].map(([k, l]) => `<button type="button" data-games="${k}" aria-pressed="${k === BUILDER.games}">${l}</button>`).join('')}</div></div></section>
      <section class="slip"><span class="pip" aria-hidden="true">♠</span><h2>deal it</h2>
        <p class="hint">makes the roles it needs and every channel, locks staff and log channels, connects welcome, levels, logs, tickets, member count and game channels, and posts the rules, role, ticket and casino panels. it never deletes what was already there, and running it again reuses what it made.</p>
        <div class="inline"><button class="btn gold" type="button" id="b-build">${ic('hammer')}Build it</button>
          <button class="btn" type="button" id="b-restyle" ${STATE.setup_built ? '' : 'disabled title="build first"'} style="background:transparent;color:#3b2f1c;border-color:#b8a47c">just rename to this look</button></div>
        <div class="status" id="b-status" aria-live="polite"></div></section>
      <section class="box danger"><div class="box-h"><h2>take it all back</h2><span class="hint">${STATE.setup_built ? `${counts[0]} channels, ${counts[1]} categories, ${counts[2]} roles` : 'nothing built yet'}</span></div>
        <p class="hint">deletes every channel, category and role the builder made, <b>with every message in them</b>, and clears the settings that pointed at them. what you had before stays.</p>
        <button class="btn red" type="button" id="b-undo" ${STATE.setup_built ? '' : 'disabled'}>${ic('trash')}Undo the build</button></section>
    </div>
    <aside class="builder-side"><div class="disc"><div class="disc-h">${esc(STATE.name)}</div><div class="disc-b" id="dp-body"></div></div><p class="hint" id="dp-count" style="text-align:center;margin-top:8px"></p></aside></div>`;
  const pickGroup = (attr, key) => el.querySelectorAll(`[${attr}]`).forEach((b) => b.addEventListener('click', () => {
    BUILDER[key] = b.getAttribute(attr);
    el.querySelectorAll(`[${attr}]`).forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    if (key === 'style') $('b-custom').hidden = BUILDER.style !== 'custom';
    drawPreview();
  }));
  pickGroup('data-style', 'style');
  pickGroup('data-theme', 'theme');
  pickGroup('data-games', 'games');
  let typing;
  ['b-pat', 'b-cpat'].forEach((id) => $(id).addEventListener('input', () => {
    BUILDER.pattern = $('b-pat').value; BUILDER.catPattern = $('b-cpat').value;
    setErr($('b-pat'), BUILDER.pattern.includes('{name}') ? '' : 'needs {name}');
    clearTimeout(typing); typing = setTimeout(drawPreview, 250);
  }));
  el.querySelectorAll('[data-section]').forEach((c) => c.addEventListener('change', () => { BUILDER.sections = [...el.querySelectorAll('[data-section]:checked')].map((x) => x.dataset.section); drawPreview(); }));
  $('b-build').addEventListener('click', () => queueSetup('build'));
  $('b-restyle').addEventListener('click', () => queueSetup('restyle'));
  $('b-undo').addEventListener('click', () => queueSetup('undo'));
  drawPreview();
  showStatus('b-status', STATE.setup_status);
  if (STATE.setup_status && ['queued', 'running'].includes(STATE.setup_status.state)) pollStatus(STATE.setup_status.action === 'roles' ? 'k-status' : 'b-status');
};

function builderBody(action) {
  const b = { action, style: BUILDER.style || 'angle', theme: BUILDER.theme || 'emoji', sections: BUILDER.sections || [], game_layout: BUILDER.games };
  if (BUILDER.style === 'custom') { b.pattern = BUILDER.pattern; b.cat_pattern = BUILDER.catPattern; }
  return b;
}

async function drawPreview() {
  const b = builderBody('build');
  const q = new URLSearchParams({ style: b.style, theme: b.theme, games: b.game_layout, sections: b.sections.join(','), pattern: b.pattern || '', cat_pattern: b.cat_pattern || '' });
  const seq = ++BUILDER.seq;
  const plan = b.sections.length ? await apiGet(`/api/setup/preview?${q}`) : [];
  const box = $('dp-body');
  if (!plan || !box || seq !== BUILDER.seq) return;
  let n = 0;
  box.innerHTML = plan.map((cat) => `<div class="cat">${esc(cat.name)}${cat.private ? ' ' + ic('lock', 'style="width:12px;height:12px"') : ''}</div>`
    + cat.channels.map((c) => { n += 1; return `<div class="ch" title="${c.games ? 'games: ' + esc(c.games.join(', ')) : ''}">${ic(c.kind === 'voice' ? 'vol' : (c.readonly ? 'mega' : 'hash'))}<span>${esc(c.name)}</span></div>`; }).join('')).join('')
    || '<p class="hint" style="padding:12px">pick at least one section</p>';
  $('dp-count').textContent = `${plan.length} categories, ${n} channels`;
}

async function queueSetup(action, extra) {
  if (action === 'build' && !BUILDER.sections.length) { toast('pick at least one section', 'error'); return; }
  if ((action === 'build' || action === 'restyle') && BUILDER.style === 'custom' && !BUILDER.pattern.includes('{name}')) { toast('the channel pattern needs {name}', 'error'); $('b-pat').focus(); return; }
  const ask = {
    build: 'this makes real channels and roles in your server. go ahead?',
    restyle: 'rename everything the builder made to this look?',
    undo: 'this DELETES every channel, category and role the builder made, with all their messages. keep going?',
    roles: 'make the missing roles, color plain ones, and move them all into order?',
  }[action];
  if (!confirm(ask)) return;
  if (action === 'undo' && prompt('type UNDO to really do it') !== 'UNDO') { toast('nothing deleted'); return; }
  const box = action === 'roles' ? 'k-status' : 'b-status';
  const r = await apiPost(`/api/guild/${GID}/setup_request`, Object.assign(builderBody(action), extra || {}));
  if (r) { toast('sent to the bot, it picks it up within 10 seconds', 'ok'); showStatus(box, { state: 'queued', log: ['waiting for the bot…'] }); pollStatus(box); }
}

function showStatus(boxId, st) {
  const box = $(boxId);
  if (!box || !st) return;
  const label = { queued: 'waiting for the bot', running: 'working on it', done: 'done', error: 'something went wrong' }[st.state] || st.state;
  box.innerHTML = `<b class="${esc(st.state)}">${label}</b><pre>${esc((st.log || []).join('\n').replace(/\*\*/g, ''))}</pre>`;
}

function pollStatus(boxId) {
  clearInterval(POLL);
  let tries = 0;
  POLL = setInterval(async () => {
    tries += 1;
    const r = await apiGet(`/api/guild/${GID}/setup_status`);
    if (!r) { if (tries > 5) clearInterval(POLL); return; }
    showStatus(boxId, r.status);
    if (r.status && ['done', 'error'].includes(r.status.state)) {
      clearInterval(POLL);
      ROLES = null; CHANNELS = null; LISTS = null;
      await refresh();
      ['logs', 'games', 'leveling', 'staff', 'builder'].forEach((v) => RENDERED.delete(v));
      go(CURRENT, { force: true, keepHash: true, noScroll: true });
      showStatus(boxId, r.status);
    }
  }, 3000);
}

const RANK_CAN = {
  9: 'everything, plus /setup and wiping the economy', 8: 'hand out roles with dangerous permissions', 7: 'hand out staff ranks, change the prefix',
  6: 'chips commands, /admin, give normal roles', 5: 'ban and unban, 28 day mutes', 4: 'clear warnings, 7 day mutes',
  3: 'kick, lock channels, 1 day mutes', 2: 'slowmode', 1: 'warn, mute up to an hour, purge up to 25',
};
const SIDE_CAN = { dealer: 'chips commands', host: 'giveaways', partners: 'no commands', media: 'no commands' };
const hex = (c) => (c ? '#' + Number(c).toString(16).padStart(6, '0') : '#3a4a41');

RENDER.staff = async function () {
  const el = $('v-staff');
  if (STATE.is_personal) return serverOnly(el);
  const [data] = await Promise.all([apiGet(`/api/guild/${GID}/staff`), loadLists()]);
  if (!data) return errorState(el, () => RENDER.staff());
  const ranks = data.groups.filter((g) => ['staff', 'security'].includes(g.key)).flatMap((g) => g.roles).filter((r) => r.tier).sort((a, b) => b.tier - a.tier);
  const sides = (data.groups.find((g) => g.key === 'crew') || { roles: [] }).roles;
  const ppl = (r) => (r.members == null ? '' : r.members.length ? r.members.map(esc).join(', ') : 'nobody yet');
  const tierChip = (t, color) => `<span class="tier">${chipSvg(color, '')}<span>${t}</span></span>`;
  el.innerHTML = head('staff & roles', 'who can do what, and every role the bot can make for you.')
    + `<div class="cols">
      <section class="box"><div class="box-h"><h2>the ladder</h2><span class="hint">${data.members_loaded ? 'each rank can do everything below it' : 'couldn\'t load members, so names are hidden'}</span></div>
        <div class="ladder">
          <div class="rung">${tierChip(9, '#d6ad4c')}<span class="nm">server owner</span><span class="can">${RANK_CAN[9]}</span></div>
          ${ranks.map((r) => `<div class="rung${r.exists ? '' : ' missing'}">${tierChip(r.tier, hex(r.color))}<span class="nm">${esc(r.name)}</span><span class="can">${RANK_CAN[r.tier]}</span><span class="ppl">${r.exists ? ppl(r) : 'not made yet'}</span></div>`).join('')}
        </div>
        <p class="hint" style="margin:12px 0 0">nobody can act on someone ranked the same or higher. On Break turns a person's staff commands off until they take it off.</p></section>
      <section class="box"><div class="box-h"><h2>side roles</h2><span class="hint">stack on top of a rank</span></div>
        <div class="ladder">${sides.map((r) => `<div class="rung${r.exists ? '' : ' missing'}" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr)"><span class="nm"><span class="swatch" style="background:${hex(r.color)}"></span>${esc(r.name)}</span><span class="can">${r.side ? SIDE_CAN[r.side] : (r.key === 'crew:break' ? 'turns staff commands off' : 'sees staff channels')}</span><span class="ppl" style="grid-column:1/-1">${r.exists ? ppl(r) : 'not made yet'}</span></div>`).join('')}</div></section>
    </div>
    <section class="box"><div class="box-h"><h2>the role kit</h2><span class="hint">${data.found} of ${data.total} are in your server</span></div>
      <div class="kit">${data.groups.map((g) => `<div class="kit-g"><h4>${esc(g.title.toLowerCase())}${g.self ? ' · self-pick' : ''}</h4>${g.roles.map((r) => `<div class="${r.exists ? '' : 'no'}"><span class="swatch" style="background:${hex(r.color)}"></span>${esc(r.name)}</div>`).join('')}</div>`).join('')}</div></section>
    ${data.is_owner ? `<section class="slip"><span class="pip" aria-hidden="true">♣</span><h2>make and sort the roles</h2>
      <p class="hint">makes what's missing, colors roles that have none, puts everything in order under the bot's role (people keep their roles), wires up level and rebirth ranks, and posts the pick-a-role buttons. drag the bot's role to the very top in Discord first.</p>
      <div class="fields" style="grid-template-columns:1fr"><div class="field"><label for="k-ch">post the role buttons in</label><select id="k-ch"></select></div></div>
      <div class="checks" style="margin-bottom:16px">${data.groups.map((g) => `<label><span class="sw"><input type="checkbox" data-kit="${g.key}" checked><i></i></span>${esc(g.title.toLowerCase())}</label>`).join('')}</div>
      <button class="btn gold" type="button" id="k-go">${ic('wand')}Make and sort roles</button>
      <div class="status" id="k-status" aria-live="polite"></div></section>`
      : `<section class="box"><p class="hint" style="margin:0">only the server owner can make roles. they can do it here or with <code>/setup roles</code> in Discord.</p></section>`}`;
  if (data.is_owner) {
    const pc = Object.values(data.panels || {})[0];
    fillSelect('k-ch', textChannels(pc ? pc[0] : '', 'the roles channel, if there is one'));
    $('k-go').addEventListener('click', () => {
      const groups = [...el.querySelectorAll('[data-kit]:checked')].map((x) => x.dataset.kit);
      if (!groups.length) { toast('pick at least one set', 'error'); return; }
      queueSetup('roles', { groups, panel_channel: $('k-ch').value || null });
    });
    if (STATE.setup_status && STATE.setup_status.action === 'roles') showStatus('k-status', STATE.setup_status);
  }
};

RENDER.rebirths = async function () {
  const el = $('v-rebirths');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('rebirths', 'people who cashed in their wealth for a permanent boost. 7 is the most anyone can have.')
    + `<div class="cols">
      <form class="box" id="rr-form" novalidate><div class="box-h"><h2>rebirth roles</h2><span class="hint">reaching a count gives every role at or below it</span></div>
        <div class="ledger-wrap"><table class="ledger"><thead><tr><th>rebirths</th><th>role</th><th></th></tr></thead><tbody id="rr-rows"></tbody></table></div>
        <div class="inline" style="margin-top:12px"><button class="btn sm" type="button" id="rr-add">${ic('plus')}add one</button><button class="btn gold" type="submit">Save rebirth roles</button></div></form>
      <section><h2 class="sec-title">most rebirths</h2><p class="sec-sub">ties go to whoever's richer.</p><div class="board" id="rb-board"><span class="skel"></span></div></section>
    </div>`;
  const [board] = await Promise.all([apiGet(`/api/guild/${GID}/rebirth_leaderboard`), loadLists()]);
  roleRows('rr', STATE.rebirth_roles, 'rebirth_roles', 'rebirth', 0, 7);
  $('rb-board').innerHTML = board === null ? '<p class="hint">couldn\'t load this</p>' : (board.length
    ? `<div class="board-h"><span>player</span><span>rebirths · worth</span></div><ol>${board.map((e) => `<li><span class="nm">${esc(e.name)}</span><span class="vl">${e.rebirths} · ${chips(e.bal + e.bank)}</span></li>`).join('')}</ol>`
    : '<p class="hint" style="margin:0">nobody has rebirthed yet.</p>');
};

const QUICK = ['loan', 'bought', 'banned', 'dashboard', 'giveaway', 'rebirth', 'reset', 'setup'];

RENDER.activity = function () { loadActivity(''); };

async function loadActivity(q) {
  const el = $('v-activity');
  if (!$('a-find')) {
    el.innerHTML = head('activity', 'loans, shop buys, bans, staff and dashboard changes. the newest 500 are kept.')
      + `<div class="filters" role="search"><label class="sr" for="a-find">search the log</label><input type="search" id="a-find" placeholder="search, then press enter">
        <div class="pill-set" role="group" aria-label="quick filters">${QUICK.map((k) => `<button type="button" data-q="${k}" aria-pressed="false">${k}</button>`).join('')}</div>
        <span class="count" id="a-count"></span></div>
      <div class="box" id="a-box"></div>`;
    $('a-find').addEventListener('keydown', (e) => { if (e.key === 'Enter') { setQuick(''); loadActivity(e.target.value.trim()); } });
    el.querySelectorAll('[data-q]').forEach((b) => b.addEventListener('click', () => {
      const on = b.getAttribute('aria-pressed') !== 'true';
      setQuick(on ? b.dataset.q : '');
      $('a-find').value = on ? b.dataset.q : '';
      loadActivity(on ? b.dataset.q : '');
    }));
  }
  const box = $('a-box');
  box.innerHTML = '<span class="skel"></span><br><span class="skel" style="width:70%"></span>';
  const list = await apiGet(`/api/guild/${GID}/activity` + (q ? `?q=${encodeURIComponent(q)}` : ''));
  if (list === null) return errorState(box, () => loadActivity(q));
  $('a-count').textContent = `${list.length} entries`;
  box.innerHTML = list.length
    ? `<ol class="timeline">${list.map((e) => `<li><time datetime="${new Date(e.ts * 1000).toISOString()}">${new Date(e.ts * 1000).toLocaleString()}</time>${esc(e.text)}</li>`).join('')}</ol>`
    : emptyState(q ? `nothing matches "${esc(q)}"` : 'nothing logged yet', '');
}

function setQuick(k) { document.querySelectorAll('#v-activity [data-q]').forEach((x) => x.setAttribute('aria-pressed', String(x.dataset.q === k))); }

RENDER.personal = function () {
  const el = $('v-personal');
  const link = STATE.app_id ? `https://discord.com/oauth2/authorize?client_id=${STATE.app_id}&integration_type=1&scope=applications.commands` : null;
  el.innerHTML = head('personal app', `anyone can add ${esc(BOT)} to their own Discord account and play anywhere, even in servers it isn't in.`)
    + `<div class="cols">
      <section class="slip"><span class="pip" aria-hidden="true">♦</span><h2>turning it on</h2>
        <ol style="padding-left:20px;color:#3b2f1c">
          <li>open the <a href="https://discord.com/developers/applications" target="_blank" rel="noopener" style="color:#6e5216">Discord developer portal</a> and pick ${esc(BOT)}</li>
          <li>under <b>Installation</b>, tick <b>User Install</b></li>
          <li>keep the <code>applications.commands</code> scope for user installs</li>
          <li>share the link below</li>
        </ol>
        ${link ? `<div class="field"><label for="pa-link">install link</label><div class="inline"><input type="text" readonly value="${link}" id="pa-link"><button class="btn gold" type="button" id="pa-copy">${ic('copy')}Copy</button></div></div>` : '<p class="hint">set DISCORD_CLIENT_ID on the dashboard host to get the link here.</p>'}
      </section>
      <section class="box"><div class="box-h"><h2>what works where</h2></div>
        <h3 style="font-size:14px;color:var(--gold);margin-bottom:4px">anywhere</h3>
        <p class="hint">every game, balance, daily, work, crime, bank, loans, shop, business, rebirth, quests, trivia, fishing, profile and help</p>
        <h3 style="font-size:14px;color:var(--gold);margin:14px 0 4px">only in your server</h3>
        <p class="hint">give, rob, bounties, leaderboard, duels, lottery, levels, tickets, reports, every staff command and /setup</p>
        <p class="hint" style="margin:14px 0 0">outside your server everyone plays from one shared personal wallet, so nothing they do touches your server's economy.</p>
      </section>
    </div>`;
  if ($('pa-copy')) $('pa-copy').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('pa-link').value); toast('link copied', 'ok'); } catch (e) { $('pa-link').select(); toast('press ctrl+c to copy'); }
  });
};

RENDER.danger = function () {
  const el = $('v-danger');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('danger zone', 'things you can\'t take back.')
    + `<section class="box danger"><div class="box-h"><h2>remove ${esc(BOT)} from ${esc(STATE.name)}</h2></div>
      <p class="hint">balances stay saved in case you add it back, but nobody can play until you do.</p>
      <form id="leave-form" novalidate><div class="field" style="max-width:360px;margin-bottom:12px"><label for="leave-name">type the server name to confirm</label><input type="text" id="leave-name" autocomplete="off" placeholder="${esc(STATE.name)}"></div>
      <button class="btn red" type="submit">${ic('out')}Remove ${esc(BOT)}</button></form></section>`;
  $('leave-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!setErr($('leave-name'), $('leave-name').value.trim() === STATE.name ? '' : 'that doesn\'t match the server name')) return;
    const r = await withBusy(e.target.querySelector('button'), () => apiPost(`/api/guild/${GID}/leave`, {}));
    if (r) { toast('left the server', 'ok'); window.location.href = '/dashboard'; }
  });
};

async function refresh() {
  const s = await apiGet(`/api/guild/${GID}`);
  if (!s) return;
  STATE = s;
  $('srv-sub').textContent = STATE.is_personal ? 'personal app' : `${STATE.users.length} players`;
  if (RENDERED.has('overview')) RENDER.overview();
  if (RENDERED.has('players')) drawPlayers();
}

const PALETTE = [
  ['overview', 'Overview', 'page'], ['players', 'Players', 'page'], ['bounties', 'Bounties', 'page'], ['economy', 'House rules', 'page'],
  ['games', 'Games', 'page'], ['leveling', 'Welcome & levels', 'page'], ['logs', 'Logs & tickets', 'page'], ['builder', 'Server builder', 'page'],
  ['staff', 'Staff & roles', 'page'], ['rebirths', 'Rebirths', 'page'], ['activity', 'Activity', 'page'], ['personal', 'Personal app', 'page'], ['danger', 'Danger zone', 'page'],
  ['players#bulk-amount', 'give chips to everyone', 'players'], ['economy#s-prefix', 'command prefix', 'house rules'], ['economy#s-tax', 'tax on winnings', 'house rules'],
  ['economy#s-jackpot', 'slots jackpot', 'house rules'], ['economy#s-testmode', 'test mode', 'house rules'], ['games#g-find', 'turn a game on or off', 'games'],
  ['games#env-box', 'server overrides', 'games'], ['leveling#w-msg', 'welcome message', 'welcome'], ['leveling#l-msg', 'level up message', 'levels'],
  ['leveling#lr-rows', 'level roles', 'levels'], ['leveling#mc-tpl', 'member counter', 'welcome'], ['logs#m-staff', 'staff team role', 'logs'],
  ['logs#m-cat', 'ticket category', 'logs'], ['logs#log-form', 'log channels', 'logs'], ['logs#st-on', 'bot status post', 'logs'],
  ['builder#b-build', 'build the server', 'builder'], ['builder#b-undo', 'undo the build', 'builder'], ['staff#k-go', 'make and sort roles', 'staff'],
  ['rebirths#rr-rows', 'rebirth roles', 'rebirths'], ['personal#pa-link', 'personal app install link', 'personal'],
  ['/account', 'your account', 'site'], ['/help', 'help & commands', 'site'], ['/privacy', 'privacy policy', 'site'], ['/dashboard', 'switch server', 'site'],
];

function initPalette() {
  const bg = $('palette');
  const input = $('pal-input');
  const list = $('pal-list');
  let hits = [];
  let sel = 0;
  let lastFocus = null;
  const visible = () => PALETTE.filter(([to]) => !(STATE && STATE.is_personal && SERVER_ONLY.includes(to.split('#')[0])));
  const draw = () => {
    const q = input.value.trim().toLowerCase();
    hits = visible().filter(([, label, g]) => !q || label.toLowerCase().includes(q) || g.includes(q)).slice(0, 12);
    sel = Math.min(sel, Math.max(0, hits.length - 1));
    list.innerHTML = hits.map(([to, label, g], i) => `<li role="option" id="pal-${i}" aria-selected="${i === sel}" data-i="${i}">${esc(label)}<small>${g}</small></li>`).join('') || '<li aria-disabled="true">nothing found</li>';
    input.setAttribute('aria-activedescendant', hits.length ? `pal-${sel}` : '');
    const cur = list.querySelector('[aria-selected=true]');
    if (cur) cur.scrollIntoView({ block: 'nearest' });
  };
  const open = () => { lastFocus = document.activeElement; bg.classList.add('open'); input.value = ''; sel = 0; draw(); input.focus(); };
  const close = () => { bg.classList.remove('open'); if (lastFocus) lastFocus.focus(); };
  const run = (i) => {
    const h = hits[i];
    if (!h) return;
    close();
    const [to] = h;
    if (to.startsWith('/')) { window.location.href = to; return; }
    const [view, anchor] = to.split('#');
    go(view);
    if (anchor) setTimeout(() => {
      const t = $(anchor);
      if (!t) return;
      t.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const f = t.matches('input,textarea,button,select') ? t : t.querySelector('input,textarea,button');
      if (f && !f.hidden) f.focus({ preventScroll: true });
    }, 400);
  };
  $('open-palette').addEventListener('click', open);
  bg.addEventListener('mousedown', (e) => { if (e.target === bg) close(); });
  input.addEventListener('input', () => { sel = 0; draw(); });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); sel = Math.min(hits.length - 1, sel + 1); draw(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); sel = Math.max(0, sel - 1); draw(); }
    else if (e.key === 'Enter') { e.preventDefault(); run(sel); }
    else if (e.key === 'Escape') { e.preventDefault(); close(); }
    else if (e.key === 'Tab') e.preventDefault();
  });
  list.addEventListener('mousedown', (e) => { const li = e.target.closest('[data-i]'); if (li) { e.preventDefault(); run(Number(li.dataset.i)); } });
  document.addEventListener('keydown', (e) => {
    const typing = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName) || document.activeElement.isContentEditable;
    if ((e.key === 'k' && (e.ctrlKey || e.metaKey)) || (e.key === '/' && !typing)) { e.preventDefault(); bg.classList.contains('open') ? close() : open(); }
  });
}

async function init() {
  initPalette();
  STATE = await apiGet(`/api/guild/${GID}`);
  if (!STATE) {
    const el = $('v-overview');
    el.classList.add('on');
    return errorState(el, () => location.reload());
  }
  $('srv-name').textContent = STATE.name;
  $('srv-sub').textContent = STATE.is_personal ? 'personal app' : `${STATE.users.length} players`;
  $('srv-ic').innerHTML = STATE.icon ? `<img src="${STATE.icon}" alt="">` : esc(STATE.name.slice(0, 1).toUpperCase());
  if (STATE.is_personal) document.querySelectorAll('[data-server]').forEach((x) => { x.hidden = true; });
  go((location.hash || '#overview').slice(1), { keepHash: !!location.hash });
}

init();
