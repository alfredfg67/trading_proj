import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st
import os
from dotenv import load_dotenv
from app.core.config import settings

try:
    DB_URL = settings.DATABASE_URL
except:
    load_dotenv()
    DB_URL = os.getenv("DATABASE_URL", "sqlite:///./trading.db")

@st.cache_resource
def get_engine():
    db_url = DB_URL.replace("+aiosqlite", "") if "aiosqlite" in DB_URL else DB_URL
    return create_engine(db_url, echo=False)

@st.cache_data(ttl=300)
def load_trades(start_date=None, end_date=None, instrument_types=None, sessions=None, symbols=None, strategies=None, _engine=None):
    try:
        engine = _engine or get_engine()
        query = "SELECT * FROM trades WHERE 1=1"
        params = {}

        if start_date:
            query += " AND entry_time >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND entry_time <= :end_date"
            params["end_date"] = end_date

        if instrument_types and "All" not in instrument_types:
            placeholders = ", ".join([f":inst_{i}" for i in range(len(instrument_types))])
            query += f" AND instrument_type IN ({placeholders})"
            for i, inst in enumerate(instrument_types):
                params[f"inst_{i}"] = inst

        if sessions and "All" not in sessions:
            placeholders = ", ".join([f":sess_{i}" for i in range(len(sessions))])
            query += f" AND session IN ({placeholders})"
            for i, sess in enumerate(sessions):
                params[f"sess_{i}"] = sess

        if symbols:
            placeholders = ", ".join([f":sym_{i}" for i in range(len(symbols))])
            query += f" AND symbol IN ({placeholders})"
            for i, sym in enumerate(symbols):
                params[f"sym_{i}"] = sym

        if strategies:
            placeholders = ", ".join([f":strat_{i}" for i in range(len(strategies))])
            query += f" AND strategy_tag IN ({placeholders})"
            for i, strat in enumerate(strategies):
                params[f"strat_{i}"] = strat

        query += " ORDER BY entry_time ASC"
        df = pd.read_sql_query(text(query), engine, params=params)

        for col in ["entry_time", "exit_time"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])

        return df

    except SQLAlchemyError as e:
        st.error(f"Database error: {str(e)}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected error loading trades: {str(e)}")
        return pd.DataFrame()

def get_filter_options(df):
    """Return unique values for filters, ensuring 'All' is always included for multiselect defaults."""
    if df.empty:
        return {
            "symbols": [],
            "instrument_types": ["All"],
            "sessions": ["All"],
            "strategies": ["All"],
        }

    options = {
        "symbols": sorted(df["symbol"].unique().tolist()),
        "instrument_types": sorted(df["instrument_type"].unique().tolist()),
        "sessions": sorted(df["session"].unique().tolist()),
        "strategies": sorted(df["strategy_tag"].dropna().unique().tolist()) if "strategy_tag" in df.columns else [],
    }

    # Ensure "All" is always available in filter lists (for default values)
    for key in ["instrument_types", "sessions", "strategies"]:
        if key in options and options[key]:
            if "All" not in options[key]:
                options[key] = ["All"] + options[key]
        elif key in options:
            options[key] = ["All"]

    return options