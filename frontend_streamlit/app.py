# app.py — Analytic Prototype (Streamlit Frontend)
# -----------------------------------------------
# - Python-only dashboard (no HTML/CSS/JS needed)
# - Calls your FastAPI backend (local or Render)
# - Pretty background, caching, filters, CSV download

import os
import time
import base64
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ======= ENV / CONFIG =======
load_dotenv()
DEFAULT_BACKEND = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

st.set_page_config(page_title="Analytic Prototype", page_icon="📊", layout="wide")

# ======= THEME: BACKGROUND + TEXT =======
def add_bg_from_local(image_file: str):
    """Embed a background image via base64."""
    try:
        with open(image_file, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(
            f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpg;base64,{encoded}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            /* make main blocks a bit translucent (glass effect) */
            .block-container {{
                backdrop-filter: blur(6px);
                background: rgba(10, 14, 20, 0.35);
                border-radius: 16px;
                padding: 2rem 2rem 3rem 2rem;
            }}
            /* improve text contrast */
            h1, h2, h3, h4, h5, h6, p, span, label, .stMarkdown {{
                color: #f3f7ff !important;
            }}
            /* sidebar glass + contrast */
            section[data-testid="stSidebar"] > div {{
                background: rgba(10, 14, 20, 0.45);
                backdrop-filter: blur(8px);
            }}
            </style>
            """,
            unsafe_allow_html=True,
        )
    except Exception:
        # If the image isn't found, continue without styling
        pass

# If your image is in the same folder as this file: "bg.jpg"
# If it's in the repo root, change the path accordingly.
add_bg_from_local("frontend_streamlit/bg.jpg")

# ======= HEADER =======
st.title("Analytic Prototype — Solana Wallet Activity")
st.caption("Python-only dashboard powered by FastAPI + Helius → built with Streamlit")

# ======= SIDEBAR =======
with st.sidebar:
    st.header("Settings")
    backend_url = st.text_input(
        "Backend URL",
        value=DEFAULT_BACKEND,
        help="Your FastAPI base URL (local or Render). Example: https://analytic-prototype.onrender.com",
    )
    wallet = st.text_input(
        "Wallet / Address",
        value="So11111111111111111111111111111111111111112",
        help="Paste any Solana wallet or mint address",
    )
    limit = st.slider("How many recent tx?", min_value=1, max_value=50, value=10)
    auto_refresh = st.checkbox("Auto-refresh every 15 sec", value=False)
    show_local_time = st.checkbox("Show local time", value=True)
    run_btn = st.button("Fetch Transactions")

# ======= HELPERS =======
@st.cache_data(ttl=15)
def cached_get(url: str):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    return r.json()

def fetch_txs_simple(base: str, addr: str, limit: int = 10):
    url = f"{base}/wallet/{addr}/txs_simple?limit={limit}"
    return cached_get(url)

def to_dataframe(items):
    if not items:
        return pd.DataFrame()
    rows = []
    for it in items:
        tokens = it.get("token_changes", [])
        token_str = ", ".join(
            [f'{c.get("amount")} { (c.get("symbol") or "") }'.strip() for c in tokens]
        ) or "—"
        rows.append(
            {
                "signature": it.get("signature"),
                "timestamp": it.get("timestamp"),
                "type": it.get("type"),
                "token_changes": token_str,
            }
        )
    df = pd.DataFrame(rows)

    # time columns
    if "timestamp" in df.columns and not df.empty:
        df["time_utc"] = pd.to_datetime(df["timestamp"], unit="s", utc=True)
        # Local time for readability (falls back to UTC if tz issues)
        try:
            df["time_local"] = df["time_utc"].dt.tz_convert(None)
        except Exception:
            df["time_local"] = df["time_utc"]

    # Solscan direct link
    base = "https://solscan.io/tx/"
    df["tx_link"] = base + df["signature"].astype(str)

    return df

def render_table(df: pd.DataFrame, use_local_time: bool):
    if df.empty:
        st.info("No transactions found for this address.")
        return

    time_col = "time_local" if use_local_time and "time_local" in df.columns else "time_utc"
    # Reorder columns for nicer view
    view = df[[time_col, "type", "token_changes", "signature", "tx_link", "timestamp"]].copy()
    view.rename(
        columns={
            time_col: "time",
            "tx_link": "solscan",
        },
        inplace=True,
    )

    # Filter by type (UX sugar)
    types = sorted(view["type"].dropna().unique().tolist())
    chosen = st.multiselect("Filter by type", types, default=types)
    view = view[view["type"].isin(chosen)]

    st.subheader("Recent Transactions")
    # LinkColumn is available on Streamlit >= 1.25; if older, just shows text
    try:
        st.dataframe(
            view,
            use_container_width=True,
            height=460,
            column_config={
                "solscan": st.column_config.LinkColumn("Solscan", help="Open on Solscan", display_text="open"),
                "signature": st.column_config.TextColumn("signature", width="medium"),
                "type": st.column_config.TextColumn("type", width="small"),
            },
            hide_index=True,
        )
    except Exception:
        st.dataframe(view, use_container_width=True, height=460)

    # download
    csv = view.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv, file_name="transactions.csv", mime="text/csv")

# ======= MAIN LOOP =======
placeholder = st.empty()

def run_once():
    try:
        data = fetch_txs_simple(backend_url, wallet, limit)
        df = to_dataframe(data)
        with placeholder.container():
            st.success("Fetched successfully from backend.")
            render_table(df, use_local_time=show_local_time)
    except requests.HTTPError as e:
        st.error(f"HTTP error: {e.response.status_code} — {e.response.text[:300]}")
    except requests.RequestException as e:
        st.error(f"Network error: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")

if run_btn:
    run_once()

if auto_refresh and not run_btn:
    while True:
        run_once()
        time.sleep(15)
        st.experimental_rerun()

# ======= FOOTER =======
st.markdown(
    """
    <hr style="border: 1px solid #666; margin-top: 40px; margin-bottom: 10px;">
    <div style='text-align: center;'>
        <p style='color:#000000; font-size:14px;'>
            Built by <a href="https://x.com/Ola_Crrypt" target="_blank" style='color:#91c9ff; text-decoration:none; font-weight:bold;'>@Ola_Crrypt</a> 
            — A Data Science Intern
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
