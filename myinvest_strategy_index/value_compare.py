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

    component_histories = [
        histories[item.code]
        for item in instruments
        if not item.kind.startswith("synthetic_") and item.code in histories
    ]
    for instrument in instruments:
        if not instrument.kind.startswith("synthetic_"):
            continue
        try:
            if instrument.kind == "synthetic_risk_parity":
                history = _build_risk_parity_history(component_histories)
            elif instrument.kind == "synthetic_drawdown_risk":
                history = _build_drawdown_risk_history(component_histories)
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
