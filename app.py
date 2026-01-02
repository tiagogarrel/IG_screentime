import streamlit as st
import pandas as pd
from datetime import date
import gspread
from google.oauth2.service_account import Credentials

from sheets import load_data, upsert_day

# ----------------------------
# Config
# ----------------------------
SHEET_ID = st.secrets.get("SHEET_ID", "")
WORKSHEET_NAME = st.secrets.get("WORKSHEET_NAME", "screen_time")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

st.set_page_config(page_title="Screen Time Tracker", layout="wide")


# ----------------------------
# Google Sheets client
# ----------------------------
@st.cache_resource
def get_gspread_client() -> gspread.Client:
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Missing credentials: add gcp_service_account in Streamlit secrets.")

    creds_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.authorize(creds)

# ----------------------------
# Helpers (analytics)
# ----------------------------
def build_full_range(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    all_days = pd.date_range(start, end, freq="D").date
    base = pd.DataFrame({"date": all_days})

    if df.empty:
        out = base.copy()
        out["minutes"] = pd.NA
        return out

    dfr = df[(df["date"] >= start) & (df["date"] <= end)][["date", "minutes"]].copy()
    out = base.merge(dfr, on="date", how="left")
    return out


def current_streak_under_threshold(daily: pd.DataFrame, threshold: int) -> int:
    """
    Streak ending at the latest date in `daily`.
    Counts consecutive days with minutes < threshold, ignoring missing days (break streak).
    """
    if daily.empty:
        return 0

    d = daily.sort_values("date").copy()
    # Break streak on missing
    ok = d["minutes"].notna() & (d["minutes"] < threshold)

    streak = 0
    for v in reversed(ok.tolist()):
        if v:
            streak += 1
        else:
            break
    return streak


def weekday_heatmap_data(daily: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a 7x1 table (Mon..Sun) with average minutes for the selected range.
    Missing days ignored for averages.
    """
    d = daily.dropna(subset=["minutes"]).copy()
    if d.empty:
        return pd.DataFrame({"avg_minutes": [0]*7}, index=["Mon","Tue","Wed","Thu","Fri","Sat","Sun"])

    dt = pd.to_datetime(d["date"])
    d["weekday"] = dt.dt.day_name()
    # Order
    order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    agg = d.groupby("weekday")["minutes"].mean().reindex(order).fillna(0)

    # Prettier index
    idx = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
    return pd.DataFrame({"avg_minutes": agg.values}, index=idx)


# ----------------------------
# UI
# ----------------------------
st.title("📱 Screen Time Tracker")

if not SHEET_ID:
    st.error("Missing SHEET_ID in secrets.")
    st.stop()

gc = get_gspread_client()
df = load_data(gc, SHEET_ID, WORKSHEET_NAME)

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("➕ Add / update a day")

    day = st.date_input("Date", value=date.today())
    minutes = st.slider("Screen time minutes", 0, 600, 180, 5)
    minutes = st.number_input("Screen time minutes", min_value=0, max_value=2000, value=0, step=5)

    if st.button("Save day", type="primary"):
        upsert_day(gc, SHEET_ID, WORKSHEET_NAME, day, int(minutes), source="manual")
        st.success("Saved ✅")
        df = load_data(gc, SHEET_ID, WORKSHEET_NAME)

    st.divider()
    st.subheader("📆 Analysis range")

    if df.empty:
        st.info("No data yet.")
        st.stop()

    min_date = min(df["date"])
    max_date = max(df["date"])

    date_range = st.date_input(
        "Select range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if isinstance(date_range, tuple) and len(date_range) == 2:
        start, end = date_range
    else:
        st.info("Select an end date to complete the range")
        st.stop()
        
    st.divider()
    st.subheader("🎯 Goal")
    goal = st.number_input("Daily goal (minutes)", min_value=1, max_value=2000, value=10, step=5)
    streak_threshold = st.number_input("Streak threshold (minutes)", min_value=1, max_value=2000, value=10, step=5)


with right:
    st.subheader("📊 Metrics & charts")

    daily = build_full_range(df, start, end).sort_values("date").copy()

    # Missing days highlighting
    daily["missing"] = daily["minutes"].isna()

    # Metrics (ignore missing for avg, but count missing separately)
    available = daily.dropna(subset=["minutes"]).copy()
    avg = available["minutes"].mean() if not available.empty else 0
    total = available["minutes"].sum() if not available.empty else 0
    days_total = len(daily)
    missing_days = int(daily["missing"].sum())

    # Days above/below goal (only where minutes exist)
    above = int((available["minutes"] > goal).sum()) if not available.empty else 0
    below = int((available["minutes"] <= goal).sum()) if not available.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg (min/day)", f"{avg:.1f}")
    c2.metric("Days meeting goal", f"{below}")
    c3.metric("Days over goal", f"{above}")
    c4.metric("Missing days", f"{missing_days}")

    # Streak
    streak = current_streak_under_threshold(daily, int(streak_threshold))
    st.info(f"Current streak under {streak_threshold} minutes: **{streak} day(s)**")

    st.write("")
    # Line chart: fill missing as 0 for charting, but keep missing flag for table
    chart_series = daily.set_index("date")["minutes"].fillna(0)
    st.line_chart(chart_series)

    st.divider()

    col_hm, col_tbl = st.columns([1, 1.3], gap="medium")

    with col_hm:
        st.subheader("🗓️ Weekday heatmap")
        heat = weekday_heatmap_data(daily)

        st.dataframe(
            heat.style
                .format({"avg_minutes": "{:.0f}"})
                .background_gradient(cmap="RdYlGn_r"),
            use_container_width=True
        )

    with col_tbl:
        st.subheader("🗂️ Data (missing days)")

        display = daily.copy()
        display["date"] = pd.to_datetime(display["date"]).dt.strftime("%Y-%m-%d")
        display["minutes"] = display["minutes"].astype("Int64")

        def highlight_missing(row):
            return ["background-color: #ffe8e8" if row["missing"] else "" for _ in row]

        st.dataframe(
            display[["date", "minutes", "missing"]]
                .style.apply(highlight_missing, axis=1),
            use_container_width=True
        )
