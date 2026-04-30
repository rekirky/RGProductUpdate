'use strict';

const DATA_URL = 'data/products.json';

let allProducts = [];
let activeFilter = 'all';
let activeNameFilter = 'all';
let searchQuery = '';
let hideOld = localStorage.getItem('hideOld') !== 'false'; // default true
let selectedProducts = new Set(); // Track selected product keys

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
  attachCheckboxListeners();
  updateSelectAllCheckbox();
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
  const isSelected = selectedProducts.has(p.key);
  const checkboxCell = p.download_url
    ? `<input type="checkbox" class="product-checkbox" data-key="${esc(p.key)}" ${isSelected ? 'checked' : ''}>`
    : `<span class="product-checkbox-disabled"></span>`;

  const nameCell = p.download_url
    ? `<a href="${esc(p.download_url)}" class="product-name" target="_blank" rel="noopener"
          title="Download ${esc(p.name)}">${esc(p.name)}</a>`
    : `<span class="product-name">${esc(p.name)}</span>`;

  const versionCell = p.version
    ? `<span class="version-tag">${esc(p.version)}</span>`
    : `<span class="version-tag empty">&mdash;</span>`;

  // Build links in desired order: Download, Release Notes, Docs, Older Versions
  const linkHTMLs = [];

  if (p.download_url)
    linkHTMLs.push(`<a href="${esc(p.download_url)}" class="row-link" target="_blank" rel="noopener">Download</a>`);
  if (p.release_notes_url)
    linkHTMLs.push(`<a href="${esc(p.release_notes_url)}" class="row-link" target="_blank" rel="noopener">Release Notes</a>`);
  if (p.doc_url)
    linkHTMLs.push(`<a href="${esc(p.doc_url)}" class="row-link" target="_blank" rel="noopener">Docs</a>`);

  // Special handling for Flyway products
  let olderVersionsUrl = '';
  if (p.key) {
    if (p.key.toLowerCase().includes('flyway')) {
      olderVersionsUrl = 'https://download.red-gate.com/maven/release/com/redgate/flyway/flyway-commandline';
    } else if (p.key === 'SQLToolbelt' || p.key === 'SQLToolbeltEssentials') {
      olderVersionsUrl = `https://download.red-gate.com/installers/${esc(p.key)}`;
    } else {
      olderVersionsUrl = `https://download.red-gate.com/checkforupdates/${esc(p.key)}/`;
    }
    linkHTMLs.push(`<a href="${olderVersionsUrl}" class="row-link" target="_blank" rel="noopener">Older Versions</a>`);
  }

  // Format as two rows: [0,1] on row 1, [2,3] on row 2
  const row1 = linkHTMLs.slice(0, 2).join('<span class="link-sep">|</span>');
  const row2 = linkHTMLs.slice(2, 4).join('<span class="link-sep">|</span>');
  const linksCell = [row1, row2].filter(Boolean).join('<br>');

  const statusLabel = STATUS_LABEL[p.status] || p.status;

  return `<tr>
    <td>${checkboxCell}</td>
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
  selectedProducts.clear();
  updateSelectedCount();
  renderTable();
});

document.querySelectorAll('.filter-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    selectedProducts.clear();
    updateSelectedCount();
    renderTable();
  });
});

document.querySelectorAll('.filter-btn-tag').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-btn-tag').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeNameFilter = btn.dataset.nameFilter;
    selectedProducts.clear();
    updateSelectedCount();
    renderTable();
  });
});

const hideOldCheckbox = document.getElementById('hide-old');
hideOldCheckbox.checked = hideOld;
hideOldCheckbox.addEventListener('change', () => {
  hideOld = hideOldCheckbox.checked;
  localStorage.setItem('hideOld', hideOld);
  selectedProducts.clear();
  updateSelectedCount();
  renderTable();
});

// ── Bulk download functionality ────────────────────────────────────────────

function updateSelectedCount() {
  const countEl = document.getElementById('selected-count');
  const downloadBtn = document.getElementById('download-selected');
  const arrowBtn = document.getElementById('download-dropdown-toggle');
  const count = selectedProducts.size;

  if (count > 0) {
    countEl.textContent = `${count} selected`;
    downloadBtn.disabled = false;
    arrowBtn.disabled = false;
  } else {
    countEl.textContent = '';
    downloadBtn.disabled = true;
    arrowBtn.disabled = true;
  }
}

function attachCheckboxListeners() {
  document.querySelectorAll('.product-checkbox').forEach(checkbox => {
    checkbox.addEventListener('change', (e) => {
      const key = e.target.dataset.key;
      if (e.target.checked) {
        selectedProducts.add(key);
      } else {
        selectedProducts.delete(key);
      }
      updateSelectAllCheckbox();
      updateSelectedCount();
    });
  });
}

function updateSelectAllCheckbox() {
  const selectAllCheckbox = document.getElementById('select-all');
  const visibleCheckboxes = document.querySelectorAll('.product-checkbox');
  const checkedCheckboxes = document.querySelectorAll('.product-checkbox:checked');

  if (visibleCheckboxes.length === 0) {
    selectAllCheckbox.checked = false;
    selectAllCheckbox.indeterminate = false;
  } else if (checkedCheckboxes.length === visibleCheckboxes.length) {
    selectAllCheckbox.checked = true;
    selectAllCheckbox.indeterminate = false;
  } else if (checkedCheckboxes.length > 0) {
    selectAllCheckbox.checked = false;
    selectAllCheckbox.indeterminate = true;
  } else {
    selectAllCheckbox.checked = false;
    selectAllCheckbox.indeterminate = false;
  }
}

document.getElementById('select-all').addEventListener('change', (e) => {
  document.querySelectorAll('.product-checkbox').forEach(checkbox => {
    checkbox.checked = e.target.checked;
    const key = checkbox.dataset.key;
    if (e.target.checked) {
      selectedProducts.add(key);
    } else {
      selectedProducts.delete(key);
    }
  });
  updateSelectedCount();
});

// ── Download queue ────────────────────────────────────────────────────────────

let downloadQueue = [];
let downloadQueueIndex = 0;

function openQueue(products) {
  downloadQueue = products;
  downloadQueueIndex = 0;

  const overlay = document.getElementById('download-queue-overlay');
  const list    = document.getElementById('queue-list');

  list.innerHTML = products.map((p, i) => `
    <li class="queue-item${i === 0 ? ' active' : ''}" data-index="${i}">
      <span class="queue-item-icon">${i === 0 ? '▶' : '·'}</span>
      <span class="queue-item-name" title="${esc(p.name)}">${esc(p.name)}</span>
    </li>
  `).join('');

  overlay.hidden = false;
  triggerQueueDownload();
}

function triggerQueueDownload() {
  const product = downloadQueue[downloadQueueIndex];
  if (!product) return;

  const link = document.createElement('a');
  link.href   = product.download_url;
  link.target = '_blank';
  link.rel    = 'noopener';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  updateQueueUI();
}

function updateQueueUI() {
  const items   = document.querySelectorAll('.queue-item');
  const nextBtn = document.getElementById('queue-next');
  const isLast  = downloadQueueIndex === downloadQueue.length - 1;

  items.forEach((el, i) => {
    const isPending = i > downloadQueueIndex;
    el.className = 'queue-item' +
      (i < downloadQueueIndex  ? ' done'   :
       i === downloadQueueIndex ? ' active' :
                                  ' pending');
    el.querySelector('.queue-item-icon').textContent =
      i < downloadQueueIndex  ? '✓' :
      i === downloadQueueIndex ? '▶' : '·';
    el.style.cursor = isPending ? 'pointer' : '';
    el.title = isPending ? `Jump to: ${downloadQueue[i].name}` : '';
  });

  nextBtn.textContent = isLast ? 'Done' : 'Download Next';
}

function advanceQueue() {
  if (downloadQueueIndex >= downloadQueue.length - 1) {
    closeQueue();
    return;
  }
  downloadQueueIndex++;
  triggerQueueDownload();
}

function closeQueue() {
  document.getElementById('download-queue-overlay').hidden = true;
  downloadQueue = [];
  downloadQueueIndex = 0;
}

document.getElementById('queue-next').addEventListener('click', advanceQueue);
document.getElementById('queue-cancel').addEventListener('click', closeQueue);
document.getElementById('queue-close').addEventListener('click', closeQueue);

document.getElementById('queue-list').addEventListener('click', (e) => {
  const item = e.target.closest('.queue-item.pending');
  if (!item) return;
  downloadQueueIndex = parseInt(item.dataset.index, 10);
  triggerQueueDownload();
});

document.getElementById('download-selected').addEventListener('click', () => {
  const products = allProducts.filter(p => selectedProducts.has(p.key) && p.download_url);
  if (products.length === 0) return;
  openQueue(products);
});

// ── Download dropdown ─────────────────────────────────────────────────────────

const dropdownToggle = document.getElementById('download-dropdown-toggle');
const dropdownMenu   = document.getElementById('download-dropdown-menu');

dropdownToggle.addEventListener('click', (e) => {
  e.stopPropagation();
  const isOpen = !dropdownMenu.hidden;
  dropdownMenu.hidden = isOpen;
  dropdownToggle.setAttribute('aria-expanded', String(!isOpen));
});

document.addEventListener('click', () => {
  dropdownMenu.hidden = true;
  dropdownToggle.setAttribute('aria-expanded', 'false');
});

dropdownMenu.addEventListener('click', (e) => e.stopPropagation());

document.getElementById('copy-links-btn').addEventListener('click', () => {
  dropdownMenu.hidden = true;
  dropdownToggle.setAttribute('aria-expanded', 'false');

  const products = allProducts.filter(p => selectedProducts.has(p.key) && p.download_url);
  if (products.length === 0) return;

  const lines = products.map(p => `${p.name}: ${p.download_url}`);
  navigator.clipboard.writeText(lines.join('\n')).then(() => {
    const btn = document.getElementById('copy-links-btn');
    const orig = btn.textContent;
    btn.textContent = `Copied ${products.length} link${products.length === 1 ? '' : 's'}!`;
    setTimeout(() => { btn.textContent = orig; }, 2000);
  });
});

// ── Start ────────────────────────────────────────────────────────────────────

init();
