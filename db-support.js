'use strict';

const DATA_URL = 'data/db-support.json';
const MAIN_PROVIDERS = ['Amazon', 'Microsoft', 'Google'];

let allData = null;
let selectedProduct = 'tdm';
let selectedCloud = 'all';
let selectedFeatureIdx = 0;

// ── Bootstrap ──────────────────────────────────────────────────────────────

async function init() {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    allData = await res.json();
    renderLastUpdated(allData.generated_at);
    renderProductTabs();
    wireCloudFilters();
    renderMatrix();
    renderVersionSection();
  } catch (err) {
    document.getElementById('matrix-table').innerHTML =
      `<tbody><tr class="error-row"><td colspan="7">Failed to load data: ${esc(err.message)}</td></tr></tbody>`;
    document.getElementById('last-updated').textContent = '';
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────

function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getProduct() {
  return allData?.products?.find(p => p.key === selectedProduct) ?? null;
}

// ── Last updated ──────────────────────────────────────────────────────────

function renderLastUpdated(isoDate) {
  const el = document.getElementById('last-updated');
  if (!isoDate) { el.textContent = ''; return; }
  const d = new Date(isoDate);
  el.textContent = `Updated ${d.toLocaleDateString('en-AU', {
    day: 'numeric', month: 'short', year: 'numeric',
  })} at ${d.toLocaleTimeString('en-AU', {
    hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
  })}`;
}

// ── Product tabs ──────────────────────────────────────────────────────────

function renderProductTabs() {
  const container = document.getElementById('product-tabs');
  container.innerHTML = allData.products
    .map(p =>
      `<button class="filter-btn-tag${p.key === selectedProduct ? ' active' : ''}"
               data-product="${esc(p.key)}">${esc(p.name)}</button>`
    )
    .join('');

  container.querySelectorAll('[data-product]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.product === selectedProduct) return;
      selectedProduct = btn.dataset.product;
      selectedFeatureIdx = 0;
      container.querySelectorAll('[data-product]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderMatrix();
      renderVersionSection();
    });
  });
}

// ── Cloud filters ─────────────────────────────────────────────────────────

function wireCloudFilters() {
  document.getElementById('cloud-filters').querySelectorAll('[data-cloud]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.getElementById('cloud-filters')
        .querySelectorAll('[data-cloud]')
        .forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      selectedCloud = btn.dataset.cloud;
      renderMatrix();
    });
  });
}

// ── Compatibility matrix ──────────────────────────────────────────────────

function renderMatrix() {
  const product = getProduct();
  const table = document.getElementById('matrix-table');

  if (!product) {
    table.innerHTML = '<tbody><tr class="state-row"><td colspan="7">Select a product above.</td></tr></tbody>';
    return;
  }

  const link = document.getElementById('source-link');
  if (link) link.href = product.source_url;

  const engines = product.engines;
  const rows = product.cloud_matrix.filter(row => {
    if (selectedCloud === 'all') return true;
    if (selectedCloud === 'other') return !MAIN_PROVIDERS.includes(row.provider);
    return row.provider === selectedCloud;
  });

  const colCount = engines.length + 2;

  let html = '<thead><tr>';
  html += '<th class="col-provider">Provider</th>';
  html += '<th class="col-service">Service</th>';
  engines.forEach(e => { html += `<th class="col-engine">${esc(e)}</th>`; });
  html += '</tr></thead><tbody>';

  if (rows.length === 0) {
    html += `<tr><td colspan="${colCount}" class="state-row">No services match this filter.</td></tr>`;
  } else {
    let prevProvider = null;
    rows.forEach(row => {
      const isNewGroup = row.provider !== prevProvider;
      html += `<tr${isNewGroup ? ' class="provider-start"' : ''}>`;
      html += `<td class="cell-provider">${esc(row.provider)}</td>`;
      html += `<td class="cell-service">${esc(row.service)}</td>`;
      engines.forEach(engine => {
        html += `<td class="cell-support">${statusBadge(row.support[engine])}</td>`;
      });
      html += '</tr>';
      prevProvider = row.provider;
    });
  }

  html += '</tbody>';
  table.innerHTML = html;
}

function statusBadge(status) {
  switch (status) {
    case 'supported':     return '<span class="support-badge supported">&#10003; Ready</span>';
    case 'preview':       return '<span class="support-badge preview">&#x1F9EA; Preview</span>';
    case 'not_supported': return '<span class="support-badge not-supported">&#10005;</span>';
    default:              return '<span class="support-badge na">&mdash;</span>';
  }
}

// ── Version support ───────────────────────────────────────────────────────

function renderVersionSection() {
  const product = getProduct();
  if (!product) return;

  const features = product.version_support;
  const tabContainer = document.getElementById('feature-tabs');

  tabContainer.innerHTML = features
    .map((f, i) =>
      `<button class="filter-btn${i === selectedFeatureIdx ? ' active' : ''}"
               data-fi="${i}">${esc(f.feature)}</button>`
    )
    .join('');

  tabContainer.querySelectorAll('[data-fi]').forEach(btn => {
    btn.addEventListener('click', () => {
      const idx = parseInt(btn.dataset.fi, 10);
      if (idx === selectedFeatureIdx) return;
      selectedFeatureIdx = idx;
      tabContainer.querySelectorAll('[data-fi]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderVersionTable(features[selectedFeatureIdx]);
    });
  });

  renderVersionTable(features[selectedFeatureIdx]);
}

function renderVersionTable(feature) {
  const wrapper = document.getElementById('version-table-wrapper');

  let html = `<table aria-label="${esc(feature.feature)} supported versions">
    <thead><tr>
      <th class="col-engine-name">Database Engine</th>
      <th class="col-versions">Supported Versions</th>
    </tr></thead>
    <tbody>`;

  feature.engines.forEach(e => {
    const versionTags = e.versions.length > 0
      ? e.versions.map(v => `<span class="version-tag">${esc(v)}</span>`).join(' ')
      : '<span class="version-tag empty">&mdash;</span>';
    html += `<tr>
      <td class="cell-engine-name">${esc(e.name)}</td>
      <td class="cell-versions">${versionTags}</td>
    </tr>`;
  });

  html += '</tbody></table>';
  wrapper.innerHTML = html;
}

// ── Start ─────────────────────────────────────────────────────────────────

init();
