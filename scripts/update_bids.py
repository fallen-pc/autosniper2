import argparse
import asyncio
import os
import re
import shutil
import tempfile
from datetime import datetime
from typing import Iterable, Optional

import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

CSV_FILE_DEFAULT = "CSV_data/active_vehicle_details.csv"


# ─── Clean URL from HTML anchor tag ─────────────────────────────
def clean_url(url):
    if not isinstance(url, str):
        return ""
    match = re.search(r'href="([^"]+)"', url)
    return match.group(1) if match else url


# ─── Extract auction info ───────────────────────────────────────
def extract_bid_info(soup):
    try:
        price_elem = soup.find("span", attrs={"itemprop": "price"})
        price = price_elem.get_text(strip=True) if price_elem else "N/A"

        time_elem = soup.find("span", id="lot-closing-countdown")
        time_remaining = time_elem.get_text(strip=True) if time_elem else "Auction Ended"

        bid_elem = soup.find("a", string=re.compile(r"\d+\s+bids", re.IGNORECASE))
        bids = bid_elem.get_text(strip=True).split()[0] if bid_elem else "0"

        return price, bids, time_remaining
    except Exception as e:
        print(f"⚠️ Error extracting auction info: {e}")
        return "N/A", "0", "Auction Ended"


# ─── Fetch one listing ──────────────────────────────────────────
async def fetch_listing_data(url, page):
    try:
        await page.goto(url, timeout=15000)
        await page.wait_for_timeout(3000)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        return extract_bid_info(soup)
    except Exception as e:
        print(f"⚠️ Failed to update {url}: {e}")
        return "N/A", "0", "Auction Ended"


# ─── Main update loop ───────────────────────────────────────────
async def update_all_bids(csv_path: str = CSV_FILE_DEFAULT, urls: Optional[Iterable[str]] = None):
    if not os.path.exists(csv_path):
        print("❌ File not found:", csv_path)
        return

    df = pd.read_csv(csv_path)
    if df.empty:
        print(f"⚠️ {os.path.basename(csv_path)} is empty.")
        return

    # Ensure columns have correct dtypes
    if "price" in df.columns:
        df["price"] = df["price"].astype(str)
    if "time_remaining_or_date_sold" in df.columns:
        df["time_remaining_or_date_sold"] = df["time_remaining_or_date_sold"].astype(str)
    if "status" not in df.columns:
        df["status"] = "Unknown"

    df["clean_url"] = df["url"].apply(clean_url)

    if urls:
        target_urls = {cleaned for url in urls if (cleaned := clean_url(url))}
        if not target_urls:
            print("⚠️ No valid URLs were provided.")
            return
        df_to_update = df[df["clean_url"].isin(target_urls)]
        if df_to_update.empty:
            print("⚠️ None of the provided URLs were found in the dataset.")
            return
    else:
        df_to_update = df

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for idx, row in df_to_update.iterrows():
            url = row.get("clean_url", "")
            if not url or not url.startswith("http"):
                continue

            print(f"🔄 Updating: {url}")
            price, bids, time_or_expired = await fetch_listing_data(url, page)

            # Update fields
            df.at[idx, "price"] = price
            try:
                df.at[idx, "bids"] = int(bids)
            except Exception:
                df.at[idx, "bids"] = 0

            if re.search(r"\d+[dhm]", time_or_expired.lower()):
                df.at[idx, "time_remaining_or_date_sold"] = time_or_expired
                df.at[idx, "status"] = "Active"
            elif price != "N/A" and bids != "0":
                df.at[idx, "time_remaining_or_date_sold"] = datetime.now().strftime("%Y-%m-%d")
                df.at[idx, "status"] = "Sold"
            else:
                df.at[idx, "time_remaining_or_date_sold"] = "N/A"
                df.at[idx, "status"] = "Referred"

        await browser.close()

    # Save updated DataFrame using temp file to avoid conflicts
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv").name
    if "clean_url" in df.columns:
        clean_mask = df["clean_url"].astype(bool)
        df.loc[clean_mask, "url"] = df.loc[clean_mask, "clean_url"]
        df = df.drop(columns=["clean_url"], errors="ignore")
    df.to_csv(temp_file, index=False)
    shutil.move(temp_file, csv_path)
    print(f"✅ {os.path.basename(csv_path)} updated with status, price, bids, and auction outcome.")


# ─── Entry point ────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update bid data for vehicle listings.")
    parser.add_argument(
        "--file",
        default=CSV_FILE_DEFAULT,
        help="Path to the CSV file containing vehicle data (default: CSV_data/active_vehicle_details.csv)",
    )
    parser.add_argument(
        "--urls",
        nargs="+",
        help="Specific listing URLs to update. If omitted, all listings in the CSV are processed.",
    )

    args = parser.parse_args()

    asyncio.run(update_all_bids(csv_path=args.file, urls=args.urls))
