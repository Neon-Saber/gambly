async function loadOverview() {
  const o = await apiGet('/api/overview');
  if (!o) return;
  document.getElementById('admin-stats').innerHTML = `
    <div class="stat big">
      <div><div class="n">${fmtChips(o.total_chips_in_circulation)}</div><div class="l">chips across every server</div></div>
      <div class="legend"><span>players <b>${fmtChips(o.total_players)}</b></span><span>owed <b>${fmtChips(o.total_debt_owed)}</b></span></div>
    </div>
    <div class="stat"><div class="n">${o.guild_count}</div><div class="l">servers with data</div></div>
    <div class="stat good"><div class="n">${o.installed_count}</div><div class="l">bot actually in</div></div>
    <div class="stat ${o.ghost_count ? 'warn' : ''}"><div class="n">${o.ghost_count}</div><div class="l">data but no bot</div></div>
    <div class="stat ${o.defaulted_count || o.banned_count ? 'bad' : ''}"><div class="n">${o.defaulted_count} / ${o.banned_count}</div><div class="l">defaulted / banned</div></div>`;
}

async function loadGuilds() {
  const list = await apiGet('/api/all_guilds');
  const grid = document.getElementById('admin-guilds-grid');
  if (!list || !list.length) { grid.innerHTML = '<div class="empty">nothing yet</div>'; return; }
  grid.innerHTML = list.map((g) => {
    const dm = g.id === 'dm';
    const icon = g.icon ? `<img src="${g.icon}" alt="">` : escapeHtml((g.name || '?').trim().slice(0, 1).toUpperCase());
    let tag;
    if (dm) tag = '<span class="tag hot">personal app</span>';
    else if (g.installed) tag = g.user_count ? '<span class="tag ok">bot in</span>' : '<span class="tag">bot in, nobody played</span>';
    else tag = '<span class="tag bad">no bot, personal app use</span>';
    const sub = dm ? '' : `<small class="sub">${g.user_count} player${g.user_count === 1 ? '' : 's'}, ${g.banned_count} banned</small>`;
    return `<a class="server" href="/dashboard/${g.id}">
      <div class="av lg${g.installed || dm ? '' : ' ghost'}">${icon}</div>
      <div style="min-width:0"><div class="sname">${escapeHtml(g.name)}</div>${tag} ${sub}${g.unnamed ? `<br><small class="sub">${g.id}</small>` : ''}</div>
    </a>`;
  }).join('');
}

async function loadSettings() {
  const s = await apiGet('/api/settings');
  if (!s) return;
  const labels = {
    starting_bal: 'new player chips', daily_amt: 'daily claim',
    bank_interest: 'bank interest (0 to 1)', loan_max: 'biggest loan', loan_interest: 'loan interest (0 to 1)',
  };
  document.getElementById('admin-settings-fields').innerHTML = Object.keys(labels).map((k) => `
    <div class="fld"><label>${labels[k]}</label><input type="number" step="any" id="gs-${k}" value="${s[k]}"></div>`).join('');
  document.getElementById('admin-settings-save').onclick = async () => {
    const body = {};
    Object.keys(labels).forEach((k) => { body[k] = Number(document.getElementById(`gs-${k}`).value); });
    if (await apiPost('/api/settings', body)) toast('saved', 'ok');
  };
}

let searchTimer;
document.getElementById('admin-search').addEventListener('input', (e) => {
  clearTimeout(searchTimer);
  const q = e.target.value.trim();
  searchTimer = setTimeout(async () => {
    const tbody = document.querySelector('#admin-search-table tbody');
    if (!q) { tbody.innerHTML = ''; return; }
    const results = await apiGet(`/api/search?q=${encodeURIComponent(q)}`);
    tbody.innerHTML = (results || []).map((r) => `
      <tr><td class="who"><b>${escapeHtml(r.name)}</b><small>${r.user_id}</small></td><td>${escapeHtml(r.guild_name)}</td>
      <td class="n">${fmtChips(r.bal)}</td><td class="n">${fmtChips(r.bank)}</td></tr>`).join('')
      || '<tr><td colspan="4" class="empty">nobody by that name</td></tr>';
  }, 250);
});

loadOverview();
loadGuilds();
loadSettings();
