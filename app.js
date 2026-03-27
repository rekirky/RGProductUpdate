'use strict';

const DATA_URL = 'data/products.json';

let allProducts = [];
let activeFilter = 'all';
let searchQuery = '';

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

// ── Filtering ────────────────────────────────────────────────────────────────

function filteredProducts() {
  const q = searchQuery;
  return allProducts.filter(p => {
    const matchesSearch = !q ||
      p.name.toLowerCase().includes(q) ||
      (p.version && p.version.includes(q));
    const matchesFilter = activeFilter === 'all' || p.status === activeFilter;
    return matchesSearch && matchesFilter;
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

  const links = [];
  if (p.download_url)
    links.push(`<a href="${esc(p.download_url)}" class="row-link" target="_blank" rel="noopener">Download</a>`);
  if (p.doc_url)
    links.push(`<a href="${esc(p.doc_url)}" class="row-link" target="_blank" rel="noopener">Docs</a>`);
  if (p.release_notes_url)
    links.push(`<a href="${esc(p.release_notes_url)}" class="row-link" target="_blank" rel="noopener">Release Notes</a>`);
  const linksCell = links.join('<span class="link-sep">|</span>');

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

// ── Start ────────────────────────────────────────────────────────────────────

init();
