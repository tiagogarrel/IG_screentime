import streamlit as st
import pandas as pd
from datetime import date, datetime
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------
# Config
# ----------------------------
SHEET_ID = st.secrets.get("SHEET_ID", "")  # id del google sheet (no el link entero)
WORKSHEET_NAME = st.secrets.get("WORKSHEET_NAME", "screen_time")

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

st.set_page_config(page_title="Screen Time Tracker", layout="wide")


# ----------------------------
# Google Sheets helpers
# ----------------------------
@st.cache_resource
def get_gspread_client():
    """
    Usa credenciales desde st.secrets["gcp_service_account"] (dict).
    """
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Faltan credenciales: agrega gcp_service_account en .streamlit/secrets.toml")

    creds_info = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
    return gspread.authorize(creds)

def load_data(gc) -> pd.DataFrame:
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(WORKSHEET_NAME)
    records = ws.get_all_records()

    if not records:
        return pd.DataFrame(columns=["date", "minutes", "source", "updated_at"])

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)
    return df

def upsert_day(gc, day: date, minutes: int, source: str = "manual"):
    sh = gc.open_by_key(SHEET_ID)
    ws = sh.worksheet(WORKSHEET_NAME)

    # traer columna A (date) para buscar coincidencias
    col_dates = ws.col_values(1)  # incluye header
    day_str = day.isoformat()

    now_str = datetime.utcnow().isoformat()

    # Si existe, update. Si no, append.
    # (col_dates[0] es header)
    if day_str in col_dates[1:]:
        row_idx = col_dates.index(day_str) + 1  # 1-indexed
        ws.update(f"B{row_idx}:D{row_idx}", [[minutes, source, now_str]])
        return "updated"
    else:
        ws.append_row([day_str, minutes, source, now_str])
        return "inserted"


# ----------------------------
# UI
# ----------------------------
st.title("📱 Screen Time Tracker")

if not SHEET_ID:
    st.warning("Configura SHEET_ID en secrets.toml")
    st.stop()

gc = get_gspread_client()
df = load_data(gc)

left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("➕ Cargar / corregir un día")
    day = st.date_input("Fecha", value=date.today())
    minutes = st.number_input("Minutos en pantalla", min_value=0, max_value=2000, value=0, step=5)

    if st.button("Guardar", type="primary"):
        action = upsert_day(gc, day, int(minutes))
        st.success(f"Guardado ✅ ({action})")
        st.cache_data.clear()
        df = load_data(gc)

    st.divider()
    st.subheader("📆 Rango de análisis")
    if df.empty:
        st.info("Todavía no hay datos en el sheet.")
        st.stop()

    min_date = min(df["date"])
    max_date = max(df["date"])

    start, end = st.date_input(
        "Seleccioná rango",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

with right:
    st.subheader("📊 Métricas y gráficas")

    # filtrar rango
    mask = (df["date"] >= start) & (df["date"] <= end)
    dfr = df.loc[mask].sort_values("date").copy()

    # asegurar todos los días del rango (para ver faltantes)
    all_days = pd.date_range(start, end, freq="D").date
    base = pd.DataFrame({"date": all_days})
    dfr_full = base.merge(dfr[["date", "minutes"]], on="date", how="left")
    dfr_full["minutes"] = dfr_full["minutes"].fillna(0).astype(int)

    avg = dfr_full["minutes"].mean()
    total = dfr_full["minutes"].sum()
    days = len(dfr_full)

    c1, c2, c3 = st.columns(3)
    c1.metric("Promedio (min/día)", f"{avg:.1f}")
    c2.metric("Total (min)", f"{total}")
    c3.metric("Días en rango", f"{days}")

    st.write("")
    st.line_chart(dfr_full.set_index("date")["minutes"])

    # gráfica por semana (suma semanal)
    weekly = dfr_full.copy()
    weekly["week"] = pd.to_datetime(weekly["date"]).dt.to_period("W").astype(str)
    weekly_s_
