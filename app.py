import streamlit as st
from datetime import date, datetime
from scraper.fetch_pdfs import fetch_and_download_cause_lists_for_date
from pathlib import Path
import os

st.set_page_config(page_title="Delhi Courts Cause List Downloader", page_icon="⚖️", layout="centered")
st.title(" Delhi Courts — Cause List Downloader")
st.caption("Fetch & download all judges' cause list PDFs for a chosen date (real-time).")

st.markdown("""
This app scrapes the Delhi District Courts "Daily Board" page and downloads **all judge** cause list PDFs for the date you select.
Source: https://newdelhi.dcourts.gov.in/cause-list-%e2%81%84-daily-board/
""")

# date input
selected_date = st.date_input("Select date for cause lists", date.today())

# options
create_subfolder = st.checkbox("Group downloads into subfolder by date (recommended)", value=True)
make_zip = st.checkbox("Create a ZIP archive of downloaded PDFs", value=False)

if st.button("Fetch & Download All Judge Cause Lists"):
    formatted_date = selected_date.strftime("%m-%d-%Y")
    st.info(f"Fetching cause lists for {formatted_date} ...")
    status_placeholder = st.empty()
    progress_bar = st.progress(0)

    out_dir = Path("output") / "cause_lists"
    if create_subfolder:
        out_dir = out_dir / selected_date.strftime("%m_%d_%Y")
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        results = fetch_and_download_cause_lists_for_date(selected_date, out_dir, progress_callback=progress_bar)
        if results.get("found_links_count", 0) == 0:
            st.warning(f"No cause list PDFs found for {selected_date.strftime('%m-%d-%Y')}. Try another date.")
            st.stop()
    except Exception as e:
        st.error(f"Something went wrong while fetching data: {e}")
        st.stop()

    downloaded = results.get("downloaded", [])
    failed = results.get("failed", [])
    found_links = results.get("found_links_count", 0)

    status_placeholder.success(f"Found {found_links} PDF link(s). Downloaded: {len(downloaded)}. Failed: {len(failed)}.")
    progress_bar.empty()

    if downloaded:
        st.write("### ✅ Downloaded files")
        for p in downloaded:
            st.write(f"- {p.name}")

        if make_zip:
            import zipfile
            zip_name = out_dir.with_suffix(".zip")
            with zipfile.ZipFile(zip_name, "w") as zf:
                for p in downloaded:
                    zf.write(p, arcname=p.name)
            st.success(f"ZIP archive created: {zip_name.name}")
            with open(zip_name, "rb") as f:
                st.download_button("Download ZIP", f, file_name=zip_name.name)
        else:
            # show individual download buttons
            st.write("### Download individual PDFs")
            for p in downloaded:
                with open(p, "rb") as f:
                    st.download_button(label=f"Download {p.name}", data=f, file_name=p.name)

    if failed:
        st.write("### ⚠️ Failed downloads")
        for item in failed:
            st.write(f"- {item}")

st.markdown("---")
