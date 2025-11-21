"""
Scrape drug data from Horizon HTML web pages and save as CSVs in the data folder.

- Preferred medical drugs:
    https://www.horizonblue.com/providers/products-programs/pharmacy/pharmacy-programs/preferred-medical-drugs

- Prior authorization / medical necessity list:
    https://www.horizonblue.com/members/plans/horizon-pharmacy/prescription-drug-lists/prior-authorization-medical-necessity-determination-medicine-list
"""

import requests
from bs4 import BeautifulSoup
import csv
import os
import re


def fetch_html(url):
    response = requests.get(url)
    response.raise_for_status()
    return response.text


def clean_drug_name(name: str) -> str:
    """
    Remove trademark / registration symbols from drug names.

    Examples:
        'Stimufend®'   -> 'Stimufend'
        'Ziextenzo™'   -> 'Ziextenzo'
        'Something (R)' -> 'Something'
        'Brand (TM)'    -> 'Brand'
    """
    if not name:
        return name

    # Remove common special symbols
    for sym in ["®", "™", "℠", "©"]:
        name = name.replace(sym, "")

    # Remove textual TM/R variants like (R), (TM), (SM) etc.
    name = re.sub(r"\(\s*R\s*\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(\s*TM\s*\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(\s*SM\s*\)", "", name, flags=re.IGNORECASE)

    # Collapse double spaces that might result from removals
    name = re.sub(r"\s{2,}", " ", name)

    return name.strip()


def normalize_camel_case(name: str) -> str:
    """
    Normalize drug name to camel case and standard spacing.
    """
    if not name:
        return name
    # Remove extra spaces
    name = re.sub(r'\s+', ' ', name.strip())
    # Convert to camel case (title case)
    name = name.title()
    return name


def parse_preferred_drugs(html):
    """
    Parse preferred medical drugs.

    Assumptions (based on your description):
    - Category is in an <h2>.
    - The table right after that <h2> contains the drugs for that category.
    - Table columns (index-based):
        0: Drug Status
        1: Drug Name
        2: HCPCS
        3: Manufacturer
    """
    soup = BeautifulSoup(html, 'html.parser')
    drugs = []

    # Find all h2s that likely represent categories
    for heading in soup.find_all('h2'):
        category = heading.get_text(strip=True)
        if not category:
            continue

        # Get the first table following this h2
        table = heading.find_next('table')
        if table is None:
            continue

        rows = table.find_all('tr')
        if not rows:
            continue

        # Skip header row (index 0)
        for row in rows[1:]:
            cells = row.find_all('td')
            # Make sure we have at least 4 columns as assumed
            if len(cells) < 4:
                continue

            drug_status = cells[0].get_text(strip=True)

            raw_drug_name = cells[1].get_text(strip=True)
            drug_name = clean_drug_name(raw_drug_name)
            drug_name = normalize_camel_case(drug_name)

            hcpcs = cells[2].get_text(strip=True)
            manufacturer = cells[3].get_text(strip=True)

            # Skip empty rows
            if not drug_name:
                continue

            drugs.append({
                'Category': category,
                'Drug Status': drug_status,
                'Drug Name': drug_name,
                'HCPCS': hcpcs,
                'Manufacturer': manufacturer,
            })

    return drugs


def parse_pa_mnd_list(html):
    """
    Parse prior authorization / medical necessity determination list.

    Assumptions:
    - Drug names live inside:
        <ul class="list-unstyled column-count-2 li-pad-t-10 li-text-wrap">
            <li>Drug Name 1</li>
            <li>Drug Name 2</li>
            ...
        </ul>
    """
    soup = BeautifulSoup(html, 'html.parser')
    drugs = []

    selector = 'ul.list-unstyled.column-count-2.li-pad-t-10.li-text-wrap li'
    for li in soup.select(selector):
        raw_name = li.get_text(strip=True)
        name = clean_drug_name(raw_name)
        name = normalize_camel_case(name)
        if not name:
            continue
        drugs.append({'Drug Name': name})

    return drugs


def save_csv(data, path, fieldnames):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def main():
    preferred_url = (
        'https://www.horizonblue.com/providers/products-programs/pharmacy/'
        'pharmacy-programs/preferred-medical-drugs'
    )
    pa_mnd_url = (
        'https://www.horizonblue.com/members/plans/horizon-pharmacy/'
        'prescription-drug-lists/prior-authorization-medical-necessity-'
        'determination-medicine-list'
    )

    print('Fetching preferred medical drugs...')
    preferred_html = fetch_html(preferred_url)
    preferred_drugs = parse_preferred_drugs(preferred_html)
    save_csv(
        preferred_drugs,
        'data/preferred_drugs_list.csv',
        ['Category', 'Drug Status', 'Drug Name', 'HCPCS', 'Manufacturer']
    )
    print(f'Saved {len(preferred_drugs)} preferred drugs.')

    print('Fetching PA/MND list...')
    pa_mnd_html = fetch_html(pa_mnd_url)
    pa_mnd_list = parse_pa_mnd_list(pa_mnd_html)
    save_csv(
        pa_mnd_list,
        'data/pa_mnd_list.csv',
        ['Drug Name']
    )
    print(f'Saved {len(pa_mnd_list)} PA/MND drugs.')


if __name__ == '__main__':
    main()