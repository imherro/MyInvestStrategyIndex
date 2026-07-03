# MyInvestStrategyIndex

独立的策略入口页和策略指数对比页，迁移自 `C:\Users\kunpeng\Documents\MyShortTerm` 的 `/value-compare`。

## 页面

- `http://127.0.0.1:8023/`
- `http://127.0.0.1:8023/value-compare`
- `http://127.0.0.1:8023/strategy-index-compare`
- `http://127.0.0.1:8023/chinext-compare`
- `http://127.0.0.1:8023/four-asset-compare`

首页是策略卡片入口，`/value-compare`、`/chinext-compare` 和 `/four-asset-compare` 各是一张卡片。`/value-compare` 和 `/strategy-index-compare` 打开同一页：页面对比国信价值全收益、创成长R、红利低波全收益、自由现金流R、518880 华安黄金ETF、511260 十年国债ETF，并提供策略等权组合、滚动60日风险平价组合和分层权重模型；分层模型使用 Calmar 全样本最优权重：国信价值0%、创成长R11.13%、红利低波0%、自由现金流R25.22%、黄金ETF23.64%、十年国债ETF40.00%，但 70/30 样本外验证弱于等权组合，仅作参考；默认所有有数据项目全部勾选；上证指数作为灰色背景线，不参与指标排序。

`/chinext-compare` 对比创业板三个指数的全收益版本：399006 创业板指使用 399606.SZ 创业板R，399673 创业板50使用 CN2673.CNI 创业板50R，399296 创成长使用 CN2296.CNI 创成长R。

`/four-asset-compare` 对比创业板R、自由现金流R、518880 华安黄金ETF、511260 十年国债ETF，并提供四资产等权组合和 Calmar 全样本最优分层权重模型。分层权重为创业板R15.80%、自由现金流R18.45%、黄金ETF25.74%、十年国债ETF40.00%；2017-08-24 至 2026-07-02 全样本区间年化收益10.43%、最大回撤8.05%、Calmar 1.296。

## 运行

先在 `.env` 配置：

```text
TUSHARE_TOKEN=...
```

启动：

```powershell
python -m myinvest_strategy_index.webapp --port 8023
```

默认端口是 `8023`，默认绑定 `0.0.0.0`，局域网可通过本机 IP 访问。

## Calmar 优化

使用本地 `data/cache/value_compare_*.csv` 历史价格缓存，生成 6 资产 Calmar Ratio 优化报告：

```powershell
python -m myinvest_strategy_index.calmar_optimizer --seed 20260703
```

输出会写入 `reports/calmar_optimizer/`，包含 Markdown 报告、权重 CSV、净值曲线 CSV 和净值曲线 PNG。
