from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

DEFAULT_TICKERS = ["^JKSE", "BBCA.JK", "BBRI.JK", "BBNI.JK", "BMRI.JK", "ASII.JK", "TLKM.JK", "UNVR.JK", "HMSP.JK", "ICBP.JK"]
DEFAULT_RAW_DIR = Path("data/raw")
REQUIRED_COLUMNS = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]

def safe_name(ticker: str) -> str:
    """Convert ticker to a safe filename."""
    return ticker.replace("^", "").replace(".", "_")

def download_ticker(
        ticker: str,
        start:str,
        end:str,
        auto_adjust: bool = False,
) -> pd.DataFrame:
    df = yf.download(
        ticker, 
        start=start, 
        end=end, 
        interval="1d",
        auto_adjust=auto_adjust,
        processing=False,
        actions=False,
        )
    if df is None or df.empty:
        raise ValueError(f"Tidak ada data untuk {ticker} (cek ticker/tanggal/koneksi).")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
        df.columns.name = None

        df.index = pd.to_datetime(df.index).tz_localize(None)
        df.index.name = "Date"
        return clean_prices(df, ticker)

def clean_prices(df: pd.DataFrame, ticker: str) -> pd.DataFrame:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"Data untuk {ticker} tidak lengkap. Kolom hilang: {missing}")

    df = df.sort_index()

    n_dup = int(df.index.duplicated().sum())
    if n_dup:
        logger.warning(f"Data untuk {ticker} memiliki {n_dup} duplikat. Menghapus duplikat.")
        df = df[~df.index.duplicated(keep="last")]

    n0 = len(df)
    df = df.dropna
    if len(df) < n0:
        logger.warning(f"Data untuk {ticker} memiliki {n0 - len(df)} baris dengan nilai NaN. Menghapus baris tersebut.")

    n0 = len(df)
    df = df([(df[REQUIRED_COLUMNS] >= 0).all(axis=1)])
    if len(df) < n0:
        logger.warning(f"Data untuk {ticker} memiliki {n0 - len(df)} baris dengan nilai negatif. Menghapus baris tersebut.")

    n0 = len(df)
    df = df[df["HIGH"] >= df["LOW"]]
    if len(df) < n0:
        logger.warning(f"Data untuk {ticker} memiliki {n0 - len(df)} baris dengan HIGH < LOW. Menghapus baris tersebut.")

    if df.empty:
        raise ValueError(f"Data untuk {ticker} tidak memiliki baris valid setelah pembersihan.")

    gaps = df.index.to_series().diff().dt.days
    if (gaps > 10).any():
        logger.warning(f"Data untuk {ticker} memiliki celah lebih dari 10 hari. Periksa data.",
        ticker, 
        int(gaps.max()),
        )
    return df