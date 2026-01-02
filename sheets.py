from __future__ import annotations

from datetime import date, datetime
from typing import List

import pandas as pd
import gspread


def load_data(gc: gspread.Client, sheet_id: str, worksheet_name: str) -> pd.DataFrame:
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(worksheet_name)
    records = ws.get_all_records()

    if not records:
        return pd.DataFrame(columns=["date", "minutes", "source", "updated_at"])

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["minutes"] = pd.to_numeric(df["minutes"], errors="coerce").fillna(0).astype(int)
    df["source"] = df.get("source", "manual")
    df["updated_at"] = df.get("updated_at", "")
    df = df.dropna(subset=["date"]).sort_values("date")
    return df


def upsert_day(
    gc: gspread.Client,
    sheet_id: str,
    worksheet_name: str,
    day: date,
    minutes: int,
    source: str = "manual",
) -> str:
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(worksheet_name)

    col_dates: List[str] = ws.col_values(1)  # includes header
    day_str = day.isoformat()
    now_str = datetime.utcnow().isoformat()

    if day_str in col_dates[1:]:
        row_idx = col_dates.index(day_str) + 1  # 1-indexed row number in sheet
        ws.update(f"B{row_idx}:D{row_idx}", [[minutes, source, now_str]])
        return "updated"
    else:
        ws.append_row([day_str, minutes, source, now_str])
        return "inserted"
