"""Scrape Redgate documentation pages for database engine support data.

Outputs data/db-support.json. Falls back to existing data per product if
scraping fails so a network hiccup doesn't wipe good data.
"""

import json
import logging
import re
import urllib.request
from datetime import datetime, timezone

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_FILE = 'data/db-support.json'

SOURCES = [
    {
        'key': 'tdm',
        'name': 'Test Data Manager',
        'source_url': (
            'https://documentation.red-gate.com/tdm/'
            'redgate-test-data-manager-overview/database-engine-support'
        ),
    },
]

STATUS_MAP = {
    '✅': 'supported',   # ✅
    '✔': 'supported',   # ✔
    'ᾞa': 'preview',    # 🧪
    '❌': 'not_supported',  # ❌
    '✖': 'not_supported',  # ✖
    '✗': 'not_supported',  # ✗
    '✕': 'not_supported',  # ✕
}


def parse_status(text):
    t = (text or '').strip()
    for char, status in STATUS_MAP.items():
        if char in t:
            return status
    lower = t.lower()
    if 'production' in lower or 'supported' in lower:
        return 'supported'
    if 'preview' in lower:
        return 'preview'
    if 'not supported' in lower:
        return 'not_supported'
    return None


def fetch_html(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': (
                'Mozilla/5.0 (compatible; RedgateDocsBot/1.0)'
            )
        },
    )
    with urllib.request.urlopen(req, timeout=20) as f:
        return f.read().decode('utf-8', errors='replace')


def expand_rowspans(table_elem):
    """Extract table rows, expanding rowspan/colspan attributes.

    Returns (headers, data_rows) where each is a list of string lists.
    """
    rows = table_elem.find_all('tr')
    if not rows:
        return [], []

    # spans[col] = (text, remaining_row_count)
    spans = {}
    all_rows = []

    for row in rows:
        cells = row.find_all(['th', 'td'])
        row_data = {}
        col = 0
        cell_idx = 0

        while True:
            # Consume any active rowspans for this column
            if col in spans:
                val, remaining = spans[col]
                row_data[col] = val
                if remaining - 1 > 0:
                    spans[col] = (val, remaining - 1)
                else:
                    del spans[col]
                col += 1
                continue

            if cell_idx >= len(cells):
                break

            cell = cells[cell_idx]
            text = cell.get_text(separator=' ', strip=True)
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))

            for offset in range(colspan):
                row_data[col + offset] = text
                if rowspan > 1:
                    spans[col + offset] = (text, rowspan - 1)

            col += colspan
            cell_idx += 1

        # Drain any remaining active rowspans (e.g. trailing merged cols)
        temp_col = col
        while temp_col in spans:
            val, remaining = spans[temp_col]
            row_data[temp_col] = val
            if remaining - 1 > 0:
                spans[temp_col] = (val, remaining - 1)
            else:
                del spans[temp_col]
            temp_col += 1

        if row_data:
            width = max(row_data.keys()) + 1
            all_rows.append([row_data.get(i, '') for i in range(width)])

    if not all_rows:
        return [], []

    # Treat first row as headers if all cells were <th>
    first_cells = rows[0].find_all(['th', 'td'])
    if first_cells and all(c.name == 'th' for c in first_cells):
        return all_rows[0], all_rows[1:]

    return [], all_rows


def find_cloud_matrix(tables):
    """Find and parse the cloud compatibility matrix table."""
    for table in tables:
        headers, data_rows = expand_rowspans(table)
        if not headers:
            continue
        norm = [h.strip().lower() for h in headers]
        if 'cloud provider' not in norm or 'service' not in norm:
            continue

        provider_idx = norm.index('cloud provider')
        service_idx = norm.index('service')
        engine_headers = [
            headers[i]
            for i in range(len(headers))
            if i not in (provider_idx, service_idx)
        ]

        matrix = []
        for row in data_rows:
            # Pad short rows
            while len(row) < len(headers):
                row.append('')

            provider = row[provider_idx].strip()
            service = row[service_idx].strip()
            if not provider and not service:
                continue

            support = {}
            for engine in engine_headers:
                idx = headers.index(engine)
                cell = row[idx] if idx < len(row) else ''
                support[engine] = parse_status(cell)

            matrix.append({
                'provider': provider,
                'service': service,
                'support': support,
            })

        if matrix:
            return engine_headers, matrix

    return [], []


def find_version_tables(tables):
    """Find and parse all version support tables."""
    results = []
    for table in tables:
        headers, data_rows = expand_rowspans(table)
        if not headers:
            continue
        norm = [h.strip().lower() for h in headers]
        if 'engine' not in norm:
            continue
        if 'versions' not in norm and 'version' not in norm:
            continue

        engine_idx = norm.index('engine')
        version_idx = norm.index('versions') if 'versions' in norm else norm.index('version')

        # Infer feature name from nearest preceding heading
        feature = 'General'
        prev = table.find_previous(['h2', 'h3', 'h4'])
        if prev:
            feature = prev.get_text(strip=True)

        engines_data = []
        for row in data_rows:
            engine_name = row[engine_idx].strip() if engine_idx < len(row) else ''
            versions_raw = row[version_idx].strip() if version_idx < len(row) else ''
            if not engine_name:
                continue
            versions = [
                v.strip()
                for v in re.split(r'[\s,]+', versions_raw)
                if v.strip() and v.strip() not in ('-', '—')
            ]
            engines_data.append({'name': engine_name, 'versions': versions})

        if engines_data:
            # Merge into existing entry for same feature if already seen
            existing = next((r for r in results if r['feature'] == feature), None)
            if existing:
                existing['engines'].extend(engines_data)
            else:
                results.append({'feature': feature, 'engines': engines_data})

    return results


def scrape_product(source):
    """Scrape one product page. Returns product dict or None on failure."""
    if not BS4_AVAILABLE:
        logger.warning('beautifulsoup4 not installed — install it to enable scraping')
        return None

    url = source['source_url']
    logger.info(f'Fetching {url}')
    try:
        html = fetch_html(url)
    except Exception as exc:
        logger.error(f'Failed to fetch {url}: {exc}')
        return None

    soup = BeautifulSoup(html, 'html.parser')
    tables = soup.find_all('table')
    logger.info(f'Found {len(tables)} table(s) on page')

    engines, cloud_matrix = find_cloud_matrix(tables)
    version_support = find_version_tables(tables)

    if not cloud_matrix and not version_support:
        logger.warning(f'No usable data extracted from {url}')
        return None

    logger.info(
        f'Extracted {len(cloud_matrix)} cloud matrix rows, '
        f'{len(version_support)} version table(s)'
    )

    return {
        'key': source['key'],
        'name': source['name'],
        'source_url': source['source_url'],
        'engines': engines,
        'cloud_matrix': cloud_matrix,
        'version_support': version_support,
    }


def load_existing():
    try:
        with open(OUTPUT_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'products': []}


def main():
    existing = load_existing()
    existing_by_key = {p['key']: p for p in existing.get('products', [])}

    products = []
    for source in SOURCES:
        result = scrape_product(source)
        if result:
            products.append(result)
        elif source['key'] in existing_by_key:
            logger.info(f"Keeping existing data for {source['name']}")
            products.append(existing_by_key[source['key']])
        else:
            logger.warning(f"No data available for {source['name']}, skipping")

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'products': products,
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f'Written {len(products)} product(s) to {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
