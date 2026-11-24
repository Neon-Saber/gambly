async function loadOverview() {
  const o = await apiGet('/api/overview');
  const el = document.getElementById('admin-stats');
  if (!o) { el.innerHTML = '<div class="tile" style="grid-column:1/-1"><div class="l">couldn\'t load the totals</div></div>'; return; }
  el.innerHTML = `
    <div class="tile"><div class="n">${fmtChips(o.total_chips_in_circulation)}</div><div class="l">chips across everything</div></div>
    <div class="tile"><div class="n">${fmtChips(o.total_players)}</div><div class="l">players</div></div>
    <div class="tile good"><div class="n">${o.installed_count} / ${o.guild_count}</div><div class="l">servers with the bot / with data</div></div>
    <div class="tile ${o.defaulted_count || o.banned_count ? 'bad' : ''}"><div class="n">${o.defaulted_count} / ${o.banned_count}</div><div class="l">defaulted / banned</div></div>`;
}

async function loadGuilds() {
  const list = await apiGet('/api/all_guilds');
  const box = document.getElementById('admin-guilds');
  if (!list) { box.innerHTML = '<div class="state error"><b>couldn\'t load servers</b><button class="btn sm" onclick="loadGuilds()">try again</button></div>'; return; }
  if (!list.length) { box.innerHTML = '<div class="state"><b>no servers yet</b></div>'; return; }
  box.innerHTML = list.map((g) => {
    const dm = g.id === 'dm';
    const ic = g.icon ? `<img src="${g.icon}" alt="">` : escapeHtml((g.name || '?').trim().slice(0, 1).toUpperCase());
    const tag = dm ? '<span class="tag gold">personal ledger</span>'
      : g.installed ? (g.user_count ? '<span class="tag mint">bot in</span>' : '<span class="tag">bot in, nobody played</span>')
      : '<span class="tag red">no bot</span>';
    const sub = dm ? 'everyone playing through the personal app' : `${g.user_count} player${g.user_count === 1 ? '' : 's'}, ${g.banned_count} banned${g.unnamed ? ' · ' + g.id : ''}`;
    return `<a class="tbl-row${g.installed || dm ? '' : ' off'}" href="/dashboard/${g.id}">
      <span class="srv-ic">${ic}</span><span style="min-width:0"><b>${escapeHtml(g.name)}</b><small>${sub}</small></span>${tag}</a>`;
  }).join('');
}

const DEFAULTS = {
  starting_bal: ['new player chips', 0, null, 1],
  daily_amt: ['daily claim', 0, null, 1],
  bank_interest: ['bank interest (0 to 1)', 0, 1, 'any'],
  loan_max: ['biggest loan', 0, null, 1],
  loan_interest: ['loan interest (0 to 1)', 0, 1, 'any'],
};

async function loadSettings() {
  const s = await apiGet('/api/settings');
  if (!s) return;
  document.getElementById('admin-settings-fields').innerHTML = Object.entries(DEFAULTS).map(([k, [label, min, max, step]]) => `
    <div class="field"><label for="gs-${k}">${label}</label>
      <input type="number" id="gs-${k}" value="${s[k]}" min="${min}" ${max !== null ? `max="${max}"` : ''} step="${step}" required>
      <span class="err-msg" hidden></span></div>`).join('');
}

document.getElementById('defaults').addEventListener('submit', async (e) => {
  e.preventDefault();
  const body = {};
  let bad = false;
  Object.entries(DEFAULTS).forEach(([k, [, min, max]]) => {
    const inp = document.getElementById(`gs-${k}`);
    const err = inp.parentElement.querySelector('.err-msg');
    const v = Number(inp.value);
    const wrong = inp.value === '' || Number.isNaN(v) || v < min || (max !== null && v > max);
    inp.setAttribute('aria-invalid', String(wrong));
    err.hidden = !wrong;
    err.textContent = wrong ? (max !== null ? `between ${min} and ${max}` : `${min} or more`) : '';
    if (wrong) bad = true; else body[k] = v;
  });
  if (bad) { toast('fix the red fields first', 'error'); return; }
  const btn = e.target.querySelector('button');
  btn.classList.add('busy');
  const r = await apiPost('/api/settings', body);
  btn.classList.remove('busy');
  if (r) toast('defaults saved', 'ok');
});

let searchTimer;
document.getElementById('admin-search').addEventListener('input', (e) => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  const tbody = document.getElementById('admin-results');
  searchTimer = setTimeout(async () => {
    if (!q) { tbody.innerHTML = '<tr><td colspan="4" class="state">type to search</td></tr>'; return; }
    tbody.innerHTML = '<tr><td colspan="4"><span class="skel"></span></td></tr>';
    const results = await apiGet(`/api/search?q=${encodeURIComponent(q)}`);
    tbody.innerHTML = (results || []).map((r) => `
      <tr><td class="who"><b>${escapeHtml(r.name)}</b><small>${r.user_id}</small></td><td>${escapeHtml(r.guild_name)}</td>
      <td class="r">${fmtChips(r.bal)}</td><td class="r">${fmtChips(r.bank)}</td></tr>`).join('')
      || '<tr><td colspan="4" class="state">nobody by that name</td></tr>';
  }, 250);
});

loadOverview();
loadGuilds();
loadSettings();
