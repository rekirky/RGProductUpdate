'use strict';

const DATA_URL = 'data/products.json';

let allProducts = [];
let activeFilter = 'all';
let activeNameFilter = 'all';
let searchQuery = '';
let hideOld = localStorage.getItem('hideOld') !== 'false'; // default true

// ── Bootstrap ──────────────────────────────────────────────────────────────

async function init() {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    allProducts = data.products || [];
    renderLastUpdated(data.generated_at);
    renderSummary(allProducts);
    renderTable();
  } catch (err) {
    document.getElementById('products-body').innerHTML =
      `<tr class="error-row"><td colspan="5">Failed to load product data: ${err.message}</td></tr>`;
    document.getElementById('last-updated').textContent = '';
  }
}

// ── Rendering ───────────────────────────────────────────────────────────────

function renderLastUpdated(isoDate) {
  const el = document.getElementById('last-updated');
  if (!isoDate) { el.textContent = ''; return; }
  const d = new Date(isoDate);
  el.textContent = `Updated ${d.toLocaleDateString('en-AU', {
    day: 'numeric', month: 'short', year: 'numeric'
  })} at ${d.toLocaleTimeString('en-AU', {
    hour: '2-digit', minute: '2-digit', timeZoneName: 'short'
  })}`;
}

function renderSummary(products) {
  const counts = { current: 0, previous: 0, old: 0 };
  products.forEach(p => { if (p.status in counts) counts[p.status]++; });

  document.getElementById('summary-bar').innerHTML = `
    <span class="summary-stat">
      <span class="stat-dot current"></span>${counts.current} updated this year
    </span>
    <span class="summary-stat">
      <span class="stat-dot previous"></span>${counts.previous} last year
    </span>
    <span class="summary-stat">
      <span class="stat-dot old"></span>${counts.old} older
    </span>
    <span class="summary-stat">${products.length} total</span>
  `;
}

function renderTable() {
  const filtered = filteredProducts();
  const tbody = document.getElementById('products-body');
  const noResults = document.getElementById('no-results');

  if (filtered.length === 0) {
    tbody.innerHTML = '';
    noResults.hidden = false;
    return;
  }

  noResults.hidden = true;
  tbody.innerHTML = filtered.map(buildRow).join('');
}

// ── Filter definitions ────────────────────────────────────────────────────────
// Each entry is a function that receives the lowercased product name and key.
// Add new category filters here — no other code changes needed.

const NAME_FILTERS = {
  all:     () => true,
  flyway:  (name, _key) => name.includes('flyway'),
  dotnet:  (name, _key) => name.includes('reflector') || name.includes('ants') || name.includes('smartassembly'),
  sqltoolbelt: (name, _key) => [
    'sql toolbelt', 'sql change automation', 'sql compare', 'sql data compare',
    'sql data generator', 'sql dependency', 'sql doc', 'sql multi script',
    'sql prompt', 'sql search', 'sql source control', 'sql test', 'sql backup',
  ].some(k => name.includes(k)),
  monitor: (name, key) => key.toLowerCase().includes('redgatemonitor') || name.includes('redgate monitor'),
  tdm:     (name, _key) => name.includes('test data manager'),
  bundles: (_name, key) => ['SQLToolbelt', 'SQLToolbeltEssentials'].includes(key),
};

// ── Filtering ────────────────────────────────────────────────────────────────

function isUpdatedThisWeek(dateStr) {
  if (!dateStr) return false;
  const updated = new Date(dateStr);
  const cutoff  = new Date();
  cutoff.setDate(cutoff.getDate() - 7);
  return updated >= cutoff;
}

function filteredProducts() {
  const q = searchQuery;
  const nameFilterFn = NAME_FILTERS[activeNameFilter] || NAME_FILTERS.all;
  return allProducts.filter(p => {
    if (hideOld && p.status === 'old') return false;
    const name = p.name.toLowerCase();
    const matchesSearch = !q || name.includes(q) || (p.version && p.version.includes(q));
    const matchesStatus = activeFilter === 'all'    ? true
                        : activeFilter === 'week'   ? isUpdatedThisWeek(p.updated)
                        : p.status === activeFilter;
    const matchesName   = nameFilterFn(name, p.key);
    return matchesSearch && matchesStatus && matchesName;
  });
}

// ── Row builder ──────────────────────────────────────────────────────────────

const STATUS_LABEL = { current: 'This year', previous: 'Last year', old: 'Older' };

function buildRow(p) {
  const nameCell = p.download_url
    ? `<a href="${esc(p.download_url)}" class="product-name" target="_blank" rel="noopener"
          title="Download ${esc(p.name)}">${esc(p.name)}</a>`
    : `<span class="product-name">${esc(p.name)}</span>`;

  const versionCell = p.version
    ? `<span class="version-tag">${esc(p.version)}</span>`
    : `<span class="version-tag empty">&mdash;</span>`;

  const row1 = [];
  const row2 = [];

  if (p.download_url)
    row1.push(`<a href="${esc(p.download_url)}" class="row-link" target="_blank" rel="noopener">Download</a>`);
  if (p.release_notes_url)
    row1.push(`<a href="${esc(p.release_notes_url)}" class="row-link" target="_blank" rel="noopener">Release Notes</a>`);
  if (p.doc_url)
    row2.push(`<a href="${esc(p.doc_url)}" class="row-link" target="_blank" rel="noopener">Docs</a>`);
  if (p.key)
    row2.push(`<a href="https://download.red-gate.com/checkforupdates/${esc(p.key)}/" class="row-link" target="_blank" rel="noopener">Older Versions</a>`);

  const row1Cell = row1.join('<span class="link-sep">|</span>');
  const row2Cell = row2.join('<span class="link-sep">|</span>');
  const linksCell = row1Cell + (row2Cell ? '<br>' + row2Cell : '');

  const statusLabel = STATUS_LABEL[p.status] || p.status;

  return `<tr>
    <td>${nameCell}</td>
    <td>${versionCell}</td>
    <td>${esc(p.updated || '—')}</td>
    <td><span class="status-badge ${esc(p.status)}">${esc(statusLabel)}</span></td>
    <td><div class="row-links">${linksCell}</div></td>
  </tr>`;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Event listeners ───────────────────────────────────────────────────────────

document.getElementById('search-name').addEventListener('input', e => {
  searchQuery = e.target.value.toLowerCase().trim();
  renderTable();
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    renderTable();
  });
});

document.querySelectorAll('.filter-btn-tag').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn-tag').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeNameFilter = btn.dataset.nameFilter;
    renderTable();
  });
});

const hideOldCheckbox = document.getElementById('hide-old');
hideOldCheckbox.checked = hideOld;
hideOldCheckbox.addEventListener('change', () => {
  hideOld = hideOldCheckbox.checked;
  localStorage.setItem('hideOld', hideOld);
  renderTable();
});

// ── Start ────────────────────────────────────────────────────────────────────

init();
