# MyInvestStrategyIndex

独立的策略指数对比页，迁移自 `C:\Users\kunpeng\Documents\MyShortTerm` 的 `/value-compare`。

## 页面

- `http://127.0.0.1:8023/value-compare`
- `http://127.0.0.1:8023/strategy-index-compare`

这两个地址打开同一页。页面对比国信价值全收益、创成长R、红利低波全收益、自由现金流R、518880 华安黄金ETF、511260 十年国债ETF，并提供策略等权组合和滚动60日风险平价组合；黄金和国债ETF会参与虚拟组合计算；上证指数作为灰色背景线，不参与指标排序。

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
