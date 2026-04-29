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
    {
        'key': 'flyway',
        'name': 'Flyway',
        'source_url': (
            'https://documentation.red-gate.com/flyway/'
            'getting-started-with-flyway/system-requirements/'
            'supported-databases-and-versions'
        ),
    },
    {
        'key': 'monitor',
        'name': 'Redgate Monitor',
        'source_url': (
            'https://documentation.red-gate.com/monitor/'
            'supported-platforms-239667385.html'
        ),
    },
]

STATUS_MAP = {
    '✅': 'supported',      # ✅ green emoji — fully supported
    '☑': 'supported',      # ☑ U+2611 ballot box with check — Flyway supported
    '✔': 'compatible',     # ✔ orange heavy check — community-compatible tier
    '◩': 'compatible',     # ◩ U+25E9 half-filled square — Flyway compatible
    '🧪': 'preview',       # 🧪 test tube — preview/beta
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
    if 'not supported' in lower:
        return 'not_supported'
    if 'production' in lower or 'supported' in lower:
        return 'supported'
    if 'compatible' in lower:
        return 'compatible'
    if 'preview' in lower:
        return 'preview'
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

    # Promote the first row to headers when:
    #   (a) every cell is a <th>, OR
    #   (b) the row lives inside a <thead> element
    # Confluence renders headers as <thead><tr><td> (not <th>), so checking
    # only for <th> misses most real-world pages.
    first_row_elem = rows[0]
    first_cells = first_row_elem.find_all(['th', 'td'])
    is_header_row = (
        (first_cells and all(c.name == 'th' for c in first_cells))
        or first_row_elem.parent.name == 'thead'
    )
    if is_header_row:
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


def extract_linux_versions_from_master_page():
    """Extract Linux versions from the master Redgate Monitor Linux support page.

    Returns list of supported Linux versions.
    """
    url = 'https://documentation.red-gate.com/monitor/monitored-instances-on-linux-machine-284069118.html'
    try:
        html = fetch_html(url)
        soup = BeautifulSoup(html, 'html.parser')

        # Look for list items containing Linux versions
        versions = []
        for li in soup.find_all('li'):
            text = li.get_text(strip=True)
            # Look for typical Linux version patterns
            if any(os_name in text for os_name in ['Ubuntu', 'Red Hat', 'Rocky', 'SUSE', 'Enterprise']):
                versions.append(text)

        if versions:
            logger.info(f'Extracted {len(versions)} Linux versions from master page')
            return versions
    except Exception as exc:
        logger.warning(f'Failed to fetch master Linux page: {exc}')

    return []


def extract_monitor_support_data(soup, engine_name):
    """Extract database versions and OS support from Monitor engine pages.

    Returns dict with:
      - versions: list of database engine versions
      - platform_support: dict with windows/linux platform data
    """
    result = {
        'versions': [],
        'platform_support': {'windows': {'versions': []}, 'linux': {'versions': [], 'support_page': None}}
    }

    # Find all lists on the page
    lists = soup.find_all(['ul', 'ol'])

    # Identify which list is which based on content patterns
    db_version_list = None
    windows_list = None
    linux_list = None

    for lst in lists:
        items = [li.get_text(strip=True) for li in lst.find_all('li', recursive=False)]
        if not items:
            continue

        first_item_lower = items[0].lower()

        # Check if this looks like a database version list (e.g., "SQL Server 2008 R2")
        if any(pattern in first_item_lower for pattern in ['sql server', 'postgresql', 'oracle', 'mysql', 'mongodb']) and db_version_list is None:
            db_version_list = items

        # Check if this looks like a Windows list
        elif any(pattern in first_item_lower for pattern in ['windows 10', 'windows 11', 'windows server']) and windows_list is None:
            windows_list = items

        # Check if this looks like a Linux list
        elif any(pattern in first_item_lower for pattern in ['ubuntu', 'red hat', 'rocky', 'suse']) and linux_list is None:
            linux_list = items

    if db_version_list:
        result['versions'] = db_version_list
        logger.info(f'Extracted {len(db_version_list)} database versions for {engine_name}')

    if windows_list:
        result['platform_support']['windows']['versions'] = windows_list
        logger.info(f'Extracted {len(windows_list)} Windows versions for {engine_name}')

    if linux_list:
        result['platform_support']['linux']['versions'] = linux_list
        logger.info(f'Extracted {len(linux_list)} Linux versions for {engine_name}')

    return result


def extract_platform_support_from_soup(soup):
    """Extract Windows and Linux OS versions from Monitor documentation page.

    Looks for sections labeled 'Windows' or 'Linux' followed by lists of OS versions.
    Also checks for links in the Linux section that point to a master Linux support page.
    Returns dict with 'windows' and 'linux' keys, each containing 'versions' list.
    """
    platform_support = {'windows': {'versions': []}, 'linux': {'versions': [], 'support_page': None}}

    # Find h2/h3/h4/strong elements that indicate Windows or Linux sections
    for header in soup.find_all(['h2', 'h3', 'h4', 'strong', 'b']):
        header_text = header.get_text(strip=True)
        header_lower = header_text.lower()

        if header_lower == 'windows':
            # Find the next list after this header
            next_list = header.find_next(['ul', 'ol'])
            if next_list:
                items = [li.get_text(strip=True) for li in next_list.find_all('li')]
                if items:
                    platform_support['windows']['versions'].extend(items)

        elif header_lower == 'linux':
            # Check if there's a link in the next element (could be in a table cell or list)
            next_elem = header.find_next(['ul', 'ol', 'p', 'td', 'div'])
            if next_elem:
                link = next_elem.find('a')
                if link and 'linux' in link.get('href', '').lower():
                    # Found a link to Linux support page
                    support_page_url = link.get('href', '')
                    if not support_page_url.startswith('http'):
                        support_page_url = 'https://documentation.red-gate.com' + support_page_url
                    platform_support['linux']['support_page'] = support_page_url
                    # Fetch and extract versions from the master page
                    logger.info(f'Found Linux support page link: {support_page_url}')
                    continue

                # If no link, extract list items normally
                if next_elem.name in ['ul', 'ol']:
                    items = [li.get_text(strip=True) for li in next_elem.find_all('li')]
                    if items:
                        platform_support['linux']['versions'].extend(items)

    # Also check tables with Windows/Linux columns
    tables = soup.find_all('table')
    for table in tables:
        headers, data_rows = expand_rowspans(table)
        if not headers:
            continue

        norm = [h.strip().lower() for h in headers]
        windows_idx = None
        linux_idx = None

        for i, h in enumerate(norm):
            if 'windows' in h:
                windows_idx = i
            if 'linux' in h:
                linux_idx = i

        if windows_idx is None and linux_idx is None:
            continue

        # Look for links in table cells
        for row_idx, row in enumerate(data_rows):
            if linux_idx is not None and linux_idx < len(row):
                # Check if there's a link in the table cell
                try:
                    row_elem = table.find_all('tr')[row_idx + (1 if headers else 0)]
                    cells = row_elem.find_all(['td', 'th'])
                    if linux_idx < len(cells):
                        cell = cells[linux_idx]
                        link = cell.find('a')
                        if link and 'linux' in link.get('href', '').lower():
                            support_page_url = link.get('href', '')
                            if not support_page_url.startswith('http'):
                                support_page_url = 'https://documentation.red-gate.com' + support_page_url
                            platform_support['linux']['support_page'] = support_page_url
                            logger.info(f'Found Linux support page link in table: {support_page_url}')
                            continue
                except:
                    pass

                # Extract text if no link
                linux_text = row[linux_idx].strip()
                if linux_text:
                    versions = [v.strip() for v in re.split(r'[•\n]', linux_text) if v.strip()]
                    platform_support['linux']['versions'].extend(versions)

            if windows_idx is not None and windows_idx < len(row):
                win_text = row[windows_idx].strip()
                if win_text:
                    versions = [v.strip() for v in re.split(r'[•\n]', win_text) if v.strip()]
                    platform_support['windows']['versions'].extend(versions)

    # Remove duplicates and filter out noise
    def clean_versions(versions):
        noise_patterns = ['visit', 'contact', 'forum', 'support', 'http://', 'https://', '@redgate']
        cleaned = []
        seen = set()

        for v in versions:
            v_lower = v.lower()
            # Skip noise
            if any(pattern in v_lower for pattern in noise_patterns):
                continue
            # Skip very short entries
            if len(v) < 3:
                continue
            # Remove duplicates
            if v not in seen:
                seen.add(v)
                cleaned.append(v)

        return cleaned

    for os_type in ['windows', 'linux']:
        platform_support[os_type]['versions'] = clean_versions(platform_support[os_type]['versions'])

    return platform_support

    return platform_support


def scrape_platform_support(engine_name):
    """Scrape versions and platform support for a specific database engine.

    Returns dict with 'versions' and 'platform_support' keys, or None if scraping fails.
    If the Linux section contains a link to a master support page, fetches that page.
    """
    # Map engine names to Monitor documentation URLs
    engine_urls = {
        'SQL Server': 'https://documentation.red-gate.com/monitor/monitored-sql-servers-239667386.html',
        'PostgreSQL': 'https://documentation.red-gate.com/monitor/monitored-postgresql-instances-239667387.html',
        'Oracle': 'https://documentation.red-gate.com/monitor/monitored-oracle-285802540.html',
        'MySQL': 'https://documentation.red-gate.com/monitor/monitored-mysql-285802551.html',
        'MongoDB': 'https://documentation.red-gate.com/monitor/monitored-mongodb-285802548.html',
    }

    url = engine_urls.get(engine_name)
    if not url:
        logger.debug(f'No documentation URL for engine: {engine_name}')
        return None

    try:
        logger.info(f'Fetching support data for {engine_name} from {url}')
        html = fetch_html(url)
        soup = BeautifulSoup(html, 'html.parser')
        result = extract_monitor_support_data(soup, engine_name)

        # If a Linux support page link was found, fetch and extract from that page
        if result['platform_support']['linux'].get('support_page'):
            logger.info(f'Fetching master Linux support page: {result["platform_support"]["linux"]["support_page"]}')
            linux_versions = extract_linux_versions_from_master_page()
            if linux_versions:
                result['platform_support']['linux']['versions'] = linux_versions

        return result
    except Exception as exc:
        logger.warning(f'Failed to scrape support data for {engine_name}: {exc}')
        return None


_FLYWAY_TIER_NAMES = ('community', 'teams', 'enterprise', 'foundational', 'advanced')


def _parse_flyway_complex_table(table):
    """Parse one Flyway tier table, handling its multi-type row structure.

    The table contains three kinds of rows after the two-row group header:

    1. Name-only rows  — engine name in col 0, all tier cells empty.
       Multiple consecutive name-only rows (e.g. "Azure SQL Database",
       "Azure SQL Database Managed Instance", "Amazon RDS") share the
       NEXT data row's version and tier values.

    2. Sub-header divider rows  — engine name in col 0, tier column labels
       ("Community", "Teams", …) repeated in the other cells.
       Marks the start of a new single-engine group whose subsequent data
       rows all belong to that engine.

    3. Data rows  — version text in col 0, emoji status in tier cells.
       Emitted as one engine entry; engine name comes from whichever
       context is active (pending_names or current_engine).
    """
    rows = table.find_all('tr')
    if not rows:
        return []

    def clean(text):
        return re.sub(r'\s+', ' ', text.replace('\xa0', ' ')).strip()

    def cell_names(cell):
        """Extract possibly-multiple engine names from a cell (via <p> tags or newlines)."""
        names = [p.get_text(strip=True) for p in cell.find_all('p') if p.get_text(strip=True)]
        if not names:
            raw = cell.get_text(separator='\n', strip=True)
            names = [s.strip() for s in raw.splitlines() if s.strip()]
        return [clean(n) for n in names if clean(n)]

    # Find the tier-name header row (contains 'community', 'teams', etc.).
    # This row doubles as the FIRST sub-header: its cells[0] holds the first engine
    # group name(s).  We read tier column indices from it AND seed pending_names /
    # current_engine so the immediately-following data rows are attributed correctly.
    tier_indices = {}
    data_start = 0
    pending_names = []
    current_engine = None

    for i, row in enumerate(rows):
        cells = row.find_all(['th', 'td'])
        texts = [c.get_text(strip=True).lower() for c in cells]
        present = [col for col in _FLYWAY_TIER_NAMES if col in texts]
        if len(present) >= 2:
            tier_indices = {col: texts.index(col) for col in present}
            data_start = i + 1
            # Treat cells[0] of this row as the first engine group
            if cells:
                first_group = cell_names(cells[0])
                if len(first_group) == 1:
                    current_engine = first_group[0]
                elif len(first_group) > 1:
                    pending_names = first_group
            break

    if not tier_indices:
        return []

    def tier_statuses(cells):
        return {
            col: parse_status(cells[idx].get_text(strip=True))
                 if idx is not None and idx < len(cells) else None
            for col, idx in tier_indices.items()
        }

    def has_tier_data(cells):
        """Any tier cell contains a recognisable emoji/status."""
        return any(s is not None for s in tier_statuses(cells).values())

    def is_sub_header(cells):
        """Other cells re-state tier column names → divider for a new engine group."""
        texts = [c.get_text(strip=True).lower() for c in cells]
        return sum(1 for col in _FLYWAY_TIER_NAMES if col in texts[1:]) >= 2

    def extract_versions(cell):
        v = [p.get_text(strip=True) for p in cell.find_all('p') if p.get_text(strip=True)]
        if not v:
            raw = cell.get_text(separator='\n', strip=True)
            v = [s.strip() for s in raw.splitlines() if s.strip()]
        return v

    result = []

    for row in rows[data_start:]:
        cells = row.find_all(['th', 'td'])
        if not cells:
            continue
        first_text = clean(cells[0].get_text(strip=True))
        if not first_text:
            continue

        if is_sub_header(cells):
            # e.g. "SQL Server | Community | Teams | Enterprise | …"
            pending_names = []
            current_engine = first_text
            continue

        if not has_tier_data(cells):
            # Name-only row — add to the shared-data group
            pending_names.append(first_text)
            current_engine = None
            continue

        # Data row — emit one entry per active engine name
        versions = extract_versions(cells[0])
        if not versions:
            continue
        tiers = tier_statuses(cells)

        if pending_names:
            for name in pending_names:
                result.append({'name': name, 'versions': versions, **tiers})
            pending_names = []
        elif current_engine:
            result.append({'name': current_engine, 'versions': versions, **tiers})

    return result


def find_flyway_sections(soup):
    """Group Flyway tier data under their parent database-category section.

    Navigation:
      1. <h3 id="*variant*"> → feature tab name (strip "variants").
      2. Within each h3, <h4 id="*supporteddatabasesandversions*"> gates
         the table that follows it.
      3. Each table is parsed by _parse_flyway_complex_table, which derives
         engine names from the table rows themselves.
    """
    results = []

    variant_h3s = [
        tag for tag in soup.find_all('h3')
        if 'variant' in (tag.get('id') or '').lower()
    ]
    logger.info(f'Flyway: found {len(variant_h3s)} variant h3 section(s)')

    for h3 in variant_h3s:
        raw = h3.get_text(strip=True)
        feature_name = re.sub(r'\s*variants?\s*', ' ', raw, flags=re.IGNORECASE).strip()
        feature_name = re.sub(r'\s+', ' ', feature_name).strip()

        engines_data = []
        seen_tables = set()  # guard against multiple h4s pointing to the same table

        for elem in h3.find_all_next():
            if elem.name == 'h3' and 'variant' in (elem.get('id') or '').lower():
                break

            if (elem.name == 'h4'
                    and 'supporteddatabasesandversions' in (elem.get('id') or '').lower()):
                table = elem.find_next('table')
                if table and id(table) not in seen_tables:
                    seen_tables.add(id(table))
                    engines_data.extend(_parse_flyway_complex_table(table))

        if engines_data:
            results.append({'feature': feature_name, 'engines': engines_data})
            logger.info(f'  Flyway section "{feature_name}": {len(engines_data)} row(s)')

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
    if source['key'] == 'flyway':
        version_support = find_flyway_sections(soup)
        if not version_support:
            logger.info('Flyway: h3/h4 strategy found nothing — falling back to tier-table scan')
            version_support = find_version_tables(tables)
    else:
        version_support = find_version_tables(tables)

    if not cloud_matrix and not version_support:
        # Log table headers to help diagnose why nothing matched.
        for i, t in enumerate(tables[:10]):
            hdrs, _ = expand_rowspans(t)
            if hdrs:
                logger.warning(f'  table[{i}] headers: {hdrs}')
            else:
                first = t.find('tr')
                if first:
                    sample = [c.get_text(strip=True)[:30] for c in first.find_all(['th', 'td'])[:6]]
                    logger.warning(f'  table[{i}] no headers detected, first-row cells: {sample}')
        logger.warning(f'No usable data extracted from {url}')
        return None

    # Sanity-check quality: a cloud matrix where every support value is None
    # almost certainly means emoji/status parsing failed — discard it.
    def has_real_support(matrix):
        return any(
            status is not None
            for row in matrix
            for status in row.get('support', {}).values()
        )

    if cloud_matrix and not has_real_support(cloud_matrix):
        logger.warning(
            f'Cloud matrix for {source["name"]} has no non-null support values '
            f'(emoji parsing likely failed) — discarding matrix'
        )
        cloud_matrix = []
        engines = []

def scrape_product(source):
    """Scrape one product page. Returns product dict or None on failure."""
    if not BS4_AVAILABLE:
        logger.warning('beautifulsoup4 not installed — install it to enable scraping')
        return None

    # Special handling for Monitor: scrape main page for versions + individual pages for platform support
    if source['key'] == 'monitor':
        logger.info('Scraping Redgate Monitor with versions and platform support')

        url = source['source_url']
        try:
            html = fetch_html(url)
        except Exception as exc:
            logger.error(f'Failed to fetch {url}: {exc}')
            return None

        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')

        # Get cloud matrix
        engines, cloud_matrix = find_cloud_matrix(tables)

        # Get version support from main page (Monitoring feature)
        version_support = find_version_tables(tables)
        logger.info(f'Found {len(version_support)} version table(s) on main page')

        # Add platform support for each engine
        platform_support_entry = {'feature': 'Supported Platforms', 'engines': []}
        for engine_name in ['SQL Server', 'PostgreSQL', 'Oracle', 'MySQL', 'MongoDB']:
            result_data = scrape_platform_support(engine_name)
            if result_data:
                platform_support_entry['engines'].append({
                    'name': engine_name,
                    'versions': result_data.get('versions', []),
                    'platform_support': result_data.get('platform_support', {})
                })
                logger.info(f'Added platform support for {engine_name}')

        # Add platform support entry if we found data
        if platform_support_entry['engines']:
            version_support.append(platform_support_entry)

        result = {
            'key': source['key'],
            'name': source['name'],
            'source_url': source['source_url'],
            'engines': engines if engines else ['SQL Server', 'PostgreSQL', 'Oracle', 'MySQL', 'MongoDB'],
            'cloud_matrix': cloud_matrix,
            'version_support': version_support
        }

        return result if result['version_support'] else None

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
    if source['key'] == 'flyway':
        version_support = find_flyway_sections(soup)
        if not version_support:
            logger.info('Flyway: h3/h4 strategy found nothing — falling back to tier-table scan')
            version_support = find_version_tables(tables)
    else:
        version_support = find_version_tables(tables)

    if not cloud_matrix and not version_support:
        # Log table headers to help diagnose why nothing matched.
        for i, t in enumerate(tables[:10]):
            hdrs, _ = expand_rowspans(t)
            if hdrs:
                logger.warning(f'  table[{i}] headers: {hdrs}')
            else:
                first = t.find('tr')
                if first:
                    sample = [c.get_text(strip=True)[:30] for c in first.find_all(['th', 'td'])[:6]]
                    logger.warning(f'  table[{i}] no headers detected, first-row cells: {sample}')
        logger.warning(f'No usable data extracted from {url}')
        return None

    # Sanity-check quality: a cloud matrix where every support value is None
    # almost certainly means emoji/status parsing failed — discard it.
    def has_real_support(matrix):
        return any(
            status is not None
            for row in matrix
            for status in row.get('support', {}).values()
        )

    if cloud_matrix and not has_real_support(cloud_matrix):
        logger.warning(
            f'Cloud matrix for {source["name"]} has no non-null support values '
            f'(emoji parsing likely failed) — discarding matrix'
        )
        cloud_matrix = []
        engines = []

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
        existing = existing_by_key.get(source['key'])
        result = scrape_product(source)

        if result is None:
            # Complete scrape failure — keep existing
            if existing:
                logger.info(f"Keeping existing data for {source['name']} (scrape failed)")
                products.append(existing)
            else:
                logger.warning(f"No data available for {source['name']}, skipping")
            continue

        # Partial scrape: fill gaps from existing data so we never regress
        if existing:
            if not result.get('cloud_matrix') and existing.get('cloud_matrix'):
                logger.info(f"Keeping existing cloud_matrix for {source['name']} (scrape got none)")
                result['cloud_matrix'] = existing['cloud_matrix']
                result['engines'] = existing.get('engines', result['engines'])
            if not result.get('version_support') and existing.get('version_support'):
                logger.info(f"Keeping existing version_support for {source['name']} (scrape got none)")
                result['version_support'] = existing['version_support']

        products.append(result)

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'products': products,
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f'Written {len(products)} product(s) to {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
