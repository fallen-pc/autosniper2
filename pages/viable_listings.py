import streamlit as st
import pandas as pd
import os
import subprocess

st.set_page_config(page_title="Viable Listings", layout="wide")
st.title("💰 Viable Active Listings")

ACTIVE_FILE = "CSV_data/active_vehicle_details.csv"
VERDICT_FILE = "CSV_data/ai_verdicts.csv"

# ─── Load Data ─────────────────────────────────────────────────
if not os.path.exists(ACTIVE_FILE):
    st.warning("active_vehicle_details.csv not found.")
    st.stop()

if not os.path.exists(VERDICT_FILE):
    st.info("No AI verdicts available yet.")
    st.stop()

active_df = pd.read_csv(ACTIVE_FILE)
verdict_df = pd.read_csv(VERDICT_FILE)

df = pd.merge(active_df, verdict_df[["url", "profit_margin_percent", "verdict"]], on="url", how="inner")

def parse_profit(p):
    try:
        return float(str(p).strip("%"))
    except Exception:
        return 0.0

df["_profit_val"] = df["profit_margin_percent"].apply(parse_profit)
df = df[(df["verdict"].str.lower() == "good") & (df["_profit_val"] > 0)]

if df.empty:
    st.info("No viable listings found.")
    st.stop()

# Display table with selection checkbox
display_cols = [
    "select",
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

df_display = df.copy()
df_display.insert(0, "select", False)
edited = st.data_editor(
    df_display[display_cols],
    hide_index=True,
    use_container_width=True,
    num_rows="dynamic",
)

selected_urls = edited[edited["select"]]["url"].tolist()

if st.button("Refresh Selected"):
    if not selected_urls:
        st.info("Please select at least one listing to refresh.")
    else:
        with st.spinner("Updating selected listings..."):
            cmd = ["python", "scripts/update_bids.py", "--file", ACTIVE_FILE, "--urls", *selected_urls]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                st.success("✅ Listings updated.")
                if result.stdout:
                    st.text(result.stdout)
                st.cache_data.clear()
            else:
                st.error(f"❌ Update failed: {result.stderr or result.stdout}")

