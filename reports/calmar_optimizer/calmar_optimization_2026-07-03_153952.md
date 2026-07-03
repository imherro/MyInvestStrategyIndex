# Calmar Ratio Portfolio Optimization

Generated: 2026-07-03 15:39:53
Assets: 6
Aligned price sample: 2018-09-03 to 2026-07-02 (1895 rows)
Return sample: 2018-09-04 to 2026-07-02 (1894 rows)
Train/OOS split: train 2018-09-04 to 2024-02-26 (1325 rows); OOS 2024-02-27 to 2026-07-02 (569 rows)

## Method

- Objective: maximize Calmar Ratio = CAGR / MaxDrawdown.
- Constraints: long-only, weights sum to 1, each weight between 0 and 40%.
- Optimization: reproducible random search plus capped-simplex local refinement. Full-sample seed `20260703`, train seed `20260704`.
- Evaluated candidates: full sample 168,002; train sample 168,002.

## Optimal Weights

| code | name | full_sample_opt_weight | train_70pct_opt_weight | equal_weight |
| --- | --- | --- | --- | --- |
| h21052.CSI | 国信价值全收益指数 | 0.00% | 0.00% | 16.67% |
| CN2296.CNI | 创成长R收益指数 | 11.13% | 0.00% | 16.67% |
| h20269.CSI | 红利低波全收益指数 | 0.00% | 0.00% | 16.67% |
| 480092.CNI | 自由现金流R收益指数 | 25.22% | 28.65% | 16.67% |
| 518880.SH | 518880 华安黄金ETF | 23.64% | 31.35% | 16.67% |
| 511260.SH | 511260 十年国债ETF | 40.00% | 40.00% | 16.67% |

## Metrics

| portfolio | CAGR | Volatility | MaxDrawdown | Sharpe | Calmar |
| --- | --- | --- | --- | --- | --- |
| Full optimized | 12.73% | 8.86% | 7.44% | 1.453 | 1.713 |
| Full equal weight | 13.72% | 12.95% | 12.12% | 1.099 | 1.132 |
| Train optimized | 11.54% | 7.44% | 6.76% | 1.567 | 1.708 |
| Train equal weight | 11.78% | 12.65% | 12.12% | 0.981 | 0.972 |
| OOS train-opt frozen | 13.50% | 10.33% | 15.44% | 1.325 | 0.874 |
| OOS equal weight | 18.42% | 13.64% | 9.64% | 1.355 | 1.910 |

## Output Files

- Weights CSV: `reports/calmar_optimizer/calmar_optimization_2026-07-03_153952_weights.csv`
- Equity CSV: `reports/calmar_optimizer/calmar_optimization_2026-07-03_153952_equity.csv`
- Equity plot: `reports/calmar_optimizer/calmar_optimization_2026-07-03_153952_equity.png`

## Notes

- Full-sample optimal weights are optimized on the entire aligned history and are not an out-of-sample claim.
- OOS train-opt frozen uses only the first 70% of returns to choose weights, then holds those weights fixed for the last 30%.
- Equal weight is 1/6 per asset.
