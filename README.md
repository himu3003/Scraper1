# Delhi Courts — Cause List Downloader (Streamlit)

A small Streamlit app that fetches and downloads **all judge cause list PDFs** from the Delhi District Courts "Daily Board" page in real time.

## What it does
- Given a date (user input), the app scrapes:
  https://newdelhi.dcourts.gov.in/cause-list-%e2%81%84-daily-board/
- Finds all judge-specific PDF links related to that date.
- Downloads each PDF into `output/cause_lists/` (optionally grouped by date).
- Optionally creates a ZIP for easier download.

## How to run (locally)
1. Create and activate a Python virtual environment (recommended).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
