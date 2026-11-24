const GID = document.body.dataset.gid;
const BOT = document.body.dataset.botName || 'Gambly';
let STATE = null;
let ROLES = null;
let CHANNELS = null;

const PAGES = ['overview', 'players', 'bounties', 'economy', 'games', 'leveling', 'logs', 'builder', 'staff', 'rebirths', 'activity', 'personal', 'danger'];
const SERVER_ONLY = ['bounties', 'economy', 'games', 'leveling', 'logs', 'builder', 'staff', 'rebirths', 'danger'];
const LAZY = { activity: () => loadActivity(), staff: () => renderStaff() };

function go(name, push) {
  if (!PAGES.includes(name) || (STATE && STATE.is_personal && SERVER_ONLY.includes(name))) name = 'overview';
  PAGES.forEach((p) => document.getElementById('p-' + p).classList.toggle('on', p === name));
  document.querySelectorAll('.nav[data-page]').forEach((b) => b.classList.toggle('on', b.dataset.page === name));
  if (push !== false) history.replaceState(null, '', '#' + name);
  if (LAZY[name]) LAZY[name]();
  window.scrollTo(0, 0);
}

document.querySelectorAll('.nav[data-page]').forEach((b) => b.addEventListener('click', () => go(b.dataset.page)));
window.addEventListener('hashchange', () => { if (STATE) go(location.hash.slice(1), false); });

const $ = (id) => document.getElementById(id);
const chips = (n) => fmtChips(n);

function av(name, url) {
  return url ? `<img src="${url}" alt="">` : escapeHtml((name || '?').slice(0, 1).toUpperCase());
}

function head(title, sub) {
  return `<h1 class="page-title">${title}</h1>${sub ? `<p class="page-sub">${sub}</p>` : ''}`;
}

function panel(title, note, body, cls) {
  return `<div class="panel ${cls || ''}"><div class="panel-head"><h2>${title}</h2>${note ? `<span class="note">${note}</span>` : ''}</div>${body}</div>`;
}

function toggle(id, on, label, attr) {
  return `<label class="toggle-row"><span class="toggle"><input type="checkbox" ${id ? `id="${id}"` : ''} ${attr || ''} ${on ? 'checked' : ''}><i></i></span>${label || ''}</label>`;
}

function serverOnly(el) {
  el.innerHTML = head('not here', '') + `<div class="panel empty">this page is for servers. the personal app ledger doesn't have it.</div>`;
}

let LISTS = null;
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
    return `<option value="">couldn't load the list (check the bot token)</option>`;
  }
  const known = list.some((c) => c.id === selectedId);
  const missing = (selectedId && !known) ? `<option value="${selectedId}" selected>missing (${selectedId}), deleted?</option>` : '';
  const rows = list.map((c) => `<option value="${c.id}" ${selectedId === c.id ? 'selected' : ''}>${prefix}${escapeHtml(c.name)}</option>`).join('');
  return `<option value="">${emptyLabel}</option>${missing}${rows}`;
}

function comboSortKey(text) {
  return text.replace(/^[^a-z0-9]+/i, '').toLowerCase();
}

function enhanceSelect(select) {
  if (!select) return;
  if (select.dataset.comboReady) { if (select._comboRefresh) select._comboRefresh(); return; }
  select.dataset.comboReady = '1';
  const carried = select.getAttribute('style') || '';
  select.style.display = 'none';
  const wrap = document.createElement('div');
  wrap.className = 'combo';
  if (carried) wrap.style.cssText = carried;
  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'combo-trigger';
  trigger.innerHTML = `<span class="combo-label"></span><span class="combo-caret">▾</span>`;
  const label = trigger.querySelector('.combo-label');
  const box = document.createElement('div');
  box.className = 'combo-panel';
  box.innerHTML = `<div class="combo-search"><input type="text" placeholder="type to search"></div>
    <div class="combo-alpha"><button type="button" data-letter="">all</button>${'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('').map((c) => `<button type="button" data-letter="${c}">${c}</button>`).join('')}</div>
    <div class="combo-list"></div>`;
  const search = box.querySelector('input');
  const list = box.querySelector('.combo-list');
  wrap.appendChild(trigger);
  wrap.appendChild(box);
  select.insertAdjacentElement('afterend', wrap);
  let mode = 'contains';
  const current = () => { const o = select.options[select.selectedIndex]; return o ? o.textContent : ''; };
  function draw() {
    const q = search.value.trim().toLowerCase();
    const opts = Array.from(select.options).filter((o) => !q || (mode === 'starts' ? comboSortKey(o.textContent).startsWith(q) : o.textContent.toLowerCase().includes(q)));
    list.innerHTML = opts.length
      ? opts.map((o, i) => `<div class="combo-opt${o.value === select.value ? ' sel' : ''}${i === 0 ? ' hl' : ''}" data-value="${escapeHtml(o.value)}">${escapeHtml(o.textContent)}</div>`).join('')
      : `<div class="combo-empty">nothing matches</div>`;
    list.querySelectorAll('.combo-opt').forEach((r) => r.addEventListener('click', () => pick(r.dataset.value)));
  }
  function pick(v) { select.value = v; select.dispatchEvent(new Event('change')); label.textContent = current(); close(); }
  function open() { wrap.classList.add('open'); mode = 'contains'; search.value = ''; draw(); setTimeout(() => search.focus(), 0); document.addEventListener('mousedown', outside); }
  function close() { wrap.classList.remove('open'); document.removeEventListener('mousedown', outside); }
  function outside(e) { if (!wrap.contains(e.target)) close(); }
  trigger.addEventListener('click', () => (wrap.classList.contains('open') ? close() : open()));
  search.addEventListener('input', () => { mode = 'contains'; draw(); });
  search.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { close(); trigger.focus(); }
    if (e.key === 'Enter') { e.preventDefault(); const h = list.querySelector('.combo-opt'); if (h) pick(h.dataset.value); }
  });
  box.querySelectorAll('.combo-alpha button').forEach((b) => b.addEventListener('click', (e) => {
    e.stopPropagation(); mode = b.dataset.letter ? 'starts' : 'contains'; search.value = b.dataset.letter; draw(); search.focus();
  }));
  label.textContent = current();
  select._comboRefresh = () => { label.textContent = current(); if (wrap.classList.contains('open')) draw(); };
}

function fillSelect(id, html) {
  const s = $(id);
  if (!s) return;
  s.innerHTML = html;
  enhanceSelect(s);
}

const textChannels = (sel, empty) => pickerOptions(CHANNELS ? CHANNELS.text : null, sel, { prefix: '#', emptyLabel: empty || 'none' });
const roleOptions = (sel, empty) => pickerOptions(ROLES, sel, { emptyLabel: empty || 'none' });

function renderOverview() {
  const el = $('p-overview');
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
  const rich = users.slice().sort((a, b) => (b.bal + b.bank) - (a.bal + a.bank)).slice(0, 10);
  const maxRich = rich.length ? Math.max(1, rich[0].bal + rich[0].bank) : 1;
  const share = total ? Math.round(100 * rich.reduce((s, u) => s + u.bal + u.bank, 0) / total) : 0;
  const bw = week.biggest_win;

  el.innerHTML = head(STATE.is_personal ? 'personal app ledger' : 'how the floor looks',
    STATE.is_personal ? 'everyone who plays through the personal app (DMs and other servers) shares this ledger. it never touches a server\'s wallets.' : '')
    + `<div class="hero">
      <div class="stat big">
        <div><div class="n">${chips(total)}</div><div class="l">chips out there right now</div></div>
        <div>
          <div class="bar"><span style="width:${total ? Math.round(100 * wallet / total) : 50}%"></span></div>
          <div class="legend"><span>wallets <b>${chips(wallet)}</b></span><span>banks <b>${chips(bank)}</b></span></div>
        </div>
      </div>
      <div class="stat"><div class="n">${users.length}</div><div class="l">players</div></div>
      <div class="stat good"><div class="n">${chips(played)}</div><div class="l">games this week</div></div>
      <div class="stat ${debt ? 'warn' : ''}"><div class="n">${chips(debt)}</div><div class="l">owed to the house</div></div>
      <div class="stat ${defaulted || banned ? 'bad' : ''}"><div class="n">${defaulted} / ${banned}</div><div class="l">defaulted / banned</div></div>
    </div>
    <div class="split">
      ${panel('this week', 'resets with the weekly tournament', `
        ${bw ? `<div class="bigwin"><div class="n">+${chips(bw.amount)}</div><div><span class="who">${escapeHtml(bw.name || nameOf(bw.user_id))}</span><small>biggest single win so far</small></div></div>`
             : `<div class="empty" style="padding:10px 0 16px">no wins yet this week</div>`}
        <div class="bars">${act.slice(0, 7).map(([uid, n]) => `
          <div class="br"><span class="who">${escapeHtml(nameOf(uid))}</span><span class="tr"><span class="mint" style="width:${Math.max(4, Math.round(100 * n / maxAct))}%"></span></span><span class="v">${n}</span></div>`).join('')
          || '<div class="empty">nobody has played yet</div>'}</div>`)}
      ${panel('who has the chips', rich.length ? `top 10 hold ${share}%` : '', `
        <div class="bars">${rich.map((u) => `
          <div class="br"><span class="who">${escapeHtml(u.name)}</span><span class="tr"><span style="width:${Math.max(3, Math.round(100 * (u.bal + u.bank) / maxRich))}%"></span></span><span class="v">${chips(u.bal + u.bank)}</span></div>`).join('')
          || '<div class="empty">no players yet</div>'}</div>`)}
    </div>`;
}

function renderPlayers() {
  const el = $('p-players');
  el.innerHTML = head('players', 'edit wallets and banks straight in the table, then hit save on that row.')
    + panel('give or take from everyone', 'hits every player here at once. use a minus number to take chips.', `
      <div class="row" style="max-width:420px">
        <input type="number" id="bulk-amount" placeholder="like 500 or -200">
        <button class="b b-go" id="bulk-go"><i data-lucide="send"></i>Apply to all</button>
      </div>`)
    + panel('everyone', `<span class="row"><input type="search" id="player-find" placeholder="search players" style="width:220px"><a class="b b-sm" href="/api/guild/${GID}/export.csv"><i data-lucide="download"></i>CSV</a></span>`, `
      <div class="tbl-wrap"><table class="tbl">
        <thead><tr><th>player</th><th class="n">wallet</th><th class="n">bank</th><th class="n">loan</th><th class="n">rebirths</th><th></th><th></th></tr></thead>
        <tbody id="players-body"></tbody>
      </table></div>`);
  $('bulk-go').addEventListener('click', async () => {
    const amount = Number($('bulk-amount').value);
    if (!amount) { toast('put in a number first', 'error'); return; }
    if (!confirm(`${amount > 0 ? 'give' : 'take'} ${chips(Math.abs(amount))} chips ${amount > 0 ? 'to' : 'from'} all ${STATE.users.length} players?`)) return;
    const r = await apiPost(`/api/guild/${GID}/bulk_grant`, { amount });
    if (r) { toast(`done, ${r.affected} players changed`, 'ok'); refresh(); }
  });
  $('player-find').addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    document.querySelectorAll('#players-body tr[data-uid]').forEach((tr) => {
      tr.style.display = !q || tr.dataset.search.includes(q) ? '' : 'none';
    });
  });
  renderPlayerRows();
  icons();
}

function renderPlayerRows() {
  const body = $('players-body');
  if (!body) return;
  if (!STATE.users.length) { body.innerHTML = `<tr><td colspan="7" class="empty">nobody has played here yet</td></tr>`; return; }
  const srv = !STATE.is_personal;
  body.innerHTML = STATE.users.map((u) => `
    <tr data-uid="${u.id}" data-search="${escapeHtml((u.name + ' ' + u.id).toLowerCase())}">
      <td class="who"><b>${escapeHtml(u.name)}</b><small>${u.id}</small></td>
      <td class="n"><input type="number" value="${u.bal}" data-field="bal"></td>
      <td class="n"><input type="number" value="${u.bank}" data-field="bank"></td>
      <td class="n">${u.loan_owed ? `${chips(u.loan_owed)}${u.loan_defaulted ? ' <span class="tag bad">defaulted</span>' : ''}` : '<small class="sub">none</small>'}</td>
      <td class="n">${u.rebirths || '<small class="sub">0</small>'}</td>
      <td>${u.is_manager ? '<span class="tag hot">manager</span> ' : ''}${u.is_banned ? '<span class="tag bad">banned</span>' : ''}</td>
      <td><div class="acts">
        <button class="b b-sm b-go" data-act="save">Save</button>
        ${srv ? `<button class="b b-sm" data-act="ban">${u.is_banned ? 'Unban' : 'Ban from games'}</button>` : ''}
        ${srv ? `<button class="b b-sm" data-act="manager">${u.is_manager ? 'Remove manager' : 'Make manager'}</button>` : ''}
        ${u.loan_owed ? '<button class="b b-sm" data-act="forgive">Forgive loan</button>' : ''}
        <button class="b b-sm b-bad" data-act="reset">Reset</button>
      </div></td>
    </tr>`).join('');
  body.querySelectorAll('button[data-act]').forEach((b) => b.addEventListener('click', () => playerAction(b)));
}

async function playerAction(btn) {
  const row = btn.closest('tr');
  const uid = row.dataset.uid;
  const u = STATE.users.find((x) => x.id === uid);
  const act = btn.dataset.act;
  if (act === 'save') {
    const bal = Number(row.querySelector('[data-field=bal]').value);
    const bank = Number(row.querySelector('[data-field=bank]').value);
    let ok = true;
    if (bal !== u.bal) ok = ok && !!(await apiPost(`/api/guild/${GID}/balance`, { user_id: uid, balance: bal }));
    if (bank !== u.bank) ok = ok && !!(await apiPost(`/api/guild/${GID}/bank`, { user_id: uid, bank }));
    if (ok) { toast(`saved ${u.name}`, 'ok'); refresh(); }
  } else if (act === 'ban') {
    const r = await apiPost(`/api/guild/${GID}/ban/${uid}`, { banned: !u.is_banned });
    if (r) { toast(u.is_banned ? `${u.name} can play again` : `${u.name} is banned from the games`, 'ok'); refresh(); }
  } else if (act === 'manager') {
    const r = await apiPost(`/api/guild/${GID}/manager/${uid}`, { manager: !u.is_manager });
    if (r) { toast(u.is_manager ? `${u.name} isn't a manager anymore` : `${u.name} is a manager now`, 'ok'); refresh(); }
  } else if (act === 'forgive') {
    if (!confirm(`wipe ${u.name}'s ${chips(u.loan_owed)} chip loan?`)) return;
    const r = await apiPost(`/api/guild/${GID}/forgive/${uid}`, {});
    if (r) { toast('loan wiped', 'ok'); refresh(); }
  } else if (act === 'reset') {
    if (!confirm(`reset ${u.name} back to a brand new account? there's no undo.`)) return;
    const r = await apiPost(`/api/guild/${GID}/reset/${uid}`, {});
    if (r) { toast(`${u.name} is starting over`, 'ok'); refresh(); }
  }
}

function renderBounties() {
  const el = $('p-bounties');
  if (STATE.is_personal) return serverOnly(el);
  const list = Object.entries(STATE.bounties || {});
  el.innerHTML = head('bounties', 'chips on someone\'s head. whoever robs them first gets it.')
    + panel('put a bounty out', 'use their user id. 0 clears it.', `
      <div class="row" style="max-width:520px">
        <input type="text" id="b-uid" placeholder="user id">
        <input type="number" id="b-amount" placeholder="chips" style="max-width:150px">
        <button class="b b-go" id="b-set">Set</button>
      </div>`)
    + panel('open bounties', '', `
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>target</th><th class="n">on their head</th><th></th></tr></thead>
      <tbody>${list.map(([uid, amt]) => {
        const u = STATE.users.find((x) => x.id === uid);
        return `<tr><td class="who"><b>${escapeHtml(u ? u.name : uid)}</b><small>${uid}</small></td><td class="n">${chips(amt)}</td>
          <td><div class="acts"><button class="b b-sm b-bad" data-clear="${uid}">Clear</button></div></td></tr>`;
      }).join('') || '<tr><td colspan="3" class="empty">no bounties out right now</td></tr>'}</tbody></table></div>`);
  $('b-set').addEventListener('click', async () => {
    const uid = $('b-uid').value.trim();
    if (!uid) { toast('need a user id', 'error'); return; }
    const r = await apiPost(`/api/guild/${GID}/bounty`, { user_id: uid, amount: Number($('b-amount').value || 0) });
    if (r) { toast('bounty set', 'ok'); refresh(); }
  });
  el.querySelectorAll('[data-clear]').forEach((b) => b.addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/bounty`, { user_id: b.dataset.clear, amount: 0 });
    if (r) { toast('cleared', 'ok'); refresh(); }
  }));
}

async function renderEconomy() {
  const el = $('p-economy');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('economy', 'the knobs that change how much money moves around.')
    + panel('basics', '', `
      <div class="grid2">
        <div class="fld"><label>command prefix</label><input type="text" id="s-prefix" maxlength="3" value="${escapeHtml(STATE.prefix)}">
          <span class="help">for the <code>!</code> commands. slash commands don't care.</span></div>
        <div class="fld"><label>manager role (old system)</label><select id="s-manager-role"></select>
          <span class="help">people with this can manage chips. the Dealer rank on Staff &amp; roles does the same thing.</span></div>
      </div>
      <button class="b b-go" id="s-basic-save">Save</button>`)
    + panel('money', '', `
      <div class="grid2">
        <div class="fld"><label>slots jackpot</label><input type="number" id="s-jackpot" value="${STATE.jackpot}"></div>
        <div class="fld"><label>tax on winnings (%)</label><input type="number" id="s-tax" min="0" max="100" value="${STATE.tax_pct}">
          <span class="help">skimmed off profits only, goes into the server pot</span></div>
        <div class="fld"><label>server pot</label><input type="number" id="s-pot" value="${STATE.server_pot}"></div>
        <div class="fld"><label>lottery pot</label><input type="number" id="s-lottery" value="${STATE.lottery_pot}"></div>
      </div>
      ${toggle('s-testmode', STATE.testmode, 'test mode: the owner\'s own bets always win. nobody else is affected.')}
      <button class="b b-go" id="s-money-save">Save</button>`);
  $('s-basic-save').addEventListener('click', async () => {
    const a = await apiPost(`/api/guild/${GID}/prefix`, { prefix: $('s-prefix').value || '!' });
    const b = await apiPost(`/api/guild/${GID}/manager_role`, { role_id: $('s-manager-role').value || null });
    if (a && b) toast('saved', 'ok');
  });
  $('s-money-save').addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/config`, {
      jackpot: Number($('s-jackpot').value), tax_pct: Number($('s-tax').value),
      server_pot: Number($('s-pot').value), lottery_pot: Number($('s-lottery').value), testmode: $('s-testmode').checked,
    });
    if (r) toast('saved', 'ok');
  });
  await loadLists();
  fillSelect('s-manager-role', roleOptions(STATE.manager_role));
}

async function renderGames() {
  const el = $('p-games');
  if (STATE.is_personal) return serverOnly(el);
  const games = STATE.game_list || [];
  const groupOf = {};
  Object.entries(STATE.game_groups || {}).forEach(([g, l]) => l.forEach((x) => { groupOf[x] = g; }));
  const off = new Set(STATE.disabled_games || []);
  const sorted = games.slice().sort((a, b) => (groupOf[a] || 'zz').localeCompare(groupOf[b] || 'zz') || a.localeCompare(b));
  el.innerHTML = head('games', `${games.filter((g) => !off.has(g)).length} of ${games.length} switched on. you can also lock each one to a channel.`)
    + panel('every game', '', `
      <div class="row" style="margin-bottom:12px">
        <input type="search" id="g-find" placeholder="find a game" style="max-width:260px">
        <button class="b b-sm" id="g-all-on">all on</button><button class="b b-sm" id="g-all-off">all off</button>
      </div>
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>on</th><th>game</th><th>room</th><th>channel</th></tr></thead>
      <tbody>${sorted.map((g) => `
        <tr data-game="${g}">
          <td><span class="toggle"><input type="checkbox" data-on ${off.has(g) ? '' : 'checked'}><i></i></span></td>
          <td><b>${escapeHtml(g)}</b></td>
          <td><span class="tag">${escapeHtml(groupOf[g] || 'own channel')}</span></td>
          <td><select data-ch style="min-width:220px"><option>loading…</option></select></td>
        </tr>`).join('')}</tbody></table></div>
      <button class="b b-go" id="g-save" style="margin-top:14px">Save</button>`)
    + panel('server overrides', 'one KEY=value per line. checked before the bot\'s own .env for this server.', `
      <textarea id="env-box" rows="7" style="font-family:ui-monospace,Consolas,monospace" placeholder="SOME_KEY=some value"></textarea>
      <button class="b b-go" id="env-save" style="margin-top:12px">Save</button>`);
  $('env-box').value = Object.entries(STATE.custom_env || {}).map(([k, v]) => `${k}=${v}`).join('\n');
  $('g-find').addEventListener('input', (e) => {
    const q = e.target.value.trim().toLowerCase();
    el.querySelectorAll('tr[data-game]').forEach((r) => { r.style.display = !q || r.textContent.toLowerCase().includes(q) ? '' : 'none'; });
  });
  const setAll = (v) => el.querySelectorAll('[data-on]').forEach((c) => { c.checked = v; });
  $('g-all-on').addEventListener('click', () => setAll(true));
  $('g-all-off').addEventListener('click', () => setAll(false));
  $('g-save').addEventListener('click', async () => {
    const chans = {};
    const disabled = [];
    el.querySelectorAll('tr[data-game]').forEach((r) => {
      chans[r.dataset.game] = r.querySelector('[data-ch]').value || null;
      if (!r.querySelector('[data-on]').checked) disabled.push(r.dataset.game);
    });
    const a = await apiPost(`/api/guild/${GID}/game_channels`, { game_channels: chans });
    const b = await apiPost(`/api/guild/${GID}/disabled_games`, { disabled_games: disabled });
    if (a && b) { toast('saved', 'ok'); await refresh(); renderGames(); }
  });
  $('env-save').addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/custom_env`, { raw: $('env-box').value });
    if (r) { toast('saved', 'ok'); refresh(); }
  });
  await loadLists();
  el.querySelectorAll('tr[data-game]').forEach((r) => {
    const s = r.querySelector('[data-ch]');
    s.innerHTML = textChannels((STATE.game_channels || {})[r.dataset.game], 'find it by name');
    enhanceSelect(s);
  });
}

async function renderLeveling() {
  const el = $('p-leveling');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('welcome & levels', 'what happens when people join, and how they rank up by chatting.')
    + panel('welcome message', '', `
      ${toggle('w-on', STATE.welcome_enabled, 'post a welcome when someone joins')}
      <div class="grid2"><div class="fld"><label>channel</label><select id="w-ch"></select></div></div>
      <div class="fld"><label>message</label>
        <textarea id="w-msg" rows="3" placeholder="welcome {user} to {server}! you're member #{membercount}">${escapeHtml(STATE.welcome_message || '')}</textarea>
        <span class="help">you can use <code>{user}</code> <code>{username}</code> <code>{server}</code> <code>{membercount}</code>. blank uses the default. WELCOME_MESSAGE in .env wins over this.</span></div>
      <button class="b b-go" id="w-save" style="margin-top:12px">Save</button>`)
    + `<div class="split">`
    + panel('levels', '', `
      ${toggle('l-on', STATE.leveling_enabled, 'give xp for chatting and post level ups')}
      <div class="fld" style="margin-bottom:12px"><label>level up channel</label><select id="l-ch"></select></div>
      <div class="fld"><label>level up message</label>
        <textarea id="l-msg" rows="2" placeholder="{user} just hit level {level}!">${escapeHtml(STATE.level_message || '')}</textarea>
        <span class="help"><code>{user}</code> <code>{username}</code> <code>{server}</code> <code>{level}</code>. LEVEL_UP_MESSAGE in .env wins.</span></div>
      <button class="b b-go" id="l-save" style="margin-top:12px">Save</button>`)
    + panel('top chatters', '', `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>player</th><th class="n">level</th><th class="n">xp</th></tr></thead><tbody id="lvl-board"><tr><td colspan="3" class="empty">loading…</td></tr></tbody></table></div>`)
    + `</div>`
    + panel('level roles', 'hitting a level gives every role at or below it. nothing gets taken away.', `
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>level</th><th>role</th><th></th></tr></thead><tbody id="lr-rows"></tbody></table></div>
      <div class="row" style="margin-top:12px"><button class="b b-sm" id="lr-add"><i data-lucide="plus"></i>add a level</button><button class="b b-go" id="lr-save">Save</button></div>`)
    + panel('member counter', 'renames a voice channel to the live member count. updates on joins and leaves, and every 10 minutes.', `
      ${toggle('mc-on', STATE.member_count_enabled, 'keep the counter going')}
      <div class="grid2">
        <div class="fld"><label>voice channel</label><select id="mc-ch"></select></div>
        <div class="fld"><label>name</label><input type="text" id="mc-tpl" value="${escapeHtml(STATE.member_count_template || '')}" placeholder="Members: {count}"></div>
      </div>
      <button class="b b-go" id="mc-save">Save</button>`);
  icons();
  $('w-save').addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/welcome_config`, { welcome_enabled: $('w-on').checked, welcome_channel_id: $('w-ch').value || null, welcome_message: $('w-msg').value });
    if (r) { toast('saved', 'ok'); refresh(); }
  });
  $('l-save').addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/leveling_config`, { leveling_enabled: $('l-on').checked, level_channel_id: $('l-ch').value || null, level_message: $('l-msg').value });
    if (r) { toast('saved', 'ok'); refresh(); }
  });
  $('mc-save').addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/member_count_config`, { member_count_enabled: $('mc-on').checked, member_count_channel_id: $('mc-ch').value || null, member_count_template: $('mc-tpl').value });
    if (r) { toast('saved', 'ok'); refresh(); }
  });
  const [board] = await Promise.all([apiGet(`/api/guild/${GID}/level_leaderboard`), loadLists()]);
  fillSelect('w-ch', textChannels(STATE.welcome_channel_id));
  fillSelect('l-ch', textChannels(STATE.level_channel_id));
  fillSelect('mc-ch', pickerOptions(CHANNELS ? CHANNELS.voice : null, STATE.member_count_channel_id));
  roleRows('lr-rows', 'lr-add', 'lr-save', STATE.level_roles, 'level_roles', 'level', 0, 1000);
  $('lvl-board').innerHTML = (board && board.length)
    ? board.map((e) => `<tr><td>${escapeHtml(e.name)}</td><td class="n">${e.level}</td><td class="n">${e.total_xp.toLocaleString()}</td></tr>`).join('')
    : '<tr><td colspan="3" class="empty">nobody has xp yet</td></tr>';
}

function roleRows(bodyId, addId, saveId, current, key, word, min, max) {
  const body = $(bodyId);
  const add = (n, rid) => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td><input type="number" min="${min}" max="${max}" class="rr-n" value="${n ?? ''}" style="width:90px"></td>
      <td><select class="rr-role" style="min-width:220px">${roleOptions(rid, 'pick a role')}</select></td>
      <td><div class="acts"><button class="b b-sm b-bad">Remove</button></div></td>`;
    tr.querySelector('.b-bad').addEventListener('click', () => tr.remove());
    body.appendChild(tr);
    enhanceSelect(tr.querySelector('.rr-role'));
  };
  const rows = Object.entries(current || {}).sort((a, b) => Number(a[0]) - Number(b[0]));
  body.innerHTML = '';
  if (rows.length) rows.forEach(([n, rid]) => add(n, rid));
  else body.innerHTML = `<tr><td colspan="3" class="empty">no ${word} roles yet</td></tr>`;
  $(addId).onclick = () => { if (body.querySelector('td.empty')) body.innerHTML = ''; add('', ''); };
  $(saveId).onclick = async () => {
    const out = {};
    body.querySelectorAll('tr').forEach((tr) => {
      const n = tr.querySelector('.rr-n');
      const s = tr.querySelector('.rr-role');
      if (n && s && n.value.trim() !== '' && s.value) out[n.value.trim()] = s.value;
    });
    const r = await apiPost(`/api/guild/${GID}/${key}`, { [key]: out });
    if (r) { toast('saved', 'ok'); refresh(); }
  };
}

const LOG_TYPES = [
  { key: 'mod', label: 'staff actions', desc: 'kicks, bans, mutes, warns, purges, locks' },
  { key: 'ticket', label: 'ticket transcripts', desc: 'sent when a ticket closes' },
  { key: 'report', label: 'reports', desc: '/report and right click → Report Message' },
  { key: 'message', label: 'edits & deletes', desc: 'gets busy in an active server' },
  { key: 'withdraw', label: 'withdrawals', desc: 'bank to wallet' },
  { key: 'deposit', label: 'deposits', desc: 'wallet to bank' },
];

async function renderLogs() {
  const el = $('p-logs');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('logs & tickets', 'where staff stuff gets posted, and how tickets work.')
    + panel('tickets', '', `
      <div class="grid2">
        <div class="fld"><label>staff team role</label><select id="m-staff"></select>
          <span class="help">lets people see tickets and staff panels. what they're allowed to do comes from their rank on Staff &amp; roles.</span></div>
        <div class="fld"><label>ticket category</label><select id="m-cat"></select><span class="help">new tickets open in here</span></div>
        <div class="fld"><label>ping on new tickets</label><select id="m-ping"></select><span class="help">optional</span></div>
      </div>
      <button class="b b-go" id="m-save">Save</button>`)
    + panel('logs', 'each one posts to its own channel. turn on what you want.', `
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>what</th><th>on</th><th>channel</th></tr></thead>
      <tbody>${LOG_TYPES.map((t) => `
        <tr data-log="${t.key}"><td class="who"><b>${t.label}</b><small>${t.desc}</small></td>
          <td><span class="toggle"><input type="checkbox" data-log-on ${STATE.logging[t.key].enabled ? 'checked' : ''}><i></i></span></td>
          <td><select data-log-ch style="min-width:220px"><option>loading…</option></select></td></tr>`).join('')}</tbody></table></div>
      <button class="b b-go" id="log-save" style="margin-top:14px">Save</button>`)
    + panel('bot status post', 'one message the bot keeps editing every few minutes with uptime, ping and chips. /status works anytime too.', `
      ${toggle('st-on', STATE.status_enabled, 'keep a status post going')}
      <div class="grid2"><div class="fld"><label>channel</label><select id="st-ch"></select></div></div>
      <button class="b b-go" id="st-save">Save</button>`);
  $('m-save').addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/moderation_config`, { staff_role_id: $('m-staff').value || null, ticket_category_id: $('m-cat').value || null, ticket_ping_role_id: $('m-ping').value || null });
    if (r) { toast('saved', 'ok'); refresh(); }
  });
  $('log-save').addEventListener('click', async () => {
    const body = {};
    el.querySelectorAll('tr[data-log]').forEach((r) => {
      body[`log_${r.dataset.log}_enabled`] = r.querySelector('[data-log-on]').checked;
      body[`log_${r.dataset.log}_channel`] = r.querySelector('[data-log-ch]').value || null;
    });
    const r = await apiPost(`/api/guild/${GID}/moderation_config`, body);
    if (r) { toast('saved', 'ok'); refresh(); }
  });
  $('st-save').addEventListener('click', async () => {
    const r = await apiPost(`/api/guild/${GID}/status_config`, { status_enabled: $('st-on').checked, status_channel_id: $('st-ch').value || null });
    if (r) { toast('saved', 'ok'); refresh(); }
  });
  await loadLists();
  fillSelect('m-staff', roleOptions(STATE.staff_role_id));
  fillSelect('m-cat', pickerOptions(CHANNELS ? CHANNELS.categories : null, STATE.ticket_category_id));
  fillSelect('m-ping', roleOptions(STATE.ticket_ping_role_id));
  fillSelect('st-ch', textChannels(STATE.status_channel_id));
  el.querySelectorAll('tr[data-log]').forEach((r) => {
    const s = r.querySelector('[data-log-ch]');
    s.innerHTML = textChannels(STATE.logging[r.dataset.log].channel);
    enhanceSelect(s);
  });
}

const BUILDER = { style: null, theme: null, games: 'grouped', sections: null, meta: null, pattern: '', catPattern: '', seq: 0 };
let POLL = null;

async function renderBuilder() {
  const el = $('p-builder');
  if (STATE.is_personal) return serverOnly(el);
  if (!BUILDER.meta) {
    BUILDER.meta = await apiGet('/api/setup/styles');
    if (!BUILDER.meta) return;
    BUILDER.style = STATE.setup_style || BUILDER.meta.default_style;
    BUILDER.theme = STATE.setup_theme || BUILDER.meta.default_theme;
    BUILDER.pattern = STATE.setup_pattern || '꒰{icon}꒱{name}';
    BUILDER.catPattern = STATE.setup_cat_pattern || '⋆ {title} ⋆';
    BUILDER.sections = BUILDER.meta.sections.map((s) => s.key);
  }
  const m = BUILDER.meta;
  const counts = STATE.setup_counts || [0, 0, 0];
  el.innerHTML = head('server builder', 'makes every category, channel and panel in one go, names them in your style, and hooks them all up. only the server owner can run it.')
    + `<div class="builder"><div>`
    + panel('divider style', 'how channel names get framed', `
      <div class="picks">${Object.entries(m.styles).map(([k, s]) => `<button class="pick${k === BUILDER.style ? ' on' : ''}" data-style="${k}"><b>${escapeHtml(s.sample)}</b><small>${escapeHtml(s.label.toLowerCase())}</small></button>`).join('')}</div>
      <div id="b-custom" class="custom-pattern" style="${BUILDER.style === 'custom' ? '' : 'display:none'}">
        <div class="fld"><label>channel pattern</label><input type="text" id="b-pat" maxlength="40" value="${escapeHtml(BUILDER.pattern)}">
          <span class="help">needs <code>{name}</code>, can use <code>{icon}</code>. try <code>꒰{icon}꒱{name}</code> or <code>⊹ {name}</code></span></div>
        <div class="fld"><label>category pattern</label><input type="text" id="b-cpat" maxlength="40" value="${escapeHtml(BUILDER.catPattern)}">
          <span class="help"><code>{title}</code> or <code>{TITLE}</code> for caps, plus <code>{icon}</code></span></div>
      </div>`)
    + panel('icons', 'emoji, plain symbols, a color theme, or nothing', `
      <div class="picks">${Object.entries(m.themes).map(([k, t]) => `<button class="pick${k === BUILDER.theme ? ' on' : ''}" data-theme="${k}"><b>${escapeHtml(t.sample)}</b><small>${escapeHtml(t.label.toLowerCase())}</small></button>`).join('')}</div>`)
    + panel('what to make', 'the locked ones are only visible to staff', `
      <div class="checks">${m.sections.map((s) => `<label><span class="toggle"><input type="checkbox" data-section="${s.key}" ${BUILDER.sections.includes(s.key) ? 'checked' : ''}><i></i></span>${escapeHtml(s.title)}${s.private ? ' <i data-lucide="lock" style="width:14px;height:14px"></i>' : ''}</label>`).join('')}</div>
      <div style="margin-top:16px"><div class="help" style="margin-bottom:6px">game channels</div>
      <div class="seg">${[['grouped', '6 shared rooms'], ['per-game', 'one per game'], ['none', 'none']].map(([k, l]) => `<button data-games="${k}" class="${k === BUILDER.games ? 'on' : ''}">${l}</button>`).join('')}</div></div>`)
    + panel('go', '', `
      <p class="help" style="margin-top:0">makes the roles it needs, every channel, locks staff and log channels, connects welcome, levels, logs, tickets, member count and game channels, and posts the rules, role, ticket and casino panels. it never deletes anything that was already there, and running it again reuses what it made.</p>
      <div class="row"><button class="b b-go" id="b-build"><i data-lucide="hammer"></i>Build it</button>
        <button class="b" id="b-restyle" ${STATE.setup_built ? '' : 'disabled title="build first"'}>Just rename to this look</button></div>
      <div id="b-status" class="status-box"></div>`)
    + panel('take it all back', STATE.setup_built ? `${counts[0]} channels, ${counts[1]} categories, ${counts[2]} roles` : 'nothing built yet', `
      <p class="help" style="margin-top:0">deletes every channel, category and role the builder made, <b>messages in them included</b>, and clears the settings that pointed at them. anything you had before stays. no undo for the undo.</p>
      <button class="b b-bad" id="b-undo" ${STATE.setup_built ? '' : 'disabled'}><i data-lucide="trash-2"></i>Undo the build</button>`, 'bad')
    + `</div><div class="builder-preview"><div class="discord-preview"><div class="dp-head">${escapeHtml(STATE.name)}<span>▾</span></div><div class="dp-body" id="dp-body"></div></div>
       <p class="help" id="dp-count" style="text-align:center"></p></div></div>`;
  icons();
  const pickGroup = (attr, key) => el.querySelectorAll(`[${attr}]`).forEach((b) => b.addEventListener('click', () => {
    BUILDER[key] = b.getAttribute(attr);
    el.querySelectorAll(`[${attr}]`).forEach((x) => x.classList.toggle('on', x === b));
    if (key === 'style') $('b-custom').style.display = BUILDER.style === 'custom' ? '' : 'none';
    drawPreview();
  }));
  pickGroup('data-style', 'style');
  pickGroup('data-theme', 'theme');
  pickGroup('data-games', 'games');
  let typing;
  ['b-pat', 'b-cpat'].forEach((id) => $(id).addEventListener('input', () => {
    BUILDER.pattern = $('b-pat').value;
    BUILDER.catPattern = $('b-cpat').value;
    clearTimeout(typing); typing = setTimeout(drawPreview, 250);
  }));
  el.querySelectorAll('[data-section]').forEach((c) => c.addEventListener('change', () => {
    BUILDER.sections = [...el.querySelectorAll('[data-section]:checked')].map((x) => x.dataset.section);
    drawPreview();
  }));
  $('b-build').addEventListener('click', () => queueSetup('build'));
  $('b-restyle').addEventListener('click', () => queueSetup('restyle'));
  $('b-undo').addEventListener('click', () => queueSetup('undo'));
  drawPreview();
  showStatus('b-status', STATE.setup_status);
  if (STATE.setup_status && ['queued', 'running'].includes(STATE.setup_status.state)) pollStatus('b-status');
}

function builderBody(action) {
  const b = { action, style: BUILDER.style, theme: BUILDER.theme, sections: BUILDER.sections, game_layout: BUILDER.games };
  if (BUILDER.style === 'custom') { b.pattern = BUILDER.pattern; b.cat_pattern = BUILDER.catPattern; }
  return b;
}

async function drawPreview() {
  const b = builderBody('build');
  const q = new URLSearchParams({ style: b.style, theme: b.theme, games: b.game_layout, sections: b.sections.join(','), pattern: b.pattern || '', cat_pattern: b.cat_pattern || '' });
  const seq = ++BUILDER.seq;
  const plan = BUILDER.sections.length ? await apiGet(`/api/setup/preview?${q}`) : [];
  const box = $('dp-body');
  if (!plan || !box || seq !== BUILDER.seq) return;
  let n = 0;
  box.innerHTML = plan.map((cat) => `
    <div class="dp-cat">${escapeHtml(cat.name)}${cat.private ? '<span class="dp-lock"><i data-lucide="lock" style="width:12px;height:12px"></i></span>' : ''}</div>
    ${cat.channels.map((c) => { n += 1; return `<div class="dp-ch" title="${c.games ? 'games: ' + escapeHtml(c.games.join(', ')) : ''}"><span class="dp-icon"><i data-lucide="${c.kind === 'voice' ? 'volume-2' : (c.readonly ? 'megaphone' : 'hash')}" style="width:15px;height:15px"></i></span><span class="dp-name">${escapeHtml(c.name)}</span></div>`; }).join('')}`).join('')
    || '<div class="empty">pick at least one section</div>';
  $('dp-count').textContent = `${plan.length} categories, ${n} channels`;
  icons();
}

async function queueSetup(action, extra) {
  if (action === 'build' && !BUILDER.sections.length) { toast('pick at least one section', 'error'); return; }
  if ((action === 'build' || action === 'restyle') && BUILDER.style === 'custom' && !BUILDER.pattern.includes('{name}')) { toast('your pattern needs {name} in it', 'error'); return; }
  const ask = {
    build: 'this makes real channels and roles in your server. go?',
    restyle: 'rename everything the builder made to this look?',
    undo: 'this DELETES every channel, category and role the builder made, with all their messages. keep going?',
    roles: 'make the missing roles, color the plain ones, and move them all into order?',
  }[action];
  if (!confirm(ask)) return;
  if (action === 'undo' && prompt('type UNDO to really do it') !== 'UNDO') { toast('ok, nothing deleted'); return; }
  const body = Object.assign(builderBody(action), extra || {});
  if (!body.style) { body.style = 'angle'; body.theme = 'emoji'; }
  const r = await apiPost(`/api/guild/${GID}/setup_request`, body);
  if (r) {
    const box = action === 'roles' ? 'k-status' : 'b-status';
    toast('sent to the bot, it picks it up within 10 seconds', 'ok');
    showStatus(box, { state: 'queued', log: ['waiting for the bot…'] });
    pollStatus(box);
  }
}

function showStatus(boxId, st) {
  const box = $(boxId);
  if (!box || !st) return;
  const label = { queued: 'waiting for the bot', running: 'working on it', done: 'done', error: 'something went wrong' }[st.state] || st.state;
  box.innerHTML = `<div class="status-state ${escapeHtml(st.state)}">${label}</div><pre class="status-log">${escapeHtml((st.log || []).join('\n').replace(/\*\*/g, ''))}</pre>`;
}

function pollStatus(boxId) {
  clearInterval(POLL);
  POLL = setInterval(async () => {
    const r = await apiGet(`/api/guild/${GID}/setup_status`);
    if (!r) return;
    showStatus(boxId, r.status);
    if (r.status && ['done', 'error'].includes(r.status.state)) {
      clearInterval(POLL);
      ROLES = null; CHANNELS = null; LISTS = null;
      STATE = (await apiGet(`/api/guild/${GID}`)) || STATE;
      if (boxId === 'k-status') renderStaff(); else renderBuilder();
      renderLogs(); renderGames(); renderLeveling();
      showStatus(boxId, r.status);
    }
  }, 3000);
}

const RANK_CAN = {
  9: 'everything, plus /setup and wiping the economy',
  8: 'hand out roles with dangerous permissions',
  7: 'hand out staff ranks, change the prefix',
  6: 'chips commands, /admin, give normal roles',
  5: 'ban and unban, 28 day mutes',
  4: 'clear warnings, 7 day mutes',
  3: 'kick, lock channels, 1 day mutes',
  2: 'slowmode',
  1: 'warn, mute up to an hour, purge up to 25',
};
const SIDE_CAN = { dealer: 'chips commands', host: 'giveaways', partners: 'no commands', media: 'no commands' };

async function renderStaff() {
  const el = $('p-staff');
  if (STATE.is_personal) return serverOnly(el);
  if (!el.dataset.ready) el.innerHTML = head('staff & roles', '') + '<div class="panel empty">loading staff…</div>';
  const [data] = await Promise.all([apiGet(`/api/guild/${GID}/staff`), loadLists()]);
  if (!data) return;
  el.dataset.ready = '1';
  const byKey = {};
  data.groups.forEach((g) => g.roles.forEach((r) => { byKey[r.key] = r; }));
  const ranks = data.groups.filter((g) => ['staff', 'security'].includes(g.key)).flatMap((g) => g.roles).filter((r) => r.tier).sort((a, b) => b.tier - a.tier);
  const sides = (data.groups.find((g) => g.key === 'crew') || { roles: [] }).roles;
  const ppl = (r) => (r.members == null ? '' : (r.members.length ? r.members.map(escapeHtml).join(', ') : 'nobody yet'));
  const dot = (c) => `<span class="dot" style="background:${c ? '#' + Number(c).toString(16).padStart(6, '0') : '#e8dce3'}"></span>`;
  el.innerHTML = head('staff & roles', 'who can do what, and every role the bot can set up for you.')
    + `<div class="split">`
    + panel('the ladder', data.members_loaded ? 'higher ranks can do everything below them' : "couldn't load members, so names are hidden", `
      <div class="ladder">
        <div class="rung"><span class="t">9</span><span class="nm">server owner</span><span class="can">${RANK_CAN[9]}</span></div>
        ${ranks.map((r) => `<div class="rung${r.exists ? '' : ' missing'}"><span class="t">${r.tier}</span><span class="nm">${dot(r.color)}${escapeHtml(r.name)}</span><span class="can">${RANK_CAN[r.tier]}</span>${r.exists ? `<span class="ppl">${ppl(r)}</span>` : '<span class="ppl">not made yet</span>'}</div>`).join('')}
      </div>
      <p class="help" style="margin-bottom:0">nobody can act on someone ranked the same or higher. On Break turns a person's staff commands off until they take it off.</p>`)
    + panel('side roles', 'these stack on top of a rank', `
      <div class="ladder">${sides.map((r) => `<div class="rung${r.exists ? '' : ' missing'}" style="grid-template-columns:minmax(0,220px) 1fr"><span class="nm">${dot(r.color)}${escapeHtml(r.name)}</span><span class="can">${r.side ? SIDE_CAN[r.side] : (r.key === 'crew:break' ? 'turns staff commands off' : 'sees staff channels')}</span>${r.exists ? `<span class="ppl" style="grid-column:1/-1">${ppl(r)}</span>` : '<span class="ppl" style="grid-column:1/-1">not made yet</span>'}</div>`).join('')}</div>`)
    + `</div>`
    + panel('role kit', `${data.found} of ${data.total} roles are in your server`, `
      ${data.groups.map((g) => `<div style="margin-bottom:14px"><div class="help" style="font-weight:600;color:var(--ink-2);margin-bottom:4px">${escapeHtml(g.title.toLowerCase())}${g.self ? ' · people pick these themselves' : ''}</div>
        <div class="rolegrid">${g.roles.map((r) => `<div class="${r.exists ? '' : 'no'}" title="${r.exists ? 'in your server' : 'missing'}">${dot(r.color)}${escapeHtml(r.name)}</div>`).join('')}</div></div>`).join('')}`)
    + (data.is_owner ? panel('set them up', 'owner only', `
      <p class="help" style="margin-top:0">makes whatever's missing, colors roles that have no color yet, puts everything in the right order under the bot's role (people keep their roles), wires up level and rebirth ranks, and posts the pick-a-role buttons. drag the bot's role to the very top first.</p>
      <div class="grid2">
        <div class="fld"><label>post the role buttons in</label><select id="k-ch"></select></div>
      </div>
      <div class="checks" style="margin-bottom:14px">${data.groups.map((g) => `<label><span class="toggle"><input type="checkbox" data-kit="${g.key}" checked><i></i></span>${escapeHtml(g.title.toLowerCase())}</label>`).join('')}</div>
      <button class="b b-go" id="k-go"><i data-lucide="wand-sparkles"></i>Make and sort roles</button>
      <div id="k-status" class="status-box"></div>`) : panel('set them up', '', '<p class="help" style="margin:0">only the server owner can run the role setup. ask them, or they can use <code>/setup roles</code> in Discord.</p>'));
  icons();
  if (data.is_owner) {
    const panelCh = Object.values(data.panels || {})[0];
    fillSelect('k-ch', textChannels(panelCh ? panelCh[0] : '', 'the roles channel (if there is one)'));
    $('k-go').addEventListener('click', () => queueSetup('roles', {
      groups: [...el.querySelectorAll('[data-kit]:checked')].map((x) => x.dataset.kit),
      panel_channel: $('k-ch').value || null,
    }));
    if (STATE.setup_status && STATE.setup_status.action === 'roles' && ['queued', 'running'].includes(STATE.setup_status.state)) pollStatus('k-status');
  }
}

async function renderRebirths() {
  const el = $('p-rebirths');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('rebirths', 'people who cashed out their wealth for a permanent boost.')
    + `<div class="split">`
    + panel('rebirth roles', 'reaching a count gives every role at or below it. 7 is the max.', `
      <div class="tbl-wrap"><table class="tbl"><thead><tr><th>rebirths</th><th>role</th><th></th></tr></thead><tbody id="rr-rows"></tbody></table></div>
      <div class="row" style="margin-top:12px"><button class="b b-sm" id="rr-add"><i data-lucide="plus"></i>add one</button><button class="b b-go" id="rr-save">Save</button></div>`)
    + panel('most rebirths', '', `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>player</th><th class="n">rebirths</th><th class="n">worth</th></tr></thead><tbody id="rb-board"><tr><td colspan="3" class="empty">loading…</td></tr></tbody></table></div>`)
    + `</div>`;
  icons();
  const [board] = await Promise.all([apiGet(`/api/guild/${GID}/rebirth_leaderboard`), loadLists()]);
  roleRows('rr-rows', 'rr-add', 'rr-save', STATE.rebirth_roles, 'rebirth_roles', 'rebirth', 0, 7);
  $('rb-board').innerHTML = (board && board.length)
    ? board.map((e) => `<tr><td>${escapeHtml(e.name)}</td><td class="n">${e.rebirths}</td><td class="n">${chips(e.bal + e.bank)}</td></tr>`).join('')
    : '<tr><td colspan="3" class="empty">nobody has rebirthed yet</td></tr>';
}

async function loadActivity(q) {
  const el = $('p-activity');
  el.innerHTML = head('activity', 'loans, shop buys, bans, staff changes and dashboard edits. the last 500.')
    + panel('log', `<input type="search" id="a-find" placeholder="search, then enter" style="width:240px" value="${q ? escapeHtml(q) : ''}">`, '<div class="log" id="a-list"><div class="empty">loading…</div></div>');
  $('a-find').addEventListener('keydown', (e) => { if (e.key === 'Enter') loadActivity(e.target.value.trim()); });
  const list = await apiGet(`/api/guild/${GID}/activity` + (q ? `?q=${encodeURIComponent(q)}` : ''));
  $('a-list').innerHTML = (list && list.length)
    ? list.map((e) => `<div><time>${new Date(e.ts * 1000).toLocaleString()}</time><span>${escapeHtml(e.text)}</span></div>`).join('')
    : '<div class="empty">nothing logged</div>';
}

function renderPersonal() {
  const el = $('p-personal');
  const link = STATE.app_id ? `https://discord.com/oauth2/authorize?client_id=${STATE.app_id}&integration_type=1&scope=applications.commands` : null;
  el.innerHTML = head('personal app', `people can add ${escapeHtml(BOT)} to their own Discord account and play anywhere, even in servers ${escapeHtml(BOT)} isn't in.`)
    + `<div class="split">`
    + panel('turning it on', '', `
      <ol class="steps">
        <li>open the <a href="https://discord.com/developers/applications" target="_blank" rel="noopener">Discord developer portal</a> and pick ${escapeHtml(BOT)}</li>
        <li>go to <b>Installation</b> and tick <b>User Install</b></li>
        <li>under default install settings for user install, keep the <code>applications.commands</code> scope</li>
        <li>share the link below</li>
      </ol>
      ${link ? `<div class="row" style="margin-top:14px"><input type="text" readonly value="${link}" id="pa-link"><button class="b b-go" id="pa-copy"><i data-lucide="copy"></i>Copy</button></div>` : '<p class="help">set DISCORD_CLIENT_ID to get the link here</p>'}`)
    + panel('what works where', '', `
      <div class="help" style="font-weight:600;color:var(--ink-2)">anywhere (DMs, group chats, any server)</div>
      <p style="margin:4px 0 14px">every game, balance, daily, work, crime, bank, loans, shop, business, rebirth, quests, trivia, fishing, profile, help</p>
      <div class="help" style="font-weight:600;color:var(--ink-2)">only in your server</div>
      <p style="margin:4px 0 14px">give, rob, bounties, leaderboard, duels, lottery, levels, tickets, reports, every staff command and /setup</p>
      <p class="help" style="margin:0">outside your server everyone plays from one shared personal wallet, so nothing they do touches your server's economy.</p>`)
    + `</div>`;
  icons();
  if ($('pa-copy')) $('pa-copy').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText($('pa-link').value); toast('copied', 'ok'); } catch (e) { $('pa-link').select(); }
  });
}

function renderDanger() {
  const el = $('p-danger');
  if (STATE.is_personal) return serverOnly(el);
  el.innerHTML = head('danger zone', '')
    + panel(`kick ${escapeHtml(BOT)} out of ${escapeHtml(STATE.name)}`, '', `
      <p class="help" style="margin-top:0">balances stay saved in case you add it back, but nobody can play until you do.</p>
      <button class="b b-bad" id="leave-go"><i data-lucide="log-out"></i>Remove ${escapeHtml(BOT)}</button>`, 'bad');
  icons();
  $('leave-go').addEventListener('click', async () => {
    if (!confirm(`really remove ${BOT} from ${STATE.name}?`)) return;
    const r = await apiPost(`/api/guild/${GID}/leave`, {});
    if (r) { toast('left the server', 'ok'); window.location.href = '/dashboard'; }
  });
}

async function refresh() {
  const s = await apiGet(`/api/guild/${GID}`);
  if (!s) return;
  STATE = s;
  renderOverview();
  renderPlayerRows();
  renderBounties();
}

const FIND = [
  ['give chips to everyone', 'players', '#bulk-amount'], ['export players', 'players', 'a[href*="export.csv"]'],
  ['command prefix', 'economy', '#s-prefix'], ['manager role', 'economy', '#s-manager-role'], ['jackpot', 'economy', '#s-jackpot'],
  ['tax', 'economy', '#s-tax'], ['server pot', 'economy', '#s-pot'], ['lottery pot', 'economy', '#s-lottery'], ['test mode', 'economy', '#s-testmode'],
  ['turn games on or off', 'games', '#g-find'], ['game channels', 'games', '#g-find'], ['server overrides / env', 'games', '#env-box'],
  ['welcome message', 'leveling', '#w-msg'], ['welcome channel', 'leveling', '#w-ch'], ['level ups', 'leveling', '#l-msg'],
  ['level roles', 'leveling', '#lr-rows'], ['member counter', 'leveling', '#mc-tpl'],
  ['staff team role', 'logs', '#m-staff'], ['ticket category', 'logs', '#m-cat'], ['ticket ping', 'logs', '#m-ping'],
  ['logs', 'logs', 'tr[data-log]'], ['bot status post', 'logs', '#st-ch'],
  ['server builder', 'builder', '.picks'], ['divider style', 'builder', '.picks'], ['undo build', 'builder', '#b-undo'],
  ['staff ranks', 'staff', '.ladder'], ['role kit / make roles', 'staff', '.rolegrid'],
  ['rebirth roles', 'rebirths', '#rr-rows'], ['bounties', 'bounties', '#b-uid'], ['activity log', 'activity', '#a-find'],
  ['personal app install link', 'personal', '.steps'], ['remove the bot', 'danger', '#leave-go'],
];

function initFind() {
  const input = $('find');
  const hits = $('find-hits');
  const show = () => {
    const q = input.value.trim().toLowerCase();
    if (!q) { hits.style.display = 'none'; return; }
    const m = FIND.filter(([l, p]) => l.includes(q) && !(STATE && STATE.is_personal && SERVER_ONLY.includes(p))).slice(0, 8);
    hits.innerHTML = m.length ? m.map(([l, p], i) => `<div class="${i ? '' : 'hl'}" data-i="${FIND.findIndex((x) => x[0] === l)}">${l}<small>${p}</small></div>`).join('') : '<div><small>nothing found</small></div>';
    hits.style.display = '';
  };
  const jump = (i) => {
    const [, p, sel] = FIND[i];
    go(p);
    input.value = '';
    hits.style.display = 'none';
    setTimeout(() => {
      const t = document.querySelector(`#p-${p} ${sel}`);
      if (!t) return;
      t.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const card = t.closest('.panel') || t;
      card.classList.remove('flash'); void card.offsetWidth; card.classList.add('flash');
    }, 350);
  };
  input.addEventListener('input', show);
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') { const f = hits.querySelector('[data-i]'); if (f) jump(Number(f.dataset.i)); }
    if (e.key === 'Escape') { hits.style.display = 'none'; input.blur(); }
  });
  hits.addEventListener('click', (e) => { const r = e.target.closest('[data-i]'); if (r) jump(Number(r.dataset.i)); });
  document.addEventListener('mousedown', (e) => { if (!e.target.closest('.side-search')) hits.style.display = 'none'; });
}

async function init() {
  icons();
  STATE = await apiGet(`/api/guild/${GID}`);
  if (!STATE) return;
  document.title = `${STATE.name} · ${BOT}`;
  $('side-name').textContent = STATE.name;
  $('side-sub').textContent = STATE.is_personal ? 'personal app' : `${STATE.users.length} players`;
  $('side-icon').innerHTML = av(STATE.name, STATE.icon);
  if (STATE.is_personal) document.querySelectorAll('[data-server]').forEach((x) => { x.style.display = 'none'; });
  renderOverview();
  renderPlayers();
  renderBounties();
  renderPersonal();
  renderDanger();
  renderEconomy();
  renderGames();
  renderLeveling();
  renderLogs();
  renderBuilder();
  renderRebirths();
  go((location.hash || '#overview').slice(1), false);
}

initFind();
init();
