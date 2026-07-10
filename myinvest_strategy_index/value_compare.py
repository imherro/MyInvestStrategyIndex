from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from myinvest_strategy_index.config import Settings, ensure_runtime_dirs


@dataclass(frozen=True)
class ValueCompareInstrument:
    code: str
    name: str
    kind: str
    source: str
    color: str


LAYERED_WEIGHT_COMPONENTS: tuple[tuple[str, float], ...] = (
    ("h21052.CSI", 0.0),
    ("CN2296.CNI", 0.11134917573934289),
    ("h20269.CSI", 0.0),
    ("480092.CNI", 0.25223535553619914),
    ("518880.SH", 0.2364154687244581),
    ("511260.SH", 0.4),
)
LAYERED_CASH_WEIGHT = 0.0

FOUR_ASSET_CALMAR_WEIGHT_COMPONENTS: tuple[tuple[str, float], ...] = (
    ("399606.SZ", 0.158012392945),
    ("480092.CNI", 0.184545205429),
    ("518880.SH", 0.257442401626),
    ("511260.SH", 0.4),
)

THREE_ASSET_CALMAR_WEIGHT_COMPONENTS: tuple[tuple[str, float], ...] = (
    ("399606.SZ", 0.216810075139),
    ("480092.CNI", 0.383189924861),
    ("518880.SH", 0.4),
)
DRAWDOWN_RISK_LOOKBACK_YEARS = 10
DRAWDOWN_REBALANCE_CANDIDATES: tuple[dict[str, object], ...] = (
    {"id": "none", "name": "不再平衡", "rule": "none"},
    {"id": "daily", "name": "每日再平衡", "rule": "daily"},
    {"id": "monthly", "name": "月度再平衡", "rule": "calendar", "period": "monthly"},
    {"id": "quarterly", "name": "季度再平衡", "rule": "calendar", "period": "quarterly"},
    {"id": "semiannual", "name": "半年度再平衡", "rule": "calendar", "period": "semiannual"},
    {"id": "annual", "name": "年度再平衡", "rule": "calendar", "period": "annual"},
    {"id": "threshold_5", "name": "偏离5%再平衡", "rule": "threshold", "threshold": 0.05},
    {"id": "threshold_10", "name": "偏离10%再平衡", "rule": "threshold", "threshold": 0.10},
    {"id": "threshold_15", "name": "偏离15%再平衡", "rule": "threshold", "threshold": 0.15},
)


DEFAULT_VALUE_COMPARE_INSTRUMENTS: tuple[ValueCompareInstrument, ...] = (
    ValueCompareInstrument(
        code="h21052.CSI",
        name="国信价值全收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#7C3AED",
    ),
    ValueCompareInstrument(
        code="CN2296.CNI",
        name="创成长R收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#0F766E",
    ),
    ValueCompareInstrument(
        code="h20269.CSI",
        name="红利低波全收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#D97706",
    ),
    ValueCompareInstrument(
        code="480092.CNI",
        name="自由现金流R收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#B23A48",
    ),
    ValueCompareInstrument(
        code="518880.SH",
        name="518880 华安黄金ETF",
        kind="etf",
        source="Tushare fund_daily + fund_adj",
        color="#C68A00",
    ),
    ValueCompareInstrument(
        code="511260.SH",
        name="511260 十年国债ETF",
        kind="etf",
        source="Tushare fund_daily + fund_adj",
        color="#475569",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_EQUAL_WEIGHT_STRATEGY",
        name="策略等权组合",
        kind="synthetic_equal_weight",
        source="国信价值/创成长R/红利低波/自由现金流R 动态等权",
        color="#111827",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_RISK_PARITY_STRATEGY",
        name="风险平价组合",
        kind="synthetic_risk_parity",
        source="国信价值/创成长R/红利低波/自由现金流R 滚动60日波动率倒数加权",
        color="#2563EB",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_LAYERED_WEIGHT_STRATEGY",
        name="分层权重模型（Calmar全样本最优）",
        kind="synthetic_layered_weight",
        source=(
            "Calmar全样本最优：国信价值0%+创成长R11.13%+红利低波0%+"
            "自由现金流R25.22%+黄金ETF23.64%+十年国债ETF40.00%；"
            "样本外70/30验证输给等权，仅作参考"
        ),
        color="#0891B2",
    ),
)

VALUE_COMPARE_BACKGROUND = ValueCompareInstrument(
    code="000001.SH",
    name="上证指数",
    kind="background",
    source="Tushare index_daily",
    color="#94A3B8",
)

CHINEXT_TOTAL_RETURN_INSTRUMENTS: tuple[ValueCompareInstrument, ...] = (
    ValueCompareInstrument(
        code="399606.SZ",
        name="399006 创业板指全收益指数",
        kind="index",
        source="Tushare index_daily；399006 的全收益指数代码 399606.SZ",
        color="#0F766E",
    ),
    ValueCompareInstrument(
        code="CN2673.CNI",
        name="399673 创业板50全收益指数",
        kind="index",
        source="Tushare index_daily；399673 的全收益指数代码 CN2673.CNI",
        color="#2563EB",
    ),
    ValueCompareInstrument(
        code="CN2296.CNI",
        name="399296 创成长全收益指数",
        kind="index",
        source="Tushare index_daily；399296 的全收益指数代码 CN2296.CNI",
        color="#D97706",
    ),
)

FOUR_ASSET_CALMAR_INSTRUMENTS: tuple[ValueCompareInstrument, ...] = (
    ValueCompareInstrument(
        code="399606.SZ",
        name="399006 创业板R（全收益）",
        kind="index",
        source="Tushare index_daily；399006 的全收益指数代码 399606.SZ",
        color="#0F766E",
    ),
    ValueCompareInstrument(
        code="480092.CNI",
        name="自由现金流R收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#B23A48",
    ),
    ValueCompareInstrument(
        code="518880.SH",
        name="518880 华安黄金ETF",
        kind="etf",
        source="Tushare fund_daily + fund_adj",
        color="#C68A00",
    ),
    ValueCompareInstrument(
        code="511260.SH",
        name="511260 十年国债ETF",
        kind="etf",
        source="Tushare fund_daily + fund_adj",
        color="#2563EB",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_FOUR_ASSET_EQUAL_WEIGHT",
        name="四资产等权组合",
        kind="synthetic_equal_weight",
        source="创业板R/自由现金流R/黄金ETF/十年国债ETF 动态等权",
        color="#111827",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_FOUR_ASSET_CALMAR_LAYERED",
        name="分层权重模型（Calmar全样本最优）",
        kind="synthetic_layered_weight",
        source=(
            "Calmar全样本最优：创业板R15.80%+自由现金流R18.45%+"
            "黄金ETF25.74%+十年国债ETF40.00%"
        ),
        color="#0891B2",
    ),
)

THREE_ASSET_CALMAR_INSTRUMENTS: tuple[ValueCompareInstrument, ...] = (
    ValueCompareInstrument(
        code="399606.SZ",
        name="399006 创业板R（全收益）",
        kind="index",
        source="Tushare index_daily；399006 的全收益指数代码 399606.SZ",
        color="#0F766E",
    ),
    ValueCompareInstrument(
        code="480092.CNI",
        name="自由现金流R收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#B23A48",
    ),
    ValueCompareInstrument(
        code="518880.SH",
        name="518880 华安黄金ETF",
        kind="etf",
        source="Tushare fund_daily + fund_adj",
        color="#C68A00",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_THREE_ASSET_EQUAL_WEIGHT",
        name="三资产等权组合",
        kind="synthetic_equal_weight",
        source="创业板R/自由现金流R/黄金ETF 动态等权",
        color="#111827",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_THREE_ASSET_CALMAR_LAYERED",
        name="分层权重模型（Calmar全样本最优）",
        kind="synthetic_layered_weight",
        source="Calmar全样本最优：创业板R21.68%+自由现金流R38.32%+黄金ETF40.00%",
        color="#0891B2",
    ),
)

CASHFLOW_GROWTH_COMPARE_INSTRUMENTS: tuple[ValueCompareInstrument, ...] = (
    ValueCompareInstrument(
        code="480092.CNI",
        name="自由现金流R收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#B23A48",
    ),
    ValueCompareInstrument(
        code="CN2296.CNI",
        name="创成长R收益指数",
        kind="index",
        source="Tushare index_daily",
        color="#0F766E",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_CASHFLOW_GROWTH_EQUAL_WEIGHT",
        name="双指数等权组合",
        kind="synthetic_equal_weight",
        source="自由现金流R/创成长R 动态等权",
        color="#111827",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_CASHFLOW_GROWTH_RISK_PARITY",
        name="双指数风险平价组合",
        kind="synthetic_risk_parity",
        source="自由现金流R/创成长R 滚动60日波动率倒数加权",
        color="#2563EB",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_CASHFLOW_GROWTH_DRAWDOWN_RISK",
        name="最大回撤风险平价组合",
        kind="synthetic_drawdown_risk",
        source="自由现金流R/创成长R 最近10年最大回撤绝对值倒数加权",
        color="#7C2D12",
    ),
    ValueCompareInstrument(
        code="VIRTUAL_CASHFLOW_GROWTH_DRAWDOWN_REBALANCED_BEST",
        name="最大回撤风险平价最优再平衡组合",
        kind="synthetic_drawdown_rebalance_best",
        source="在不再平衡/日/月/季/半年/年/偏离阈值规则中按Calmar选优",
        color="#9333EA",
    ),
)


def get_value_compare_payload(settings: Settings, *, refresh: bool = False) -> dict[str, object]:
    return _get_compare_payload(
        settings,
        instruments=DEFAULT_VALUE_COMPARE_INSTRUMENTS,
        background=VALUE_COMPARE_BACKGROUND,
        layered_components=LAYERED_WEIGHT_COMPONENTS,
        layered_cash_weight=LAYERED_CASH_WEIGHT,
        refresh=refresh,
    )


def get_chinext_total_return_payload(settings: Settings, *, refresh: bool = False) -> dict[str, object]:
    return _get_compare_payload(
        settings,
        instruments=CHINEXT_TOTAL_RETURN_INSTRUMENTS,
        background=None,
        layered_components=(),
        layered_cash_weight=0.0,
        refresh=refresh,
    )


def get_four_asset_calmar_payload(settings: Settings, *, refresh: bool = False) -> dict[str, object]:
    return _get_compare_payload(
        settings,
        instruments=FOUR_ASSET_CALMAR_INSTRUMENTS,
        background=None,
        layered_components=FOUR_ASSET_CALMAR_WEIGHT_COMPONENTS,
        layered_cash_weight=0.0,
        refresh=refresh,
    )


def get_three_asset_calmar_payload(settings: Settings, *, refresh: bool = False) -> dict[str, object]:
    return _get_compare_payload(
        settings,
        instruments=THREE_ASSET_CALMAR_INSTRUMENTS,
        background=None,
        layered_components=THREE_ASSET_CALMAR_WEIGHT_COMPONENTS,
        layered_cash_weight=0.0,
        refresh=refresh,
    )


def get_cashflow_growth_compare_payload(settings: Settings, *, refresh: bool = False) -> dict[str, object]:
    return _get_compare_payload(
        settings,
        instruments=CASHFLOW_GROWTH_COMPARE_INSTRUMENTS,
        background=VALUE_COMPARE_BACKGROUND,
        layered_components=(),
        layered_cash_weight=0.0,
        refresh=refresh,
    )


def _get_compare_payload(
    settings: Settings,
    *,
    instruments: tuple[ValueCompareInstrument, ...],
    background: ValueCompareInstrument | None,
    layered_components: tuple[tuple[str, float], ...],
    layered_cash_weight: float,
    refresh: bool,
) -> dict[str, object]:
    ensure_runtime_dirs(settings)
    instrument_records = [asdict(item) for item in instruments]
    series: dict[str, list[dict[str, object]]] = {}
    histories: dict[str, pd.DataFrame] = {}
    errors: list[dict[str, str]] = []
    updated_at = datetime.now().isoformat(timespec="seconds")

    for instrument in instruments:
        if instrument.kind.startswith("synthetic_"):
            continue
        try:
            history = load_or_fetch_value_history(settings, instrument, refresh=refresh)
            histories[instrument.code] = history
            series[instrument.code] = _history_records(history)
        except Exception as exc:
            errors.append({"code": instrument.code, "name": instrument.name, "error": str(exc)})

    component_items = [
        item for item in instruments if not item.kind.startswith("synthetic_") and item.code in histories
    ]
    component_histories = [histories[item.code] for item in component_items]
    component_codes = [item.code for item in component_items]
    rebalance_analysis: dict[str, object] | None = None
    drawdown_rebalance_result: tuple[dict[str, object], pd.DataFrame] | None = None
    for instrument in instruments:
        if not instrument.kind.startswith("synthetic_"):
            continue
        try:
            if instrument.kind == "synthetic_risk_parity":
                history = _build_risk_parity_history(component_histories)
            elif instrument.kind == "synthetic_drawdown_risk":
                history = _build_drawdown_risk_history(component_histories)
            elif instrument.kind == "synthetic_drawdown_rebalance_best":
                if drawdown_rebalance_result is None:
                    drawdown_rebalance_result = _build_drawdown_rebalance_analysis(
                        component_histories,
                        component_codes=component_codes,
                    )
                rebalance_analysis, history = drawdown_rebalance_result
            elif instrument.kind == "synthetic_layered_weight":
                history = _build_layered_weight_history(
                    histories,
                    layered_components=layered_components,
                    cash_weight=layered_cash_weight,
                )
            else:
                history = _build_equal_weight_history(component_histories)
            series[instrument.code] = _history_records(history)
        except Exception as exc:
            errors.append({"code": instrument.code, "name": instrument.name, "error": str(exc)})

    background_series: list[dict[str, object]] = []
    if background is not None:
        try:
            background_history = load_or_fetch_value_history(settings, background, refresh=refresh)
            background_series = _history_records(background_history)
        except Exception as exc:
            errors.append({"code": background.code, "name": background.name, "error": str(exc)})

    return {
        "ok": not errors or bool(series),
        "updated_at": updated_at,
        "refresh": refresh,
        "instruments": instrument_records,
        "series": series,
        "background": asdict(background) if background is not None else None,
        "background_series": background_series,
        "rebalance_analysis": rebalance_analysis,
        "errors": errors,
    }


def load_or_fetch_value_history(
    settings: Settings, instrument: ValueCompareInstrument, *, refresh: bool = False
) -> pd.DataFrame:
    if instrument.kind.startswith("synthetic_"):
        raise RuntimeError("Synthetic strategy history is computed from index histories")
    path = _cache_path(settings, instrument)
    if path.exists() and not refresh:
        return _load_cached_history(path)

    if instrument.kind == "etf":
        history = _fetch_tushare_fund(settings, instrument)
    else:
        history = _fetch_tushare_index(settings, instrument)
    path.parent.mkdir(parents=True, exist_ok=True)
    history.to_csv(path, index=False, encoding="utf-8")
    return history


def _history_records(history: pd.DataFrame) -> list[dict[str, object]]:
    frame = history.sort_values("date").copy()
    output: list[dict[str, object]] = []
    for row in frame.to_dict("records"):
        output.append(
            {
                "date": pd.Timestamp(row["date"]).strftime("%Y-%m-%d"),
                "close": _round_float(row["close"]),
                "value": _round_float(row["value"]),
            }
        )
    return output


def _build_equal_weight_history(histories: list[pd.DataFrame]) -> pd.DataFrame:
    if len(histories) < 2:
        raise RuntimeError("At least two index histories are required for equal-weight series")
    returns: list[pd.Series] = []
    all_dates: set[pd.Timestamp] = set()
    for index, history in enumerate(histories):
        window = history.sort_values("date").drop_duplicates("date", keep="last").copy()
        if window.empty:
            continue
        series = window.set_index("date")["value"].astype(float)
        all_dates.update(pd.Timestamp(date) for date in series.index)
        returns.append(series.pct_change().rename(f"asset_{index}"))
    if not returns or not all_dates:
        raise RuntimeError("Index histories have no usable rows")

    value = 1.0
    rows: list[dict[str, object]] = []
    for index, date in enumerate(sorted(all_dates)):
        if index > 0:
            available_returns = [float(item.loc[date]) for item in returns if date in item.index and pd.notna(item.loc[date])]
            if available_returns:
                value *= 1.0 + sum(available_returns) / len(available_returns)
        rows.append({"date": date, "close": value, "value": value})
    return _normalize_history(pd.DataFrame(rows))


def _build_risk_parity_history(histories: list[pd.DataFrame], *, window: int = 60) -> pd.DataFrame:
    if len(histories) < 2:
        raise RuntimeError("At least two index histories are required for risk parity series")

    returns: list[pd.Series] = []
    all_dates: set[pd.Timestamp] = set()
    for index, history in enumerate(histories):
        frame = history.sort_values("date").drop_duplicates("date", keep="last").copy()
        if frame.empty:
            continue
        value = frame.set_index("date")["value"].astype(float)
        all_dates.update(pd.Timestamp(date) for date in value.index)
        returns.append(value.pct_change().rename(f"asset_{index}"))
    if not returns or not all_dates:
        raise RuntimeError("Index histories have no usable rows")

    value = 1.0
    trailing_returns: list[list[float]] = [[] for _ in returns]
    rows: list[dict[str, object]] = []
    for row_index, date in enumerate(sorted(all_dates)):
        available: list[tuple[int, float, float]] = []
        for asset_index, series in enumerate(returns):
            if date not in series.index or pd.isna(series.loc[date]):
                continue
            daily_return = float(series.loc[date])
            vol = _trailing_volatility(trailing_returns[asset_index], window)
            available.append((asset_index, daily_return, vol))

        if row_index > 0 and available:
            weights = _inverse_volatility_weights([vol for _, _, vol in available])
            portfolio_return = sum(item[1] * weight for item, weight in zip(available, weights))
            value *= 1.0 + portfolio_return

        rows.append({"date": date, "close": value, "value": value})

        for asset_index, series in enumerate(returns):
            if date in series.index and pd.notna(series.loc[date]):
                daily_return = float(series.loc[date])
                if math.isfinite(daily_return):
                    trailing_returns[asset_index].append(daily_return)

    return _normalize_history(pd.DataFrame(rows))


def _build_drawdown_risk_history(
    histories: list[pd.DataFrame],
    *,
    lookback_years: int = DRAWDOWN_RISK_LOOKBACK_YEARS,
) -> pd.DataFrame:
    if len(histories) < 2:
        raise RuntimeError("At least two index histories are required for drawdown-risk series")

    values: list[pd.Series] = []
    starts: list[pd.Timestamp] = []
    ends: list[pd.Timestamp] = []
    for history in histories:
        frame = history.sort_values("date").drop_duplicates("date", keep="last").copy()
        if frame.empty:
            continue
        series = frame.set_index("date")["value"].astype(float).sort_index()
        values.append(series)
        starts.append(pd.Timestamp(series.index.min()))
        ends.append(pd.Timestamp(series.index.max()))
    if len(values) < 2:
        raise RuntimeError("Index histories have no usable rows")

    end = min(ends)
    lookback_start = end - pd.DateOffset(years=lookback_years)
    risks = []
    for series in values:
        window = series[(series.index >= lookback_start) & (series.index <= end)]
        if len(window) < 2:
            window = series[series.index <= end]
        risks.append(_max_drawdown_risk(window))
    weights = _inverse_drawdown_weights(risks)

    start = max(starts)
    dates = sorted(
        {
            pd.Timestamp(date)
            for series in values
            for date in series.index
            if start <= pd.Timestamp(date) <= end
        }
    )
    if len(dates) < 2:
        raise RuntimeError("Drawdown-risk components have no overlapping history")

    returns = [series.pct_change() for series in values]
    value = 1.0
    rows: list[dict[str, object]] = []
    for index, date in enumerate(dates):
        if index > 0:
            available = [
                (float(series.loc[date]), weights[asset_index])
                for asset_index, series in enumerate(returns)
                if date in series.index and pd.notna(series.loc[date]) and math.isfinite(float(series.loc[date]))
            ]
            total_weight = sum(weight for _, weight in available)
            if available and total_weight > 0:
                portfolio_return = sum(daily_return * weight for daily_return, weight in available) / total_weight
                value *= 1.0 + portfolio_return
        rows.append({"date": date, "close": value, "value": value})

    return _normalize_history(pd.DataFrame(rows))


def _build_drawdown_rebalance_analysis(
    histories: list[pd.DataFrame],
    *,
    component_codes: list[str],
    lookback_years: int = DRAWDOWN_RISK_LOOKBACK_YEARS,
) -> tuple[dict[str, object], pd.DataFrame]:
    values = _aligned_value_frame(histories, component_codes)
    candidates = [
        _simulate_drawdown_rebalance(values, candidate, lookback_years=lookback_years)
        for candidate in DRAWDOWN_REBALANCE_CANDIDATES
    ]
    candidates.sort(key=_rebalance_candidate_sort_key, reverse=True)
    best = candidates[0]
    start_date = pd.Timestamp(values.index.min()).strftime("%Y-%m-%d")
    end_date = pd.Timestamp(values.index.max()).strftime("%Y-%m-%d")
    candidate_records = [{key: value for key, value in item.items() if key != "history"} for item in candidates]
    analysis = {
        "ok": True,
        "objective": "Calmar",
        "lookback_years": lookback_years,
        "start_date": start_date,
        "end_date": end_date,
        "best_rule_id": best["id"],
        "best_rule_name": best["name"],
        "best_metrics": best["metrics"],
        "best_final_weights": best["final_weights"],
        "candidates": candidate_records,
    }
    return analysis, best["history"]


def _aligned_value_frame(histories: list[pd.DataFrame], component_codes: list[str]) -> pd.DataFrame:
    if len(histories) < 2:
        raise RuntimeError("At least two index histories are required for rebalance analysis")
    series_list: list[pd.Series] = []
    for code, history in zip(component_codes, histories, strict=False):
        frame = history.sort_values("date").drop_duplicates("date", keep="last").copy()
        if frame.empty:
            continue
        series = frame.set_index("date")["value"].astype(float).sort_index().rename(code)
        series_list.append(series)
    if len(series_list) < 2:
        raise RuntimeError("Rebalance components have no usable rows")
    values = pd.concat(series_list, axis=1, join="inner").dropna()
    values = values[(values > 0).all(axis=1)].sort_index()
    if len(values) < 2:
        raise RuntimeError("Rebalance components have no overlapping history")
    return values


def _simulate_drawdown_rebalance(
    values: pd.DataFrame,
    candidate: dict[str, object],
    *,
    lookback_years: int,
) -> dict[str, object]:
    dates = list(values.index)
    returns = values.pct_change().replace([math.inf, -math.inf], math.nan).fillna(0.0)
    current_weights, _ = _drawdown_target_weights(values, dates[0], lookback_years=lookback_years)
    value = 1.0
    daily_returns: list[float] = []
    rows: list[dict[str, object]] = [{"date": dates[0], "close": value, "value": value}]
    total_turnover = 0.0
    rebalance_count = 0

    for index in range(1, len(dates)):
        date = dates[index]
        asset_returns = returns.loc[date].astype(float)
        portfolio_return = float((current_weights * asset_returns).sum())
        if not math.isfinite(portfolio_return):
            portfolio_return = 0.0
        value *= 1.0 + portfolio_return
        daily_returns.append(portfolio_return)
        rows.append({"date": date, "close": value, "value": value})

        drifted_weights = current_weights * (1.0 + asset_returns)
        total_weight = float(drifted_weights.sum())
        if math.isfinite(total_weight) and total_weight > 0:
            current_weights = drifted_weights / total_weight

        if index >= len(dates) - 1:
            continue

        should_rebalance = False
        target_weights: pd.Series | None = None
        rule = str(candidate.get("rule") or "")
        if rule == "daily":
            should_rebalance = True
        elif rule == "calendar":
            should_rebalance = _should_calendar_rebalance(
                pd.Timestamp(date),
                pd.Timestamp(dates[index + 1]),
                str(candidate.get("period") or "monthly"),
            )
        elif rule == "threshold":
            target_weights, _ = _drawdown_target_weights(values, date, lookback_years=lookback_years)
            threshold = float(candidate.get("threshold") or 0.0)
            should_rebalance = float((target_weights - current_weights).abs().max()) >= threshold

        if should_rebalance:
            if target_weights is None:
                target_weights, _ = _drawdown_target_weights(values, date, lookback_years=lookback_years)
            turnover = 0.5 * float((target_weights - current_weights).abs().sum())
            if math.isfinite(turnover) and turnover > 1e-12:
                total_turnover += turnover
                rebalance_count += 1
            current_weights = target_weights

    history = _normalize_history(pd.DataFrame(rows))
    _, final_risks = _drawdown_target_weights(values, dates[-1], lookback_years=lookback_years)
    metrics = _portfolio_metrics_from_returns(
        history,
        daily_returns=daily_returns,
        total_turnover=total_turnover,
        rebalance_count=rebalance_count,
    )
    return {
        "id": str(candidate["id"]),
        "name": str(candidate["name"]),
        "rule": str(candidate["rule"]),
        "metrics": metrics,
        "final_weights": {code: _json_float(current_weights.get(code)) for code in values.columns},
        "final_risks": {code: _json_float(final_risks.get(code)) for code in values.columns},
        "history": history,
    }


def _drawdown_target_weights(
    values: pd.DataFrame,
    date: pd.Timestamp,
    *,
    lookback_years: int,
) -> tuple[pd.Series, dict[str, float]]:
    end = pd.Timestamp(date)
    lookback_start = end - pd.DateOffset(years=lookback_years)
    risks: dict[str, float] = {}
    for code in values.columns:
        series = values.loc[(values.index >= lookback_start) & (values.index <= end), code]
        if len(series) < 2:
            series = values.loc[values.index <= end, code]
        risks[code] = _max_drawdown_risk(series)
    weights = _inverse_drawdown_weights(list(risks.values()))
    return pd.Series(weights, index=values.columns, dtype=float), risks


def _should_calendar_rebalance(date: pd.Timestamp, next_date: pd.Timestamp, period: str) -> bool:
    return _period_key(date, period) != _period_key(next_date, period)


def _period_key(date: pd.Timestamp, period: str) -> tuple[int, int]:
    if period == "annual":
        return (date.year, 0)
    if period == "semiannual":
        return (date.year, 0 if date.month <= 6 else 1)
    if period == "quarterly":
        return (date.year, (date.month - 1) // 3)
    return (date.year, date.month)


def _portfolio_metrics_from_returns(
    history: pd.DataFrame,
    *,
    daily_returns: list[float],
    total_turnover: float,
    rebalance_count: int,
) -> dict[str, object]:
    first = history.iloc[0]
    last = history.iloc[-1]
    first_value = float(first["value"])
    last_value = float(last["value"])
    days = max((pd.Timestamp(last["date"]) - pd.Timestamp(first["date"])).days, 1)
    years = max(days / 365.25, 1 / 365.25)
    total_return = last_value / first_value - 1.0 if first_value > 0 else math.nan
    annualized_return = (last_value / first_value) ** (1.0 / years) - 1.0 if first_value > 0 and last_value > 0 else math.nan

    return_series = pd.Series([item for item in daily_returns if math.isfinite(item)], dtype=float)
    annualized_volatility = (
        float(return_series.std(ddof=1)) * math.sqrt(252) if len(return_series) > 1 else 0.0
    )
    annualized_excess = float(return_series.mean()) * 252 if len(return_series) else math.nan
    sharpe = annualized_excess / annualized_volatility if annualized_volatility > 1e-12 else math.nan

    peak = -math.inf
    max_drawdown = 0.0
    for raw_value in history["value"]:
        value = float(raw_value)
        if not math.isfinite(value) or value <= 0:
            continue
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value / peak - 1.0)
    calmar = annualized_return / abs(max_drawdown) if abs(max_drawdown) > 1e-12 else math.nan
    return {
        "total_return": _json_float(total_return),
        "annualized_return": _json_float(annualized_return),
        "annualized_volatility": _json_float(annualized_volatility),
        "max_drawdown": _json_float(max_drawdown),
        "sharpe": _json_float(sharpe),
        "calmar": _json_float(calmar),
        "total_turnover": _json_float(total_turnover),
        "annualized_turnover": _json_float(total_turnover / years),
        "rebalance_count": rebalance_count,
    }


def _rebalance_candidate_sort_key(item: dict[str, object]) -> tuple[bool, float, float, float, float]:
    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else {}
    calmar = _as_finite_number(metrics.get("calmar")) if isinstance(metrics, dict) else None
    annualized_return = _as_finite_number(metrics.get("annualized_return")) if isinstance(metrics, dict) else None
    max_drawdown = _as_finite_number(metrics.get("max_drawdown")) if isinstance(metrics, dict) else None
    total_turnover = _as_finite_number(metrics.get("total_turnover")) if isinstance(metrics, dict) else None
    return (
        calmar is not None,
        calmar if calmar is not None else -math.inf,
        annualized_return if annualized_return is not None else -math.inf,
        -abs(max_drawdown) if max_drawdown is not None else -math.inf,
        -(total_turnover if total_turnover is not None else math.inf),
    )


def _build_layered_weight_history(
    histories: dict[str, pd.DataFrame],
    *,
    layered_components: tuple[tuple[str, float], ...],
    cash_weight: float,
) -> pd.DataFrame:
    missing = [code for code, _ in layered_components if code not in histories]
    if missing:
        raise RuntimeError(f"Missing layered model components: {', '.join(missing)}")

    total_weight = cash_weight + sum(weight for _, weight in layered_components)
    if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
        raise RuntimeError(f"Layered model weights must sum to 1.0, got {total_weight:.6f}")

    values: dict[str, pd.Series] = {}
    starts: list[pd.Timestamp] = []
    ends: list[pd.Timestamp] = []
    for code, _ in layered_components:
        frame = histories[code].sort_values("date").drop_duplicates("date", keep="last").copy()
        if frame.empty:
            raise RuntimeError(f"Layered model component has no rows: {code}")
        series = frame.set_index("date")["value"].astype(float).sort_index()
        values[code] = series
        starts.append(pd.Timestamp(series.index.min()))
        ends.append(pd.Timestamp(series.index.max()))

    start = max(starts)
    end = min(ends)
    dates = sorted(
        {
            pd.Timestamp(date)
            for series in values.values()
            for date in series.index
            if start <= pd.Timestamp(date) <= end
        }
    )
    if len(dates) < 2:
        raise RuntimeError("Layered model components have no overlapping history")

    returns = {code: series.pct_change() for code, series in values.items()}
    value = 1.0
    rows: list[dict[str, object]] = []
    for index, date in enumerate(dates):
        if index > 0:
            portfolio_return = 0.0
            for code, weight in layered_components:
                daily_return = returns[code].get(date, math.nan)
                if math.isfinite(float(daily_return)):
                    portfolio_return += weight * float(daily_return)
            value *= 1.0 + portfolio_return
        rows.append({"date": date, "close": value, "value": value})

    return _normalize_history(pd.DataFrame(rows))


def _trailing_volatility(values: list[float], window: int) -> float:
    recent = [item for item in values[-window:] if math.isfinite(item)]
    if len(recent) < 20:
        return math.nan
    return float(pd.Series(recent).std(ddof=1))


def _inverse_volatility_weights(volatilities: list[float]) -> list[float]:
    valid = [item for item in volatilities if math.isfinite(item) and item > 1e-9]
    fallback = float(pd.Series(valid).median()) if valid else math.nan
    inverse: list[float] = []
    for vol in volatilities:
        usable = vol if math.isfinite(vol) and vol > 1e-9 else fallback
        inverse.append(1.0 / usable if math.isfinite(usable) and usable > 1e-9 else 1.0)
    total = sum(inverse)
    if total <= 0:
        return [1.0 / len(volatilities)] * len(volatilities)
    return [item / total for item in inverse]


def _max_drawdown_risk(series: pd.Series) -> float:
    if series.empty:
        return math.nan
    peak = -math.inf
    max_drawdown = 0.0
    for raw_value in series.dropna():
        value = float(raw_value)
        if not math.isfinite(value) or value <= 0:
            continue
        peak = max(peak, value)
        if math.isfinite(peak) and peak > 0:
            max_drawdown = min(max_drawdown, value / peak - 1.0)
    return abs(max_drawdown)


def _inverse_drawdown_weights(risks: list[float]) -> list[float]:
    if not risks:
        return []
    positive = [risk for risk in risks if math.isfinite(risk) and risk > 1e-9]
    floor = min(positive) * 0.5 if positive else 1e-9
    inverse = []
    for risk in risks:
        usable = risk if math.isfinite(risk) and risk > 1e-9 else floor
        inverse.append(1.0 / usable)
    total = sum(inverse)
    if not math.isfinite(total) or total <= 0:
        return [1.0 / len(risks)] * len(risks)
    return [item / total for item in inverse]


def _load_cached_history(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, parse_dates=["date"])
    return _normalize_history(frame)


def _fetch_tushare_index(settings: Settings, instrument: ValueCompareInstrument) -> pd.DataFrame:
    if not settings.tushare_token:
        raise RuntimeError("TUSHARE_TOKEN is not configured")
    try:
        import tushare as ts
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError(f"tushare import failed: {exc}") from exc

    pro = ts.pro_api(settings.tushare_token)
    daily = _fetch_tushare_index_yearly(pro, instrument.code)
    if daily.empty:
        raise RuntimeError(f"Tushare returned no index_daily rows for {instrument.code}")

    frame = daily[["trade_date", "close"]].copy()
    frame["date"] = pd.to_datetime(frame["trade_date"], format="%Y%m%d", errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["value"] = frame["close"]
    return _normalize_history(frame[["date", "close", "value"]])


def _fetch_tushare_fund(settings: Settings, instrument: ValueCompareInstrument) -> pd.DataFrame:
    if not settings.tushare_token:
        raise RuntimeError("TUSHARE_TOKEN is not configured")
    try:
        import tushare as ts
    except Exception as exc:  # pragma: no cover - import guard
        raise RuntimeError(f"tushare import failed: {exc}") from exc

    pro = ts.pro_api(settings.tushare_token)
    daily = _fetch_tushare_yearly(pro, "fund_daily", instrument.code, start_year=2012)
    if daily.empty:
        raise RuntimeError(f"Tushare returned no fund_daily rows for {instrument.code}")
    adj = _fetch_tushare_yearly(pro, "fund_adj", instrument.code, start_year=2012)

    frame = daily[["trade_date", "close"]].copy()
    if not adj.empty and "adj_factor" in adj:
        frame = frame.merge(adj[["trade_date", "adj_factor"]], on="trade_date", how="left")
    else:
        frame["adj_factor"] = 1.0
    frame["date"] = pd.to_datetime(frame["trade_date"], format="%Y%m%d", errors="coerce")
    frame["close"] = pd.to_numeric(frame["close"], errors="coerce")
    frame["adj_factor"] = pd.to_numeric(frame["adj_factor"], errors="coerce").fillna(1.0)
    frame["value"] = frame["close"] * frame["adj_factor"]
    return _normalize_history(frame[["date", "close", "value"]])


def _fetch_tushare_index_yearly(pro: object, ts_code: str) -> pd.DataFrame:
    return _fetch_tushare_yearly(pro, "index_daily", ts_code, start_year=2005)


def _fetch_tushare_yearly(pro: object, method_name: str, ts_code: str, *, start_year: int) -> pd.DataFrame:
    method = getattr(pro, method_name)
    frames: list[pd.DataFrame] = []
    history_end = datetime.now().strftime("%Y%m%d")
    end_year = int(history_end[:4])
    for year in range(start_year, end_year + 1):
        start = f"{year}0101"
        end = history_end if year == end_year else f"{year}1231"
        part = method(ts_code=ts_code, start_date=start, end_date=end)
        if part is not None and not part.empty:
            frames.append(part)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates(["trade_date"]).sort_values("trade_date")


def _normalize_history(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    output["date"] = pd.to_datetime(output["date"], errors="coerce")
    output["close"] = pd.to_numeric(output["close"], errors="coerce")
    output["value"] = pd.to_numeric(output["value"], errors="coerce")
    output = output.dropna(subset=["date", "close", "value"])
    output = output.sort_values("date").drop_duplicates("date", keep="last")
    if output.empty:
        raise RuntimeError("history rows could not be normalized")
    return output.reset_index(drop=True)


def _cache_path(settings: Settings, instrument: ValueCompareInstrument) -> Path:
    safe_code = instrument.code.replace(".", "_")
    return settings.cache_dir / f"value_compare_{safe_code}.csv"


def _round_float(value: object) -> float:
    number = float(value)
    if not math.isfinite(number):
        return 0.0
    return round(number, 6)


def _json_float(value: object) -> float | None:
    number = _as_finite_number(value)
    if number is None:
        return None
    return round(number, 6)


def _as_finite_number(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number
