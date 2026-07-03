from __future__ import annotations

from myinvest_strategy_index.webapp import render_strategy_index_compare_page, render_value_compare_page


def test_value_compare_page_renders_strategy_index_shell() -> None:
    html = render_strategy_index_compare_page()

    assert render_value_compare_page() == html
    assert "策略指数收益曲线对比" in html
    assert "/api/strategy-index-compare/history.json" in html
    assert 'data-extra-metrics="true"' in html
    assert 'data-synthetic-code="VIRTUAL_EQUAL_WEIGHT_STRATEGY"' in html
    assert 'data-risk-parity-code="VIRTUAL_RISK_PARITY_STRATEGY"' in html
    assert 'data-anchor-synthetic="false"' in html
    assert 'data-show-background="true"' in html
    assert "国信价值全收益" in html
    assert "创成长R" in html
    assert "价值100R" not in html
    assert "自由现金流R" in html
    assert "策略等权组合" in html
    assert "风险平价组合" in html
    assert "buildRiskParityRows" in html
    assert "inverseVolatilityWeights" in html
    assert "dynamicRiskParityRows" in html
    assert "上证指数作为灰色背景线" in html
    assert "background_series" in html
    assert "backgroundNormalizedSeries" in html
    assert "background-line" in html
    assert "最长回本时间" in html
