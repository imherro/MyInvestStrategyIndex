from __future__ import annotations

from myinvest_strategy_index.webapp import (
    render_chinext_compare_page,
    render_four_asset_compare_page,
    render_home_page,
    render_strategy_index_compare_page,
    render_value_compare_page,
)


def test_home_page_renders_strategy_card_entry() -> None:
    html = render_home_page()

    assert "策略入口 - MyInvestStrategyIndex" in html
    assert "策略卡片" in html
    assert 'href="/value-compare"' in html
    assert 'href="/chinext-compare"' in html
    assert 'href="/four-asset-compare"' in html
    assert "策略指数收益曲线对比" in html
    assert "value-compare" in html
    assert "创业板全收益指数对比" in html
    assert "chinext-compare" in html
    assert "四资产组合对比" in html
    assert "four-asset" in html
    assert "/api/strategy-index-compare/history.json" not in html
    assert "/api/chinext-compare/history.json" not in html
    assert "/api/four-asset-compare/history.json" not in html


def test_value_compare_page_renders_strategy_index_shell() -> None:
    html = render_strategy_index_compare_page()

    assert render_value_compare_page() == html
    assert "策略指数收益曲线对比" in html
    assert "/api/strategy-index-compare/history.json" in html
    assert 'data-extra-metrics="true"' in html
    assert 'data-synthetic-code="VIRTUAL_EQUAL_WEIGHT_STRATEGY"' in html
    assert 'data-risk-parity-code="VIRTUAL_RISK_PARITY_STRATEGY"' in html
    assert "data-default-unselected-codes" not in html
    assert 'data-anchor-synthetic="false"' in html
    assert 'data-show-background="true"' in html
    assert 'href="/"' in html
    assert "国信价值全收益" in html
    assert "创成长R" in html
    assert "价值100R" not in html
    assert "自由现金流R" in html
    assert "华安黄金ETF" in html
    assert "十年国债ETF" in html
    assert "分层权重模型" in html
    assert "Calmar 优化结论" in html
    assert "国信价值0%、创成长R11.13%、红利低波0%、自由现金流R25.22%、黄金ETF23.64%、十年国债ETF40.00%" in html
    assert "最优分层权重模型年化表现" in html
    assert "年化收益 12.73%，年化波动 8.86%，最大回撤 7.44%，Sharpe 1.453，Calmar 1.713" in html
    assert "样本内有效、样本外不稳健" in html
    assert "样本外 Calmar 0.874" in html
    assert "70/30 样本外验证" in html
    assert 'instrument.kind === "index"' not in html
    assert "isDynamicSyntheticCode" in html
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


def test_chinext_compare_page_renders_three_total_return_indices() -> None:
    html = render_chinext_compare_page()

    assert "创业板全收益指数对比" in html
    assert "/api/chinext-compare/history.json" in html
    assert 'data-extra-metrics="true"' in html
    assert 'data-anchor-synthetic="false"' in html
    assert 'data-show-background="false"' in html
    assert 'href="/"' in html
    assert 'href="/value-compare"' in html
    assert "399006 创业板指" in html
    assert "399673 创业板50" in html
    assert "399296 创成长" in html
    assert "399606.SZ、CN2673.CNI、CN2296.CNI" in html
    assert "Calmar 优化结论" not in html
    assert "样本内有效、样本外不稳健" not in html
    assert "最长回本时间" in html


def test_four_asset_compare_page_renders_calmar_layered_model() -> None:
    html = render_four_asset_compare_page()

    assert "四资产组合对比" in html
    assert "/api/four-asset-compare/history.json" in html
    assert 'data-extra-metrics="true"' in html
    assert 'data-synthetic-code="VIRTUAL_FOUR_ASSET_EQUAL_WEIGHT"' in html
    assert 'data-anchor-synthetic="false"' in html
    assert 'data-show-background="false"' in html
    assert 'href="/"' in html
    assert 'href="/value-compare"' in html
    assert "四资产 Calmar 优化结论" in html
    assert "创业板R15.80%、自由现金流R18.45%、黄金ETF25.74%、十年国债ETF40.00%" in html
    assert "年化收益 10.43%，年化波动 8.54%，最大回撤 8.05%，Sharpe 1.251，Calmar 1.296" in html
    assert "等权组合年化收益 11.93%" in html
    assert "四资产等权组合" in html
    assert "分层权重模型" in html
    assert "最长回本时间" in html
