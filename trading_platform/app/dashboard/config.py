"""
Dashboard configuration & constants
"""
from datetime import time

# Color scheme (dark theme)
COLORS = {
    "positive": "#00ff88",      # Green
    "negative": "#ff4444",      # Red
    "primary": "#00aaff",       # Blue
    "secondary": "#ffaa00",     # Orange
    "background": "#0e1117",
    "card_bg": "#1e222d",
    "text": "#f0f0f0",
    "text_muted": "#888888",
}

# Session time windows (UTC)
SESSION_WINDOWS = {
    "Asian": (time(0, 0), time(8, 0)),
    "London": (time(7, 0), time(16, 0)),
    "NY": (time(12, 0), time(21, 0)),
    "Overlap": (time(12, 0), time(16, 0)),
}

# Instrument type mapping
INSTRUMENT_TYPES = {
    "forex": "Forex",
    "stock": "Stocks",
    "synthetic": "Synthetics",
    "index": "Index",
    "crypto": "Crypto",
}

# Default metric configurations
METRICS = {
    "risk_free_rate": 0.02,      # 2% annual
    "trading_days_per_year": 252,
}

# Chart defaults
CHART_HEIGHT = 400
CHART_TEMPLATE = "plotly_dark"