import streamlit as st
import pandas as pd
import os
import subprocess

# ─── Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="Viable Listings", layout="wide")
st.title("📈 Viable Listings")

DETAILS_FILE = "CSV_data/vehicle_static_details.csv"
VERDICT_FILE = "CSV_data/ai_verdicts.csv"

# ─── Load and Merge Data ───────────────────────────────────────
if not os.path.exists(DETAILS_FILE) or not os.path.exists(VERDICT_FILE):
    st.info("Required CSV files are missing.")
    st.stop()

details_df = pd.read_csv(DETAILS_FILE)
verdict_df = pd.read_csv(VERDICT_FILE)

merged_df = pd.merge(verdict_df, details_df, on="url", suffixes=("", "_details"))

if merged_df.empty:
    st.info("No listings available.")
    st.stop()

# ─── Filter for Active & Viable ────────────────────────────────
merged_df["status"] = merged_df["status"].astype(str).str.strip().str.lower()
merged_df["profit_margin_percent"] = (
    merged_df["profit_margin_percent"]
    .astype(str)
    .str.replace("%", "", regex=False)
)
merged_df["profit_margin_percent"] = pd.to_numeric(
    merged_df["profit_margin_percent"], errors="coerce"
).fillna(0)

viable_df = merged_df[
    (merged_df["status"] == "active")
    & (
        (merged_df["verdict"].astype(str).str.lower() == "good")
        | (merged_df["profit_margin_percent"] > 0)
    )
]

if viable_df.empty:
    st.info("No viable listings found.")
    st.stop()

# ─── Display and Selection ─────────────────────────────────────
show_cols = [
    "year",
    "make",
    "model",
    "variant",
    "price",
    "bids",
    "time_remaining_or_date_sold",
    "profit_margin_percent",
    "verdict",
    "url",
]

viable_df = viable_df[show_cols]
viable_df["Select"] = False

edited_df = st.data_editor(
    viable_df,
    hide_index=True,
    column_config={
        "Select": st.column_config.CheckboxColumn(required=False),
    },
)

selected_urls = edited_df[edited_df["Select"]]["url"].tolist()

# ─── Refresh Selected ──────────────────────────────────────────
if st.button("Refresh Selected"):
    if not selected_urls:
        st.warning("No listings selected.")
    else:
        with st.spinner("Updating selected listings..."):
            try:
                subprocess.run(
                    ["python", "scripts/update_bids.py", *selected_urls],
                    check=True,
                )
                st.success("✅ Selected listings refreshed.")
            except subprocess.CalledProcessError as e:
                st.error(f"❌ Update failed: {e}")
