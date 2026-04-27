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
    wireCapabilitiesModal();
    renderAll();
  } catch (err) {
    const el = document.getElementById('load-error');
    if (el) { el.textContent = `Failed to load data: ${err.message}`; el.hidden = false; }
    document.getElementById('last-updated').textContent = '';
  }
}

function renderAll() {
  renderMatrix();
  renderVersionSection();
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

function hasCloudMatrix(product) {
  return product?.cloud_matrix?.length > 0;
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

const PRODUCT_ICONS = {
  tdm:     'images/tdm.png',
  flyway:  'images/flyway.png',
  monitor: 'images/monitor.png',
};

function renderProductTabs() {
  const container = document.getElementById('product-tabs');
  container.innerHTML = allData.products
    .map(p => {
      const icon = PRODUCT_ICONS[p.key]
        ? `<img src="${esc(PRODUCT_ICONS[p.key])}" class="product-tab-icon" alt="" aria-hidden="true">`
        : '';
      return `<button class="filter-btn-tag${p.key === selectedProduct ? ' active' : ''}"
               data-product="${esc(p.key)}">${icon}${esc(p.name)}</button>`;
    })
    .join('');

  container.querySelectorAll('[data-product]').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.product === selectedProduct) return;
      selectedProduct = btn.dataset.product;
      selectedFeatureIdx = 0;
      selectedCloud = 'all';
      // Reset cloud filter active state
      document.getElementById('cloud-filters')
        .querySelectorAll('[data-cloud]')
        .forEach((b, i) => b.classList.toggle('active', i === 0));
      container.querySelectorAll('[data-product]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      renderAll();
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
  const cloudSection = document.getElementById('cloud-section');

  if (!hasCloudMatrix(product)) {
    cloudSection.hidden = true;
    return;
  }

  cloudSection.hidden = false;

  const link = document.getElementById('source-link');
  if (link) link.href = product.source_url;

  const engines = product.engines;
  const rows = product.cloud_matrix.filter(row => {
    if (selectedCloud === 'all') return true;
    if (selectedCloud === 'other') return !MAIN_PROVIDERS.includes(row.provider);
    return row.provider === selectedCloud;
  });

  const colCount = engines.length + 2;
  const table = document.getElementById('matrix-table');

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
        html += `<td class="cell-support">${cloudStatusBadge(row.support[engine])}</td>`;
      });
      html += '</tr>';
      prevProvider = row.provider;
    });
  }

  html += '</tbody>';
  table.innerHTML = html;
}

function cloudStatusBadge(status) {
  switch (status) {
    case 'supported':     return '<span class="support-badge supported">&#10003;</span>';
    case 'preview':       return '<span class="support-badge preview">&#x1F9EA;</span>';
    case 'not_supported': return '<span class="support-badge not-supported">&#10005;</span>';
    default:              return '<span class="support-badge na">&mdash;</span>';
  }
}

// ── Feature tab colours ───────────────────────────────────────────────────

// Matched case-insensitively against the feature name (first match wins).
const FEATURE_COLOURS = [
  { match: 'sql server',          colour: '#003087' },  // Dark Blue   – SQL Server
  { match: 'oracle',              colour: '#C74634' },  // Red         – Oracle
  { match: 'postgresql',          colour: '#0284C7' },  // Light Blue  – PostgreSQL
  { match: 'mariadb',             colour: '#C0765A' },  // Orange      – MariaDB
  { match: 'mysql',               colour: '#00618A' },  // Teal-Blue   – MySQL
  { match: 'mongodb',             colour: '#47A248' },  // Green       – MongoDB
  { match: 'anonymize',           colour: '#7C3AED' },  // Violet      – TDM Anonymize
  { match: 'subset',              colour: '#0D9488' },  // Teal        – TDM Subset
  { match: 'monitoring',          colour: '#2DB84B' },  // Green       – Monitor (matches Healthy status)
  { match: 'data warehouse',      colour: '#9333EA' },  // Purple      – Data Warehousing
  { match: 'nosql',               colour: '#16A34A' },  // Green       – NoSQL & Document
  { match: 'specialised',         colour: '#B45309' },  // Amber       – Specialised
  { match: 'enterprise',          colour: '#475569' },  // Slate       – Enterprise
  { match: 'lightweight',         colour: '#0891B2' },  // Cyan        – Lightweight & Embedded
];

function featureColour(featureName) {
  const lower = featureName.toLowerCase();
  const entry = FEATURE_COLOURS.find(f => lower.includes(f.match));
  return entry ? entry.colour : null;
}

// ── Version support ───────────────────────────────────────────────────────

function renderVersionSection() {
  const product = getProduct();
  if (!product) return;

  // Show/hide the capabilities info button
  const capsBtn = document.getElementById('capabilities-btn');
  if (capsBtn) capsBtn.hidden = !product.capabilities?.length;

  // Always reset Flyway-specific extras before rendering any product
  hideFlywaySectionExtras();

  const features = product.version_support ?? [];
  const tabContainer = document.getElementById('feature-tabs');
  const wrapper = document.getElementById('version-table-wrapper');

  // Source link — only show for Flyway (version section link)
  const versionSourceLink = document.getElementById('version-source-link');
  if (versionSourceLink) {
    const showLink = product.key === 'flyway' && product.source_url;
    versionSourceLink.href = showLink ? product.source_url : '#';
    versionSourceLink.hidden = !showLink;
  }

  if (features.length === 0) {
    tabContainer.innerHTML = '';
    wrapper.innerHTML = '<table><tbody><tr class="state-row"><td colspan="2">No version data available.</td></tr></tbody></table>';
    return;
  }

  tabContainer.innerHTML = features
    .map((f, i) => {
      const colour = featureColour(f.feature);
      const style = colour ? ` style="--btn-accent:${colour}"` : '';
      return `<button class="filter-btn${i === selectedFeatureIdx ? ' active' : ''}"
               data-fi="${i}"${style}>${esc(f.feature)}</button>`;
    })
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

const FLYWAY_TIERS = ['community', 'teams', 'enterprise', 'foundational', 'advanced'];

function tierStatusBadge(status) {
  switch (status) {
    case 'supported':     return '<span class="support-badge supported">&#10003;</span>';
    case 'compatible':    return '<span class="support-badge compatible">&#9675;</span>';
    case 'not_supported': return '<span class="support-badge not-supported">&#10005;</span>';
    default:              return '<span class="support-badge na">&mdash;</span>';
  }
}

function renderVersionTable(feature) {
  if (!feature) return;

  const wrapper = document.getElementById('version-table-wrapper');

  // Hybrid Flyway format: has both 'versions' and tier columns
  const isFlywayFormat = feature.engines.length > 0 && 'community' in feature.engines[0];

  if (isFlywayFormat) {
    renderFlywayTable(feature, wrapper);
  } else {
    renderVersionsTable(feature, wrapper);
  }
}

function renderFlywayTable(feature, wrapper) {
  const legend = document.getElementById('flyway-legend');
  if (legend) legend.hidden = false;

  let html = `<table aria-label="${esc(feature.feature)} supported versions">
    <thead>
      <tr>
        <th class="col-engine-name" rowspan="2">Database Engine</th>
        <th class="col-versions"    rowspan="2">Supported Versions</th>
        <th class="col-tier-group"  colspan="3">Flyway Edition</th>
        <th class="col-tier-group tier-group-divider" colspan="2">Capabilities</th>
      </tr>
      <tr>
        <th class="col-tier">Community</th>
        <th class="col-tier">Teams</th>
        <th class="col-tier">Enterprise</th>
        <th class="col-tier tier-divider">Foundational</th>
        <th class="col-tier">Advanced</th>
      </tr>
    </thead>
    <tbody>`;

  feature.engines.forEach(e => {
    const versions = (e.versions ?? []);
    const versionTags = versions.length > 0
      ? versions.map(v => `<span class="version-tag">${esc(v)}</span>`).join(' ')
      : '<span class="version-tag empty">&mdash;</span>';

    html += `<tr>
      <td class="cell-engine-name">${esc(e.name)}</td>
      <td class="cell-versions">${versionTags}</td>`;
    FLYWAY_TIERS.forEach(tier => {
      const divider = tier === 'foundational' ? ' tier-divider' : '';
      html += `<td class="cell-support${divider}">${tierStatusBadge(e[tier])}</td>`;
    });
    html += '</tr>';
  });

  html += '</tbody></table>';
  wrapper.innerHTML = html;
}

function hideFlywaySectionExtras() {
  const legend = document.getElementById('flyway-legend');
  if (legend) legend.hidden = true;
}

function renderVersionsTable(feature, wrapper) {
  hideFlywaySectionExtras();
  const hasStatus = feature.engines.some(e => e.status != null);

  let html = `<table aria-label="${esc(feature.feature)} supported versions">
    <thead><tr>
      <th class="col-engine-name">Database Engine</th>
      ${hasStatus ? '<th class="col-support-level">Support Level</th>' : ''}
      <th class="col-versions">Supported Versions</th>
    </tr></thead>
    <tbody>`;

  feature.engines.forEach(e => {
    const versions = e.versions ?? [];
    const versionTags = versions.length > 0
      ? versions.map(v => `<span class="version-tag">${esc(v)}</span>`).join(' ')
      : '<span class="version-tag empty">&mdash;</span>';

    const levelBadge = e.status === 'supported'
      ? '<span class="support-badge supported">&#10003; Full Support</span>'
      : e.status === 'compatible'
        ? '<span class="support-badge compatible">&#9675; Community</span>'
        : '';

    html += `<tr>
      <td class="cell-engine-name">${esc(e.name)}</td>
      ${hasStatus ? `<td class="cell-support-level">${levelBadge}</td>` : ''}
      <td class="cell-versions">${versionTags}</td>
    </tr>`;
  });

  html += '</tbody></table>';
  wrapper.innerHTML = html;
}

// ── Capabilities modal ────────────────────────────────────────────────────

function wireCapabilitiesModal() {
  const btn    = document.getElementById('capabilities-btn');
  const dialog = document.getElementById('capabilities-modal');
  if (!btn || !dialog) return;

  btn.addEventListener('click', () => {
    renderCapabilityCards(getProduct()?.capabilities ?? []);
    dialog.showModal();
  });

  dialog.querySelector('.cap-modal-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
}

function renderCapabilityCards(capabilities) {
  const container = document.getElementById('cap-modal-cards');
  container.innerHTML = capabilities.map(cap => {
    const slug = cap.name.toLowerCase();
    return `<div class="capability-card capability-card--${esc(slug)}">
      <p class="capability-card__tier">${esc(cap.name)}</p>
      <p class="capability-card__desc">${esc(cap.description)}</p>
    </div>`;
  }).join('');
}

// ── Start ─────────────────────────────────────────────────────────────────

init();
