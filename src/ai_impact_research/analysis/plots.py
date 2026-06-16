from __future__ import annotations

import pandas as pd
import plotly.express as px


def score_distribution_figure(panel: pd.DataFrame, score_col: str):
    return px.histogram(panel, x=score_col, nbins=5, title=f"Distribution of {score_col}")


def signal_vs_outcome_figure(panel: pd.DataFrame, signal: str, outcome: str):
    hover_cols = [col for col in ["ticker", "company_id", "quarter"] if col in panel.columns]
    color = "sector" if "sector" in panel.columns else None
    return px.scatter(panel, x=signal, y=outcome, color=color, hover_data=hover_cols)


def ic_heatmap_figure(ic_summary: pd.DataFrame):
    if ic_summary.empty:
        return px.imshow([[0]], text_auto=True, title="Mean IC by Signal and Outcome")
    pivot = ic_summary.pivot(index="signal", columns="outcome", values="mean_ic")
    return px.imshow(pivot, text_auto=".3f", aspect="auto", title="Mean IC by Signal and Outcome")


def long_short_curve_figure(long_short: pd.DataFrame):
    y_col = "cumulative_return" if "cumulative_return" in long_short.columns else "cumulative_long_short"
    return px.line(long_short, x="quarter", y=y_col, markers=True, title="Long-Short Cumulative Return")
