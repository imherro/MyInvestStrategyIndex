from __future__ import annotations

from myinvest_strategy_index.config import load_settings
from myinvest_strategy_index.value_compare import (
    CASHFLOW_GROWTH_COMPARE_INSTRUMENTS,
    CHINEXT_TOTAL_RETURN_INSTRUMENTS,
    DEFAULT_VALUE_COMPARE_INSTRUMENTS,
    FOUR_ASSET_CALMAR_INSTRUMENTS,
    THREE_ASSET_CALMAR_INSTRUMENTS,
    VALUE_COMPARE_BACKGROUND,
    get_cashflow_growth_compare_payload,
    get_chinext_total_return_payload,
    get_four_asset_calmar_payload,
    get_three_asset_calmar_payload,
    get_value_compare_payload,
)


def test_value_compare_payload_reads_cached_histories_with_background(tmp_path) -> None:
    settings = load_settings(root=tmp_path, env_file=tmp_path / ".env")
    settings.cache_dir.mkdir(parents=True)
    instruments = [*DEFAULT_VALUE_COMPARE_INSTRUMENTS, VALUE_COMPARE_BACKGROUND]
    for instrument in instruments:
        safe_code = instrument.code.replace(".", "_")
        (settings.cache_dir / f"value_compare_{safe_code}.csv").write_text(
            "date,close,value\n"
            "2021-01-04,1000.000,1000.000\n"
            "2021-01-05,1050.000,1050.000\n",
            encoding="utf-8",
        )

    payload = get_value_compare_payload(settings)

    assert payload["ok"] is True
    assert not payload["errors"]
    assert len(payload["instruments"]) == len(DEFAULT_VALUE_COMPARE_INSTRUMENTS)
    assert payload["background"]["code"] == "000001.SH"
    assert "h21052.CSI" in payload["series"]
    assert "CN2296.CNI" in payload["series"]
    assert "480081.CNI" not in payload["series"]
    assert "h20269.CSI" in payload["series"]
    assert "480092.CNI" in payload["series"]
    assert "518880.SH" in payload["series"]
    assert "511260.SH" in payload["series"]
    assert "VIRTUAL_EQUAL_WEIGHT_STRATEGY" in payload["series"]
    assert "VIRTUAL_RISK_PARITY_STRATEGY" in payload["series"]
    assert "VIRTUAL_LAYERED_WEIGHT_STRATEGY" in payload["series"]
    assert payload["series"]["h21052.CSI"][0]["date"] == "2021-01-04"
    assert payload["series"]["CN2296.CNI"][1]["value"] == 1050.0
    assert payload["series"]["VIRTUAL_EQUAL_WEIGHT_STRATEGY"][1]["value"] == 1.05
    assert payload["series"]["VIRTUAL_RISK_PARITY_STRATEGY"][1]["value"] == 1.05
    assert payload["series"]["VIRTUAL_LAYERED_WEIGHT_STRATEGY"][1]["value"] == 1.05
    assert payload["background_series"][1]["value"] == 1050.0


def test_value_compare_synthetic_series_include_gold_and_bond_etfs(tmp_path) -> None:
    settings = load_settings(root=tmp_path, env_file=tmp_path / ".env")
    settings.cache_dir.mkdir(parents=True)
    for instrument in [*DEFAULT_VALUE_COMPARE_INSTRUMENTS, VALUE_COMPARE_BACKGROUND]:
        if instrument.kind.startswith("synthetic_"):
            continue
        safe_code = instrument.code.replace(".", "_")
        second_value = 1200 if instrument.code in {"518880.SH", "511260.SH"} else 1000
        (settings.cache_dir / f"value_compare_{safe_code}.csv").write_text(
            "date,close,value\n"
            "2021-01-04,1000.000,1000.000\n"
            f"2021-01-05,{second_value}.000,{second_value}.000\n",
            encoding="utf-8",
        )

    payload = get_value_compare_payload(settings)

    assert payload["ok"] is True
    assert payload["series"]["VIRTUAL_EQUAL_WEIGHT_STRATEGY"][1]["value"] == 1.066667
    assert payload["series"]["VIRTUAL_RISK_PARITY_STRATEGY"][1]["value"] == 1.066667
    assert payload["series"]["VIRTUAL_LAYERED_WEIGHT_STRATEGY"][1]["value"] == 1.127283


def test_layered_weight_model_uses_calmar_full_sample_weights(tmp_path) -> None:
    settings = load_settings(root=tmp_path, env_file=tmp_path / ".env")
    settings.cache_dir.mkdir(parents=True)
    second_values = {
        "CN2296.CNI": 1200,
        "480092.CNI": 1100,
        "h21052.CSI": 1050,
        "h20269.CSI": 900,
        "518880.SH": 1300,
        "511260.SH": 950,
    }
    for instrument in [*DEFAULT_VALUE_COMPARE_INSTRUMENTS, VALUE_COMPARE_BACKGROUND]:
        if instrument.kind.startswith("synthetic_"):
            continue
        safe_code = instrument.code.replace(".", "_")
        second_value = second_values.get(instrument.code, 1000)
        (settings.cache_dir / f"value_compare_{safe_code}.csv").write_text(
            "date,close,value\n"
            "2021-01-04,1000.000,1000.000\n"
            f"2021-01-05,{second_value}.000,{second_value}.000\n",
            encoding="utf-8",
        )

    payload = get_value_compare_payload(settings)

    assert payload["ok"] is True
    assert payload["series"]["VIRTUAL_LAYERED_WEIGHT_STRATEGY"][1]["value"] == 1.098418


def test_chinext_total_return_payload_reads_three_cached_indices(tmp_path) -> None:
    settings = load_settings(root=tmp_path, env_file=tmp_path / ".env")
    settings.cache_dir.mkdir(parents=True)
    second_values = {
        "399606.SZ": 1100,
        "CN2673.CNI": 1200,
        "CN2296.CNI": 1300,
    }
    for instrument in CHINEXT_TOTAL_RETURN_INSTRUMENTS:
        safe_code = instrument.code.replace(".", "_")
        second_value = second_values[instrument.code]
        (settings.cache_dir / f"value_compare_{safe_code}.csv").write_text(
            "date,close,value\n"
            "2021-01-04,1000.000,1000.000\n"
            f"2021-01-05,{second_value}.000,{second_value}.000\n",
            encoding="utf-8",
        )

    payload = get_chinext_total_return_payload(settings)

    assert payload["ok"] is True
    assert not payload["errors"]
    assert len(payload["instruments"]) == 3
    assert payload["background"] is None
    assert payload["background_series"] == []
    assert set(payload["series"]) == {"399606.SZ", "CN2673.CNI", "CN2296.CNI"}
    assert payload["series"]["399606.SZ"][1]["value"] == 1100.0
    assert payload["series"]["CN2673.CNI"][1]["value"] == 1200.0
    assert payload["series"]["CN2296.CNI"][1]["value"] == 1300.0


def test_cashflow_growth_payload_keeps_two_indices_and_same_virtual_features(tmp_path) -> None:
    settings = load_settings(root=tmp_path, env_file=tmp_path / ".env")
    settings.cache_dir.mkdir(parents=True)
    second_values = {
        "480092.CNI": 1200,
        "CN2296.CNI": 1100,
        "000001.SH": 1050,
    }
    for instrument in [*CASHFLOW_GROWTH_COMPARE_INSTRUMENTS, VALUE_COMPARE_BACKGROUND]:
        if instrument.kind.startswith("synthetic_"):
            continue
        safe_code = instrument.code.replace(".", "_")
        second_value = second_values[instrument.code]
        (settings.cache_dir / f"value_compare_{safe_code}.csv").write_text(
            "date,close,value\n"
            "2021-01-04,1000.000,1000.000\n"
            f"2021-01-05,{second_value}.000,{second_value}.000\n",
            encoding="utf-8",
        )

    payload = get_cashflow_growth_compare_payload(settings)

    assert payload["ok"] is True
    assert not payload["errors"]
    assert len(payload["instruments"]) == 4
    assert payload["background"]["code"] == "000001.SH"
    assert set(payload["series"]) == {
        "480092.CNI",
        "CN2296.CNI",
        "VIRTUAL_CASHFLOW_GROWTH_EQUAL_WEIGHT",
        "VIRTUAL_CASHFLOW_GROWTH_RISK_PARITY",
    }
    assert payload["series"]["480092.CNI"][1]["value"] == 1200.0
    assert payload["series"]["CN2296.CNI"][1]["value"] == 1100.0
    assert payload["series"]["VIRTUAL_CASHFLOW_GROWTH_EQUAL_WEIGHT"][1]["value"] == 1.15
    assert payload["series"]["VIRTUAL_CASHFLOW_GROWTH_RISK_PARITY"][1]["value"] == 1.15
    assert payload["background_series"][1]["value"] == 1050.0


def test_four_asset_calmar_payload_includes_equal_and_layered_models(tmp_path) -> None:
    settings = load_settings(root=tmp_path, env_file=tmp_path / ".env")
    settings.cache_dir.mkdir(parents=True)
    second_values = {
        "399606.SZ": 1100,
        "480092.CNI": 1200,
        "518880.SH": 1300,
        "511260.SH": 950,
    }
    for instrument in FOUR_ASSET_CALMAR_INSTRUMENTS:
        if instrument.kind.startswith("synthetic_"):
            continue
        safe_code = instrument.code.replace(".", "_")
        second_value = second_values[instrument.code]
        (settings.cache_dir / f"value_compare_{safe_code}.csv").write_text(
            "date,close,value\n"
            "2021-01-04,1000.000,1000.000\n"
            f"2021-01-05,{second_value}.000,{second_value}.000\n",
            encoding="utf-8",
        )

    payload = get_four_asset_calmar_payload(settings)

    assert payload["ok"] is True
    assert not payload["errors"]
    assert len(payload["instruments"]) == 6
    assert payload["background"] is None
    bond = next(item for item in payload["instruments"] if item["code"] == "511260.SH")
    assert bond["color"] == "#2563EB"
    assert set(payload["series"]) == {
        "399606.SZ",
        "480092.CNI",
        "518880.SH",
        "511260.SH",
        "VIRTUAL_FOUR_ASSET_EQUAL_WEIGHT",
        "VIRTUAL_FOUR_ASSET_CALMAR_LAYERED",
    }
    assert payload["series"]["VIRTUAL_FOUR_ASSET_EQUAL_WEIGHT"][1]["value"] == 1.1375
    assert payload["series"]["VIRTUAL_FOUR_ASSET_CALMAR_LAYERED"][1]["value"] == 1.109943


def test_three_asset_calmar_payload_includes_equal_and_layered_models(tmp_path) -> None:
    settings = load_settings(root=tmp_path, env_file=tmp_path / ".env")
    settings.cache_dir.mkdir(parents=True)
    second_values = {
        "399606.SZ": 1100,
        "480092.CNI": 1200,
        "518880.SH": 1300,
    }
    for instrument in THREE_ASSET_CALMAR_INSTRUMENTS:
        if instrument.kind.startswith("synthetic_"):
            continue
        safe_code = instrument.code.replace(".", "_")
        second_value = second_values[instrument.code]
        (settings.cache_dir / f"value_compare_{safe_code}.csv").write_text(
            "date,close,value\n"
            "2021-01-04,1000.000,1000.000\n"
            f"2021-01-05,{second_value}.000,{second_value}.000\n",
            encoding="utf-8",
        )

    payload = get_three_asset_calmar_payload(settings)

    assert payload["ok"] is True
    assert not payload["errors"]
    assert len(payload["instruments"]) == 5
    assert payload["background"] is None
    assert set(payload["series"]) == {
        "399606.SZ",
        "480092.CNI",
        "518880.SH",
        "VIRTUAL_THREE_ASSET_EQUAL_WEIGHT",
        "VIRTUAL_THREE_ASSET_CALMAR_LAYERED",
    }
    assert payload["series"]["VIRTUAL_THREE_ASSET_EQUAL_WEIGHT"][1]["value"] == 1.2
    assert payload["series"]["VIRTUAL_THREE_ASSET_CALMAR_LAYERED"][1]["value"] == 1.218319
