from __future__ import annotations

import pandas as pd


def to_calendar_quarter(value: pd.Series | str) -> pd.Series | str:
    """Convert dates to labels like 2025Q1."""
    if isinstance(value, pd.Series):
        return pd.to_datetime(value).dt.to_period("Q").astype(str)
    return str(pd.Timestamp(value).to_period("Q"))


def next_quarter_label(quarter: str, periods: int = 1) -> str:
    return str(pd.Period(quarter, freq="Q") + periods)
