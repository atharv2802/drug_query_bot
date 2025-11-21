# Drug Data Scraper

This module scrapes drug data from HTML web pages and saves it as CSV files in the `data/` folder.

## Usage

1. Install dependencies (from project root):
   ```powershell
   pip install -r requirements.txt
   ```
2. Run the scraper:
   ```powershell
   python scraper/scrape_drugs.py
   ```

## Configuration
- Edit `scrape_drugs.py` to specify the target URLs and parsing logic for your data source.
- Output CSV files will be saved in the `data/` folder, matching the format required by the ingestion pipeline.

## Dependencies
- `beautifulsoup4`
- `requests`

## Output
- `data/preferred_drugs_list.csv`
- `data/pa_mnd_list.csv`

## Example
See `scrape_drugs.py` for a template to get started.
