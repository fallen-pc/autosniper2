import streamlit as st
import os
import pandas as pd
import subprocess

st.set_page_config(page_title="Extract Details", layout="wide")
st.title("🛠️ Extract Vehicle Details")

LINKS_FILE = "CSV_data/all_vehicle_links.csv"
CSV_FILE = "CSV_data/vehicle_static_details.csv"
OUTPUT_FILE = CSV_FILE  # Output file for extracted details

# ─── Run Detail Scraper ─────────────────────────────────────────
if st.button("🚀 Run Detail Scraper"):
    if not os.path.exists(LINKS_FILE):
        st.error("❌ All links CSV not found.")
    else:
        with st.spinner("Extracting vehicle details from Grays listings..."):
            try:
                result = subprocess.run(
                    ["python", "scripts/extract_vehicle_details.py"],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                st.success("✅ Vehicle details successfully extracted.")
                if result.stdout:
                    st.text(result.stdout)
            except subprocess.CalledProcessError as e:
                error_msg = e.stderr or e.stdout
                st.error(f"❌ Script failed: {error_msg}")

# ─── Show Output if Available ───────────────────────────────────
if os.path.exists(OUTPUT_FILE):
    try:
        df = pd.read_csv(OUTPUT_FILE)
        if df.empty or df.columns.size == 0:
            st.warning("⚠️ No vehicle details found in the CSV.")
        else:
            st.markdown("### 📄 Extracted Vehicle Listings")
            st.write(f"Total listings: {len(df)}")

            # Make URL clickable
            if "url" in df.columns:
                df["url"] = df["url"].apply(lambda x: f'<a href="{x}" target="_blank">Link</a>' if pd.notna(x) else "N/A")

            # Move status column to the front if it exists
            cols = list(df.columns)
            if "status" in cols:
                cols.remove("status")
                df = df[["status"] + cols]

            # Use scrollable dataframe instead of HTML to avoid clipping
            st.markdown("### 📄 Extracted Vehicle Listings")
            st.dataframe(df, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Failed to load extracted vehicle data: {e}")
