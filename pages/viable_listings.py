import streamlit as st
import pandas as pd
import os
import subprocess

# ─── Page Config ───────────────────────────────────────────────
st.set_page_config(page_title="Viable Listings", layout="wide")
st.title("📈 Viable Listings")

DETAILS_FILE = "CSV_data/active_vehicle_details.csv"
VERDICT_FILE = "CSV_data/ai_verdicts.csv"

# ─── Load and Merge Data ───────────────────────────────────────
if not os.path.exists(DETAILS_FILE) or not os.path.exists(VERDICT_FILE):
    st.info("Required CSV files are missing.")
    st.stop()

active_df = pd.read_csv(DETAILS_FILE)
verdict_df = pd.read_csv(VERDICT_FILE)

if "url" not in active_df.columns:
    st.info("Active vehicle data is missing the 'url' column.")
    st.stop()

if "url" not in verdict_df.columns:
    st.info("AI verdict data is missing the 'url' column.")
    st.stop()

verdict_cols = [
    "url",
    "verdict",
    "profit_margin_percent",
    "max_bid",
    "resale_estimate",
]
existing_verdict_cols = [col for col in verdict_cols if col in verdict_df.columns]
verdict_df = verdict_df[existing_verdict_cols]

for required_col in ["verdict", "profit_margin_percent"]:
    if required_col not in verdict_df.columns:
        verdict_df[required_col] = pd.NA

merged_df = pd.merge(active_df, verdict_df, on="url", how="left")

if merged_df.empty:
    st.info("No listings available.")
    st.stop()

# ─── Filter for Active & Viable ────────────────────────────────
merged_df["profit_margin_percent_numeric"] = pd.to_numeric(
    merged_df["profit_margin_percent"]
    .astype(str)
    .str.replace("%", "", regex=False),
    errors="coerce",
)

verdict_profitable = merged_df["verdict"].astype(str).str.contains(
    "profitable", case=False, na=False
)
positive_margin = merged_df["profit_margin_percent_numeric"].fillna(0) > 0

viable_df = merged_df.loc[verdict_profitable | positive_margin].copy()

if viable_df.empty:
    st.info("No viable listings found.")
    st.stop()

viable_df["profit_margin_percent"] = viable_df["profit_margin_percent_numeric"].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else ""
)
viable_df.drop(columns=["profit_margin_percent_numeric"], inplace=True)

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
    "max_bid",
    "resale_estimate",
]

available_cols = [col for col in show_cols if col in viable_df.columns]

viable_df = viable_df[available_cols]
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
                result = subprocess.run(
                    ["python", "scripts/update_bids.py", "--urls", *selected_urls],
                    check=True,
                    capture_output=True,
                    text=True,
                )
                st.success("✅ Selected listings refreshed.")
                if result.stdout:
                    st.text(result.stdout)
            except subprocess.CalledProcessError as e:
                error_message = e.stderr or e.stdout or str(e)
                st.error(f"❌ Update failed: {error_message}")
