import xmltodict
import urllib.request
import re
import json
import csv
import logging
from datetime import datetime, date, timezone

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

CONFIG_FILE = 'config/products.csv'
OUTPUT_FILE = 'data/products.json'


def load_config():
    """Load product config keyed by S3 product key."""
    config = {}
    with open(CONFIG_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = row['key'].strip()
            config[key] = {
                'name': row['name'].strip(),
                'doc_url': row['doc_url'].strip(),
                'release_notes_url': row['release_notes_url'].strip(),
            }
    return config


def version_compare(v1, v2):
    """Return the higher of two version strings."""
    v1_clean = re.sub(r'-.*', '', v1)
    v2_clean = re.sub(r'-.*', '', v2)
    try:
        v1_parts = list(map(int, v1_clean.split('.')))
        v2_parts = list(map(int, v2_clean.split('.')))
        for a, b in zip(v1_parts, v2_parts):
            if a < b:
                return v2
            if a > b:
                return v1
        return v1 if len(v1_parts) >= len(v2_parts) else v2
    except ValueError:
        return v1


def status_for_date(date_str):
    """Return 'current', 'previous', or 'old' based on update year."""
    try:
        year = int(date_str[:4])
        current_year = date.today().year
        if year == current_year:
            return 'current'
        if year == current_year - 1:
            return 'previous'
    except (ValueError, TypeError):
        pass
    return 'old'


def fetch_xml(url):
    with urllib.request.urlopen(url, timeout=15) as f:
        return xmltodict.parse(f.read())


def get_products():
    """List all product keys from the S3 checkforupdates prefix."""
    url = 'https://redgate-download.s3.eu-west-1.amazonaws.com/?delimiter=/&prefix=checkforupdates/'
    data = fetch_xml(url)
    prefixes = data['ListBucketResult']['CommonPrefixes']
    return [
        p['Prefix'].replace('checkforupdates/', '').replace('/', '')
        for p in prefixes
    ]


def get_updates(products):
    """Fetch version, download URL, and update date for each product."""
    results = []
    for product in products:
        url = f'https://redgate-download.s3.eu-west-1.amazonaws.com/?delimiter=/&prefix=checkforupdates/{product}/'
        try:
            data = fetch_xml(url)
            contents = data['ListBucketResult'].get('Contents')
            if not contents:
                logger.warning(f'No contents for {product}')
                continue

            # Contents is a dict (single file) or list (multiple files)
            if isinstance(contents, dict):
                contents = [contents]

            latest_date = ''
            latest_link = ''
            for item in contents:
                if item['LastModified'] > latest_date:
                    latest_date = item['LastModified']
                    latest_link = f"https://download.red-gate.com/{item['Key']}"

            version_match = re.search(r'(\d+\.\d+\.\d+)', latest_link)
            version = version_match.group(1) if version_match else ''

            results.append({
                'key': product,
                'version': version,
                'download_url': latest_link,
                'updated': latest_date[:10],
            })
        except Exception as e:
            logger.error(f'Failed to get updates for {product}: {e}')

    return results


def get_flyway_cli():
    """Fetch the latest Flyway CLI version from the Maven S3 bucket."""
    base_url = 'https://redgate-download.s3.eu-west-1.amazonaws.com/?delimiter=/&prefix=maven/release/com/redgate/flyway/flyway-commandline/'
    data = fetch_xml(base_url)
    prefixes = data['ListBucketResult']['CommonPrefixes']

    best_version = '0.0.0'
    for p in prefixes:
        v = p['Prefix'].replace('maven/release/com/redgate/flyway/flyway-commandline/', '').replace('/', '')
        best_version = version_compare(best_version, v)

    version_url = f'{base_url.split("?")[0]}?delimiter=/&prefix=maven/release/com/redgate/flyway/flyway-commandline/{best_version}/'
    data = fetch_xml(version_url)
    contents = data['ListBucketResult']['Contents']
    if isinstance(contents, dict):
        contents = [contents]

    updated = ''
    for item in contents:
        if item['Key'].endswith('.zip') and item['LastModified'] > updated:
            updated = item['LastModified']

    return {
        'key': 'FlywayCLI',
        'name': 'Flyway CLI',
        'version': best_version,
        'download_url': f'https://download.red-gate.com/maven/release/com/redgate/flyway/flyway-commandline/{best_version}',
        'updated': updated[:10],
        'status': status_for_date(updated[:10]),
        'doc_url': 'https://documentation.red-gate.com/fd',
        'release_notes_url': 'https://documentation.red-gate.com/fd/release-notes',
    }


_TDM_DOWNLOAD = 'https://documentation.red-gate.com/testdatamanager/getting-started/installation/download-links'
_TDM_RELEASE_NOTES = 'https://documentation.red-gate.com/testdatamanager/graphical-user-interface-gui/gui-release-notes'


def get_tdm():
    """Fetch TDM package last-modified date from S3.

    EAP/TDM.zip is used only to determine the last-modified date shared by
    all TDM components. Each component gets its own product entry.
    """
    url = 'https://redgate-download.s3.eu-west-1.amazonaws.com/?prefix=EAP/TDM.zip'
    data = fetch_xml(url)
    contents = data['ListBucketResult'].get('Contents')
    if not contents:
        raise ValueError('EAP/TDM.zip not found in S3')
    if isinstance(contents, list):
        contents = contents[0]
    updated = contents['LastModified'][:10]
    status = status_for_date(updated)

    return [
        {
            'key': 'TDMGui',
            'name': 'Test Data Manager GUI',
            'version': '',
            'download_url': _TDM_DOWNLOAD,
            'updated': updated,
            'status': status,
            'doc_url': 'https://documentation.red-gate.com/tdm',
            'release_notes_url': _TDM_RELEASE_NOTES,
        },
        {
            'key': 'TDMAnonymize',
            'name': 'Test Data Manager Anonymize',
            'version': '',
            'download_url': _TDM_DOWNLOAD,
            'updated': updated,
            'status': status,
            'doc_url': 'https://documentation.red-gate.com/testdatamanager/graphical-user-interface-gui/anonymization-treatments',
            'release_notes_url': _TDM_RELEASE_NOTES,
        },
        {
            'key': 'TDMSubsetting',
            'name': 'Test Data Manager Subsetting',
            'version': '',
            'download_url': _TDM_DOWNLOAD,
            'updated': updated,
            'status': status,
            'doc_url': 'https://documentation.red-gate.com/testdatamanager/graphical-user-interface-gui/subsetting-treatments',
            'release_notes_url': _TDM_RELEASE_NOTES,
        },
    ]


def main():
    config = load_config()
    logger.info('Fetching product list from S3...')
    product_keys = get_products()
    logger.info(f'Found {len(product_keys)} products')

    logger.info('Fetching update info...')
    updates = get_updates(product_keys)

    products = []
    for item in updates:
        key = item['key']
        cfg = config.get(key, {})
        products.append({
            'key': key,
            'name': cfg.get('name', key),
            'version': item['version'],
            'download_url': item['download_url'],
            'updated': item['updated'],
            'status': status_for_date(item['updated']),
            'doc_url': cfg.get('doc_url', 'https://documentation.red-gate.com'),
            'release_notes_url': cfg.get('release_notes_url', ''),
        })

    logger.info('Fetching Flyway CLI...')
    try:
        flyway = get_flyway_cli()
        products.append(flyway)
    except Exception as e:
        logger.error(f'Failed to get Flyway CLI: {e}')

    logger.info('Fetching Test Data Manager...')
    try:
        products.extend(get_tdm())
    except Exception as e:
        logger.error(f'Failed to get TDM: {e}')

    products.sort(key=lambda x: x['name'].lower())

    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'products': products,
    }

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    logger.info(f'Written {len(products)} products to {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
