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
    ("CN2296.CNI", 0.18),
    ("480092.CNI", 0.22),
    ("h21052.CSI", 0.15),
    ("h20269.CSI", 0.20),
    ("518880.SH", 0.15),
    ("511260.SH", 0.10),
)
LAYERED_CASH_WEIGHT = 0.0


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
        name="分层权重模型",
        kind="synthetic_layered_weight",
        source=(
            "固定比例：创成长R18%+自由现金流R22%+国信价值15%+红利低波20%+"
            "黄金ETF15%+十年国债ETF10%；满足约束：红利+现金流42%、创成长18%、黄金15%"
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


def get_value_compare_payload(settings: Settings, *, refresh: bool = False) -> dict[str, object]:
    ensure_runtime_dirs(settings)
    instruments = [asdict(item) for item in DEFAULT_VALUE_COMPARE_INSTRUMENTS]
    series: dict[str, list[dict[str, object]]] = {}
    histories: dict[str, pd.DataFrame] = {}
    errors: list[dict[str, str]] = []
    updated_at = datetime.now().isoformat(timespec="seconds")

    for instrument in DEFAULT_VALUE_COMPARE_INSTRUMENTS:
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
        for item in DEFAULT_VALUE_COMPARE_INSTRUMENTS
        if not item.kind.startswith("synthetic_") and item.code in histories
    ]
    for instrument in DEFAULT_VALUE_COMPARE_INSTRUMENTS:
        if not instrument.kind.startswith("synthetic_"):
            continue
        try:
            if instrument.kind == "synthetic_risk_parity":
                history = _build_risk_parity_history(component_histories)
            elif instrument.kind == "synthetic_layered_weight":
                history = _build_layered_weight_history(histories)
            else:
                history = _build_equal_weight_history(component_histories)
            series[instrument.code] = _history_records(history)
        except Exception as exc:
            errors.append({"code": instrument.code, "name": instrument.name, "error": str(exc)})

    background_series: list[dict[str, object]] = []
    try:
        background = load_or_fetch_value_history(settings, VALUE_COMPARE_BACKGROUND, refresh=refresh)
        background_series = _history_records(background)
    except Exception as exc:
        errors.append({"code": VALUE_COMPARE_BACKGROUND.code, "name": VALUE_COMPARE_BACKGROUND.name, "error": str(exc)})

    return {
        "ok": not errors or bool(series),
        "updated_at": updated_at,
        "refresh": refresh,
        "instruments": instruments,
        "series": series,
        "background": asdict(VALUE_COMPARE_BACKGROUND),
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


def _build_layered_weight_history(histories: dict[str, pd.DataFrame]) -> pd.DataFrame:
    missing = [code for code, _ in LAYERED_WEIGHT_COMPONENTS if code not in histories]
    if missing:
        raise RuntimeError(f"Missing layered model components: {', '.join(missing)}")

    total_weight = LAYERED_CASH_WEIGHT + sum(weight for _, weight in LAYERED_WEIGHT_COMPONENTS)
    if not math.isclose(total_weight, 1.0, abs_tol=1e-9):
        raise RuntimeError(f"Layered model weights must sum to 1.0, got {total_weight:.6f}")

    values: dict[str, pd.Series] = {}
    starts: list[pd.Timestamp] = []
    ends: list[pd.Timestamp] = []
    for code, _ in LAYERED_WEIGHT_COMPONENTS:
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
            for code, weight in LAYERED_WEIGHT_COMPONENTS:
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
