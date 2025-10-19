import requests
from bs4 import BeautifulSoup
from datetime import date
from pathlib import Path
import re
from .utils import sanitize_filename, ensure_extension
import logging
import time
import pandas as pd
from pathlib import Path

def update_excel(date_str, label, url, saved_file, status):
    """Append a row to Excel log, create file if not exists."""
    row = {
        "Date": date_str,
        "Judge Name / Label": label,
        "PDF URL": url,
        "File Name Saved": saved_file,
        "Status": status
    }

    if EXCEL_LOG_PATH.exists():
        df = pd.read_excel(EXCEL_LOG_PATH)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_excel(EXCEL_LOG_PATH, index=False)



LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.INFO)

BASE_PAGE = "https://newdelhi.dcourts.gov.in/cause-list-%e2%81%84-daily-board/"
EXCEL_LOG_PATH = Path("output") / "newdelhi.xlsx"


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/116.0 Safari/537.36"
}

def _fetch_page():
    resp = requests.get(BASE_PAGE, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    return resp.text

def _fmt_date_variants(dt: date):
    """Return possible date strings to match on page and PDF URLs."""
    variants = set()
    # Common Windows-safe formats
    variants.add(dt.strftime("%d-%m-%Y"))
    variants.add(dt.strftime("%d_%m_%Y"))
    variants.add(dt.strftime("%d/%m/%Y"))
    variants.add(dt.strftime("%d %B %Y"))    # e.g., 18 October 2025
    variants.add(dt.strftime("%#d %B %Y"))   # Windows version of %-d
    variants.add(dt.strftime("%d %b %Y"))    # e.g., 18 Oct 2025
    variants.add(dt.strftime("%m_%d_%y"))
    return list(variants)


def find_pdf_links_for_date(html: str, dt: date):
    """Find all PDF links that contain the selected date (in any common format)."""
    soup = BeautifulSoup(html, "html.parser")
    all_links = [a.get("href") for a in soup.find_all("a", href=True)]
    variants = _fmt_date_variants(dt)
    found = []

    for link in all_links:
        if not link:
            continue
        if not link.lower().endswith(".pdf"):
            continue

        # Clean link and normalize for matching
        clean_link = link.replace(" ", "").replace("_", "").replace("-", "").lower()
        for v in variants:
            if v.replace(" ", "").replace("_", "").replace("-", "").lower() in clean_link:
                full_url = requests.compat.urljoin(BASE_PAGE, link)
                label = Path(link).name
                found.append((label, full_url))
                break

    # Deduplicate links
    unique = []
    seen = set()
    for label, url in found:
        if url in seen:
            continue
        seen.add(url)
        unique.append((label, url))
    return unique

    soup = BeautifulSoup(html, "html.parser")
    # collect all anchors with .pdf
    anchors = soup.find_all("a", href=True)
    pdfs = []
    date_variants = _fmt_date_variants(dt)
    for a in anchors:
        href = a['href'].strip()
        if not href.lower().endswith(".pdf"):
            continue
        text = a.get_text(separator=" ", strip=True)
        # try to match by date in either href or text or parent nodes
        match = False
        for v in date_variants:
            if v in href or v in text:
                match = True
                break
            # check parent text
            parent_text = a.find_parent().get_text(" ", strip=True) if a.find_parent() else ""
            if v in parent_text:
                match = True
                break
        # fallback: if page contains only one date block and pdfs are listed under that block,
        # we still want to include PDF (so allow if no explicit date but the page includes chosen date somewhere)
        if not match:
            # search page for any date variant anywhere
            if any(v in soup.get_text(" ", strip=True) for v in date_variants):
                match = True

        if match:
            # resolve relative URLs
            full_url = requests.compat.urljoin(BASE_PAGE, href)
            label = text if text else Path(href).name
            pdfs.append((label, full_url))
    # attempt dedup and return
    unique = []
    seen = set()
    for label, url in pdfs:
        if url in seen:
            continue
        seen.add(url)
        unique.append((label, url))
    return unique

def download_file(url: str, dest: Path, timeout=30):
    """Download a file and save to dest Path. Returns dest on success or raise."""
    resp = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
    resp.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return dest

def fetch_and_download_cause_lists_for_date(selected_date: date, out_dir: Path, progress_callback=None):
    """
    1) Fetch the main page
    2) Parse all PDF links for the chosen date
    3) Download each PDF into out_dir
    progress_callback: Streamlit progress object (optional) - set a fraction 0..100
    Returns dict with downloaded list and failed list.
    """
    results = {"downloaded": [], "failed": [], "found_links_count": 0}
    html = _fetch_page()
    pdf_links = find_pdf_links_for_date(html, selected_date)
    results["found_links_count"] = len(pdf_links)

    if not pdf_links:
        LOGGER.info("No PDF links found for date %s", selected_date)
        return results

    total = len(pdf_links)
    count = 0
    for label, url in pdf_links:
        try:
            safe_label = sanitize_filename(label) or "cause_list"
            filename = f"{safe_label}_{selected_date.strftime('%d_%m_%Y')}.pdf"
            dest = out_dir / filename
            dest = ensure_extension(dest, ".pdf")
            # avoid re-download if exists
            if dest.exists():
                LOGGER.info("File exists, skipping download: %s", dest)
                results["downloaded"].append(dest)
            else:
                # courteous sleep between downloads
                time.sleep(0.3)
                download_file(url, dest)
                results["downloaded"].append(dest)
                LOGGER.info("Downloaded %s -> %s", url, dest)
        except Exception as e:
            LOGGER.exception("Failed to download %s : %s", url, e)
            results["failed"].append(f"{url} -> {e}")
        count += 1
        if progress_callback:
            try:
                progress_callback(int(count / total * 100))
            except Exception:
                pass

    return results
