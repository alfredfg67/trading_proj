"""
Database connection and query functions
"""
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import streamlit as st
from app.core.config import settings

# Engine singleton
@st.cache_resource
def get_engine():
    """Create and cache database engine"""
    try:
        # Try to use settings from main app
        db_url = settings.DATABASE_URL
    except:
        # Fallback to environment variable
        import os
        from dotenv import load_dotenv
        load_dotenv()
        db_url = os.getenv("DATABASE_URL", "sqlite:///./trading.db")

    # Convert sqlite+aiosqlite to sqlite for synchronous access
    if "aiosqlite" in db_url:
        db_url = db_url.replace("+aiosqlite", "")

    engine = create_engine(db_url, echo=False)
    return engine

@st.cache_data(ttl=300)  # 5 minute cache
def load_trades(
    start_date=None,
    end_date=None,
    instrument_types=None,
    sessions=None,
    symbols=None,
    strategies=None,
    _engine=None
):
    """Load trades with filters applied"""
    try:
        engine = _engine or get_engine()

        # Build query
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

        # Execute
        df = pd.read_sql_query(text(query), engine, params=params)

        # Convert timestamps
        for col in ["entry_time", "exit_time"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col])

        return df

    except SQLAlchemyError as e:
        st.error(f"Database error: {str(e)}")
        return pd.DataFrame()

def get_filter_options(df):
    """Get unique values for filter dropdowns"""
    if df.empty:
        return {
            "symbols": [],
            "instrument_types": [],
            "sessions": [],
            "strategies": [],
        }

    return {
        "symbols": sorted(df["symbol"].unique().tolist()),
        "instrument_types": sorted(df["instrument_type"].unique().tolist()),
        "sessions": sorted(df["session"].unique().tolist()),
        "strategies": sorted(df["strategy_tag"].dropna().unique().tolist()) if "strategy_tag" in df.columns else [],
    }

@st.cache_data(ttl=300)
def get_date_range(_engine=None):
    """Get min and max dates from trades table"""
    engine = _engine or get_engine()
    try:
        query = "SELECT MIN(entry_time) as min_date, MAX(entry_time) as max_date FROM trades"
        result = pd.read_sql_query(text(query), engine)
        return result["min_date"].iloc[0], result["max_date"].iloc[0]
    except:
        return None, None