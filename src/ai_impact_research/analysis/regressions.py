from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import statsmodels.formula.api as smf

DEFAULT_CONTROLS = [
    "prior_return_1q",
    "revenue_growth_qoq",
    "operating_margin_t",
    "log_market_cap",
]


@dataclass(frozen=True)
class RegressionResult:
    table: pd.DataFrame
    warning: str | None
    nobs: int
    r_squared: float | None
    formula: str


def run_pooled_regression(
    panel: pd.DataFrame,
    signal: str,
    outcome: str,
    controls: list[str] | None = None,
    add_sector_fe: bool = True,
    add_quarter_fe: bool = True,
    min_obs: int = 10,
) -> RegressionResult:
    controls = [control for control in (controls or DEFAULT_CONTROLS) if control in panel.columns]
    formula = _build_formula(panel, signal, outcome, controls, add_sector_fe, add_quarter_fe)
    subset_cols = [signal, outcome, *controls]
    if add_sector_fe and "sector" in panel.columns:
        subset_cols.append("sector")
    if add_quarter_fe and "quarter" in panel.columns:
        subset_cols.append("quarter")
    elif add_quarter_fe and "score_quarter" in panel.columns:
        subset_cols.append("score_quarter")

    data = panel.dropna(subset=[col for col in subset_cols if col in panel.columns]).copy()
    if len(data) < min_obs:
        warning = f"Need at least {min_obs} observations for OLS; got {len(data)}"
        return RegressionResult(
            table=_empty_regression_table(),
            warning=warning,
            nobs=int(len(data)),
            r_squared=None,
            formula=formula,
        )

    model_spec = smf.ols(formula=formula, data=data)
    parameter_count = int(model_spec.exog.shape[1])
    if len(data) <= parameter_count:
        warning = (
            f"Need more observations than model parameters for OLS; "
            f"got {len(data)} observations and {parameter_count} parameters"
        )
        return RegressionResult(
            table=_empty_regression_table(),
            warning=warning,
            nobs=int(len(data)),
            r_squared=None,
            formula=formula,
        )

    model = model_spec.fit()
    conf = model.conf_int()
    table = pd.DataFrame(
        {
            "term": model.params.index,
            "coefficient": model.params.values,
            "std_error": model.bse.values,
            "t_stat": model.tvalues.values,
            "p_value": model.pvalues.values,
            "conf_low": conf[0].values,
            "conf_high": conf[1].values,
            "nobs": int(model.nobs),
            "r_squared": float(model.rsquared),
            "formula": formula,
        }
    )
    return RegressionResult(
        table=table,
        warning=None,
        nobs=int(model.nobs),
        r_squared=float(model.rsquared),
        formula=formula,
    )


def run_baseline_ols(
    panel: pd.DataFrame,
    signal: str,
    outcome: str,
    add_sector_fe: bool = True,
    add_quarter_fe: bool = True,
) -> pd.DataFrame:
    result = run_pooled_regression(
        panel,
        signal,
        outcome,
        add_sector_fe=add_sector_fe,
        add_quarter_fe=add_quarter_fe,
        min_obs=5,
    )
    if result.warning:
        raise ValueError(result.warning)
    return result.table


def run_regression_grid(
    panel: pd.DataFrame,
    signals: list[str],
    outcomes: list[str],
    min_obs: int = 10,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tables: list[pd.DataFrame] = []
    warnings: list[dict[str, Any]] = []
    for signal in signals:
        if signal not in panel.columns:
            continue
        for outcome in outcomes:
            if outcome not in panel.columns:
                continue
            result = run_pooled_regression(panel, signal, outcome, min_obs=min_obs)
            if result.warning:
                warnings.append(
                    {
                        "signal": signal,
                        "outcome": outcome,
                        "warning": result.warning,
                        "nobs": result.nobs,
                        "formula": result.formula,
                    }
                )
            elif not result.table.empty:
                table = result.table.copy()
                table.insert(0, "outcome", outcome)
                table.insert(0, "signal", signal)
                tables.append(table)
    return (
        pd.concat(tables, ignore_index=True) if tables else _empty_regression_table(with_grid=True),
        pd.DataFrame(warnings),
    )


def _build_formula(
    panel: pd.DataFrame,
    signal: str,
    outcome: str,
    controls: list[str],
    add_sector_fe: bool,
    add_quarter_fe: bool,
) -> str:
    terms = [signal, *controls]
    if add_sector_fe and "sector" in panel.columns and panel["sector"].nunique(dropna=True) > 1:
        terms.append("C(sector)")
    if add_quarter_fe and "quarter" in panel.columns and panel["quarter"].nunique(dropna=True) > 1:
        terms.append("C(quarter)")
    elif (
        add_quarter_fe
        and "score_quarter" in panel.columns
        and panel["score_quarter"].nunique(dropna=True) > 1
    ):
        terms.append("C(score_quarter)")
    return f"{outcome} ~ " + " + ".join(terms)


def _empty_regression_table(with_grid: bool = False) -> pd.DataFrame:
    columns = [
        "term",
        "coefficient",
        "std_error",
        "t_stat",
        "p_value",
        "conf_low",
        "conf_high",
        "nobs",
        "r_squared",
        "formula",
    ]
    if with_grid:
        columns = ["signal", "outcome", *columns]
    return pd.DataFrame(columns=columns)
