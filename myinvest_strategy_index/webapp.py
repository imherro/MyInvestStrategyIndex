from __future__ import annotations

import argparse
import json
import math
from collections.abc import Callable
from datetime import datetime
from html import escape
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from myinvest_strategy_index.config import Settings, load_settings
from myinvest_strategy_index.cycle_backtests import get_cycle_backtest_detail, get_cycle_backtest_index
from myinvest_strategy_index.value_compare import (
    get_chinext_total_return_payload,
    get_four_asset_calmar_payload,
    get_three_asset_calmar_payload,
    get_value_compare_payload,
)


__version__ = "0.1.0"
MYINVEST_HEADER_SCRIPT = "https://invest.okbbc.com/header.js"
MYINVEST_FOOTER_SCRIPT = "https://invest.okbbc.com/footer.js"


def _myinvest_header_html() -> str:
    return (
        '<div data-myinvest-header></div>\n'
        f'<script defer src="{MYINVEST_HEADER_SCRIPT}" data-target="[data-myinvest-header]"></script>'
    )


def _myinvest_footer_html() -> str:
    return (
        '<div data-myinvest-footer></div>\n'
        f'<script defer src="{MYINVEST_FOOTER_SCRIPT}" data-target="[data-myinvest-footer]"></script>'
    )


def _inject_unified_shell(page: str) -> str:
    return page.replace("__MYINVEST_HEADER__", _myinvest_header_html()).replace(
        "__MYINVEST_FOOTER__", _myinvest_footer_html()
    )


class StrategyIndexHandler(BaseHTTPRequestHandler):
    settings: Settings

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send_html(render_home_page())
            return
        if parsed.path in {"/value-compare", "/strategy-index-compare"}:
            self._send_html(render_value_compare_page())
            return
        if parsed.path in {"/chinext-compare", "/chinext-total-return"}:
            self._send_html(render_chinext_compare_page())
            return
        if parsed.path in {"/four-asset-compare", "/four-asset-calmar"}:
            self._send_html(render_four_asset_compare_page())
            return
        if parsed.path in {"/three-asset-compare", "/three-asset-calmar"}:
            self._send_html(render_three_asset_compare_page())
            return
        if parsed.path == "/strategy-backtests":
            self._send_html(render_strategy_backtests_page(self.settings))
            return
        if parsed.path.startswith("/strategy-backtests/"):
            strategy_id = parsed.path.removeprefix("/strategy-backtests/").strip("/")
            self._send_cycle_backtest_page(strategy_id)
            return
        if parsed.path in {"/api/value-compare/history.json", "/api/strategy-index-compare/history.json"}:
            self._send_history(parsed.query, get_value_compare_payload)
            return
        if parsed.path in {"/api/chinext-compare/history.json", "/api/chinext-total-return/history.json"}:
            self._send_history(parsed.query, get_chinext_total_return_payload)
            return
        if parsed.path in {"/api/four-asset-compare/history.json", "/api/four-asset-calmar/history.json"}:
            self._send_history(parsed.query, get_four_asset_calmar_payload)
            return
        if parsed.path in {"/api/three-asset-compare/history.json", "/api/three-asset-calmar/history.json"}:
            self._send_history(parsed.query, get_three_asset_calmar_payload)
            return
        if parsed.path == "/api/strategy-backtests/index.json":
            self._send_json(get_cycle_backtest_index(self.settings))
            return
        if parsed.path.startswith("/api/strategy-backtests/") and parsed.path.endswith(".json"):
            strategy_id = parsed.path.removeprefix("/api/strategy-backtests/").removesuffix(".json").strip("/")
            self._send_cycle_backtest_json(strategy_id)
            return
        if parsed.path == "/health.json":
            self._send_json({"ok": True, "version": __version__, "time": datetime.now().isoformat(timespec="seconds")})
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send_html(self, body: str, status: HTTPStatus = HTTPStatus.OK) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send_history(self, raw_query: str, payload_loader: Callable[..., dict[str, object]]) -> None:
        query = parse_qs(raw_query)
        refresh = (query.get("refresh", ["0"])[0] or "").lower() in {"1", "true", "yes", "y"}
        try:
            payload = payload_loader(self.settings, refresh=refresh)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        self._send_json(payload)

    def _send_cycle_backtest_json(self, strategy_id: str) -> None:
        try:
            payload = get_cycle_backtest_detail(self.settings, strategy_id)
        except Exception as exc:
            self._send_json({"ok": False, "error": str(exc)}, status=HTTPStatus.NOT_FOUND)
            return
        self._send_json(payload)

    def _send_cycle_backtest_page(self, strategy_id: str) -> None:
        try:
            page = render_strategy_backtest_detail_page(self.settings, strategy_id)
        except Exception as exc:
            self._send_html(render_not_found_page(str(exc)), status=HTTPStatus.NOT_FOUND)
            return
        self._send_html(page)


def run(host: str = "0.0.0.0", port: int = 8023) -> None:
    settings = load_settings()
    StrategyIndexHandler.settings = settings
    server = ThreadingHTTPServer((host, port), StrategyIndexHandler)
    print(
        json.dumps(
            {
                "url": f"http://{host}:{port}/",
                "value_compare_url": f"http://{host}:{port}/value-compare",
                "chinext_compare_url": f"http://{host}:{port}/chinext-compare",
                "four_asset_compare_url": f"http://{host}:{port}/four-asset-compare",
                "three_asset_compare_url": f"http://{host}:{port}/three-asset-compare",
                "strategy_backtests_url": f"http://{host}:{port}/strategy-backtests",
                "cache_dir": str(settings.cache_dir),
                "tushare_token": bool(settings.tushare_token),
            },
            ensure_ascii=False,
        )
    )
    server.serve_forever()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the MyInvest strategy index comparison page")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8023)
    args = parser.parse_args(argv)
    run(host=args.host, port=args.port)
    return 0


def render_home_page() -> str:
    page = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>策略入口 - MyInvestStrategyIndex</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1c2430;
      --muted: #687385;
      --line: #d9dee7;
      --accent: #0f766e;
      --soft: #edf7f5;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      letter-spacing: 0;
    }
    a { color: inherit; text-decoration: none; }
    a:hover { text-decoration: none; }
    .page-header {
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.97);
    }
    .bar {
      max-width: 1440px;
      margin: 0 auto;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
    }
    .meta {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #fff;
      white-space: nowrap;
    }
    main {
      max-width: 1440px;
      margin: 0 auto;
      padding: 20px 20px 32px;
      display: grid;
      gap: 16px;
      align-items: start;
    }
    .section-title {
      margin: 0;
      font-size: 15px;
      font-weight: 700;
      color: var(--muted);
    }
    .strategy-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
    }
    .strategy-card {
      min-height: 172px;
      display: grid;
      gap: 12px;
      align-content: space-between;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      transition: border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
    }
    .strategy-card:hover {
      border-color: #93c5bd;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
      transform: translateY(-1px);
    }
    .card-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }
    .card-title {
      margin: 0;
      font-size: 18px;
      line-height: 1.3;
      font-weight: 750;
    }
    .card-tag {
      flex: 0 0 auto;
      border: 1px solid #b7ddd6;
      border-radius: 999px;
      padding: 3px 8px;
      color: var(--accent);
      background: var(--soft);
      font-size: 12px;
      font-weight: 650;
      white-space: nowrap;
    }
    .card-desc {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }
    .card-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      color: var(--muted);
      font-size: 12px;
    }
    .card-action {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      color: var(--accent);
      font-weight: 700;
    }
    @media (max-width: 720px) {
      .bar { align-items: flex-start; flex-direction: column; }
      .meta { justify-content: flex-start; }
      .strategy-grid { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  __MYINVEST_HEADER__
  <div class="page-header">
    <div class="bar">
      <h1>策略入口</h1>
      <div class="meta">
        <span class="pill">MyInvestStrategyIndex</span>
        <span class="pill">端口 8023</span>
      </div>
    </div>
  </div>
  <main>
    <h2 class="section-title">策略研究</h2>
    <div class="strategy-grid">
      <a class="strategy-card" href="/value-compare" aria-label="打开策略指数收益曲线对比">
        <div class="card-head">
          <h3 class="card-title">策略指数收益曲线对比</h3>
          <span class="card-tag">value-compare</span>
        </div>
        <p class="card-desc">
          对比国信价值、创成长R、红利低波、自由现金流R、黄金ETF、十年国债ETF，并展示等权、风险平价和 Calmar 分层权重模型。
        </p>
        <div class="card-footer">
          <span>收益曲线 / 回撤 / 指标排序</span>
          <span class="card-action">打开 →</span>
        </div>
      </a>
      <a class="strategy-card" href="/chinext-compare" aria-label="打开创业板全收益指数对比">
        <div class="card-head">
          <h3 class="card-title">创业板全收益指数对比</h3>
          <span class="card-tag">chinext-compare</span>
        </div>
        <p class="card-desc">
          对比 399006 创业板指、399673 创业板50、399296 创成长三个指数的全收益版本，保留收益曲线、回撤和指标排序。
        </p>
        <div class="card-footer">
          <span>三个全收益指数 / 同屏比较</span>
          <span class="card-action">打开 →</span>
        </div>
      </a>
      <a class="strategy-card" href="/four-asset-compare" aria-label="打开四资产组合对比">
        <div class="card-head">
          <h3 class="card-title">四资产组合对比</h3>
          <span class="card-tag">four-asset</span>
        </div>
        <p class="card-desc">
          对比创业板R、自由现金流R、黄金ETF、十年国债ETF，并加入等权组合和 Calmar 全样本最优分层权重模型。
        </p>
        <div class="card-footer">
          <span>真实标的 / 等权 / 最优分层</span>
          <span class="card-action">打开 →</span>
        </div>
      </a>
      <a class="strategy-card" href="/three-asset-compare" aria-label="打开三资产组合对比">
        <div class="card-head">
          <h3 class="card-title">三资产组合对比</h3>
          <span class="card-tag">three-asset</span>
        </div>
        <p class="card-desc">
          对比创业板R、自由现金流R、黄金ETF，并加入等权组合和 Calmar 全样本最优分层权重模型。
        </p>
        <div class="card-footer">
          <span>三类资产 / 等权 / 最优分层</span>
          <span class="card-action">打开 →</span>
        </div>
      </a>
    </div>
    <h2 class="section-title">策略回测</h2>
    <div class="strategy-grid">
      <a class="strategy-card" href="/strategy-backtests" aria-label="打开策略回测集合">
        <div class="card-head">
          <h3 class="card-title">Cycle 策略回测集合</h3>
          <span class="card-tag">strategy-backtests</span>
        </div>
        <p class="card-desc">
          汇总同级 MyInvestCycle 子系统的资产配置、ETF轮动、自由现金流和回归/回撤类策略回测结果，保留净值曲线、指标、最新权重和信号。
        </p>
        <div class="card-footer">
          <span>回测结果 / 策略分类 / 详情页</span>
          <span class="card-action">打开 →</span>
        </div>
      </a>
    </div>
  </main>
  __MYINVEST_FOOTER__
</body>
</html>"""
    return _inject_unified_shell(page)


def render_strategy_backtests_page(settings: Settings, *, backtest_dir: Path | None = None) -> str:
    payload = get_cycle_backtest_index(settings, backtest_dir=backtest_dir)
    strategies = [item for item in payload.get("strategies", []) if isinstance(item, dict)]
    grouped: dict[str, list[dict[str, object]]] = {}
    for item in strategies:
        grouped.setdefault(str(item.get("category") or "其他策略"), []).append(item)
    group_html = "\n".join(
        _cycle_strategy_group_html(category, grouped[category])
        for category in sorted(grouped)
    )
    errors = [item for item in payload.get("errors", []) if isinstance(item, dict)]
    error_html = ""
    if errors:
        rows = "\n".join(
            f"<li>{_h(item.get('file', '-'))}: {_h(item.get('error', '-'))}</li>"
            for item in errors
        )
        error_html = f"""
    <section class="notice">
      <h2>读取异常</h2>
      <ul>{rows}</ul>
    </section>"""
    if not group_html:
        group_html = '<section class="empty">没有找到 MyInvestCycle 策略回测结果。</section>'
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>策略回测 - MyInvestStrategyIndex</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1c2430;
      --muted: #687385;
      --line: #d9dee7;
      --accent: #0f766e;
      --soft: #edf7f5;
      --bad: #b42318;
      --good: #157347;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      letter-spacing: 0;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page-header {{
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.97);
    }}
    .bar {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
    .meta {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #fff;
      white-space: nowrap;
    }}
    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 20px 20px 34px;
      display: grid;
      gap: 18px;
    }}
    .intro {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      display: grid;
      gap: 8px;
    }}
    .intro h2, .notice h2 {{
      margin: 0;
      font-size: 17px;
    }}
    .intro p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.6;
    }}
    .category {{
      display: grid;
      gap: 10px;
    }}
    .category h2 {{
      margin: 0;
      font-size: 16px;
    }}
    .strategy-list {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 12px;
    }}
    .backtest-card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px;
      display: grid;
      gap: 11px;
      min-height: 188px;
    }}
    .backtest-card:hover {{
      border-color: #93c5bd;
      box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
    }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
    }}
    .card-title {{
      margin: 0;
      font-size: 17px;
      line-height: 1.35;
    }}
    .card-id {{
      color: var(--muted);
      font-size: 12px;
      word-break: break-all;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 8px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 8px;
      background: #fbfcfd;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      margin-bottom: 4px;
    }}
    .metric strong {{
      font-size: 14px;
    }}
    .card-desc {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.55;
    }}
    .card-foot {{
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 12px;
      flex-wrap: wrap;
    }}
    .notice, .empty {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      color: var(--muted);
    }}
    .notice ul {{ margin: 8px 0 0; padding-left: 20px; }}
    @media (max-width: 760px) {{
      .bar {{ align-items: flex-start; flex-direction: column; }}
      .meta {{ justify-content: flex-start; }}
      .metrics {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      .strategy-list {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  __MYINVEST_HEADER__
  <div class="page-header">
    <div class="bar">
      <h1>策略回测</h1>
      <div class="meta">
        <a class="pill" href="/">首页</a>
        <span class="pill">MyInvestCycle 结果读取</span>
        <span class="pill">{_h(payload.get("count", 0))} 个策略</span>
      </div>
    </div>
  </div>
  <main>
    <section class="intro">
      <h2>Cycle 子系统回测集合</h2>
      <p>这里读取同级 MyInvestCycle 的已生成回测 JSON，按策略类别展示；本页只做结果汇总和详情查看，不改变 Cycle 原有回测引擎。</p>
      <p>数据源：MyInvestCycle / data / strategy_backtests。API：<a href="/api/strategy-backtests/index.json">/api/strategy-backtests/index.json</a></p>
    </section>
    {error_html}
    {group_html}
  </main>
  __MYINVEST_FOOTER__
</body>
</html>"""
    return _inject_unified_shell(page)


def render_strategy_backtest_detail_page(
    settings: Settings,
    strategy_id: str,
    *,
    backtest_dir: Path | None = None,
) -> str:
    payload = get_cycle_backtest_detail(settings, strategy_id, backtest_dir=backtest_dir)
    summary = payload["summary"] if isinstance(payload.get("summary"), dict) else {}
    metadata = payload["metadata"] if isinstance(payload.get("metadata"), dict) else {}
    validation = payload["validation"] if isinstance(payload.get("validation"), dict) else {}
    equity_curve = payload["equity_curve"] if isinstance(payload.get("equity_curve"), list) else []
    signals = payload["signals"] if isinstance(payload.get("signals"), list) else []
    comparison_assets = payload["comparison_assets"] if isinstance(payload.get("comparison_assets"), list) else []
    strategy_name = str(summary.get("strategy_name") or strategy_id)
    method_items = metadata.get("method") if isinstance(metadata.get("method"), list) else []
    method_html = ""
    if method_items:
        method_html = "<ul>" + "".join(f"<li>{_h(item)}</li>" for item in method_items) + "</ul>"
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_h(strategy_name)} - 策略回测</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1c2430;
      --muted: #687385;
      --line: #d9dee7;
      --accent: #0f766e;
      --soft: #edf7f5;
      --bad: #b42318;
      --good: #157347;
      --blue: #2563eb;
      --gray: #64748b;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      letter-spacing: 0;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page-header {{
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.97);
    }}
    .bar {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
    .meta {{
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .pill {{
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #fff;
      white-space: nowrap;
    }}
    main {{
      max-width: 1440px;
      margin: 0 auto;
      padding: 20px 20px 34px;
      display: grid;
      gap: 18px;
    }}
    .summary {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      display: grid;
      gap: 12px;
    }}
    .summary h2, .section h2 {{
      margin: 0;
      font-size: 17px;
    }}
    .summary p {{
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.65;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 10px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfcfd;
      padding: 10px;
    }}
    .metric span {{
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 5px;
    }}
    .metric strong {{
      font-size: 17px;
    }}
    .section {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 16px;
      display: grid;
      gap: 12px;
    }}
    .chart-wrap {{
      width: 100%;
      min-height: 340px;
    }}
    .chart {{
      width: 100%;
      height: auto;
      display: block;
      background: #ffffff;
      border: 1px solid var(--line);
      border-radius: 8px;
    }}
    .legend {{
      display: flex;
      gap: 14px;
      flex-wrap: wrap;
      color: var(--muted);
      font-size: 12px;
    }}
    .legend span {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }}
    .swatch {{
      width: 18px;
      height: 3px;
      border-radius: 999px;
      display: inline-block;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 9px 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      color: var(--muted);
      font-weight: 700;
      background: #fbfcfd;
    }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .grid-2 {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 18px;
    }}
    .empty {{
      color: var(--muted);
      font-size: 13px;
    }}
    ul {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.65;
    }}
    @media (max-width: 980px) {{
      .metric-grid {{ grid-template-columns: repeat(3, minmax(0, 1fr)); }}
      .grid-2 {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 680px) {{
      .bar {{ align-items: flex-start; flex-direction: column; }}
      .meta {{ justify-content: flex-start; }}
      .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
      th, td {{ padding: 8px 6px; }}
    }}
  </style>
</head>
<body>
  __MYINVEST_HEADER__
  <div class="page-header">
    <div class="bar">
      <h1>{_h(strategy_name)}</h1>
      <div class="meta">
        <a class="pill" href="/">首页</a>
        <a class="pill" href="/strategy-backtests">策略回测</a>
        <a class="pill" href="/api/strategy-backtests/{_h(summary.get('strategy_id') or strategy_id)}.json">JSON</a>
      </div>
    </div>
  </div>
  <main>
    <section class="summary">
      <h2>回测摘要</h2>
      <p>{_h(metadata.get("description") or "该策略来自 MyInvestCycle 子系统的已生成回测结果。")}</p>
      <div class="metric-grid">
        {_metric_card("年化收益", _pct(summary.get("annualized_return")))}
        {_metric_card("累计收益", _pct(summary.get("total_return")))}
        {_metric_card("最大回撤", _pct(summary.get("max_drawdown")))}
        {_metric_card("Sharpe", _number(summary.get("sharpe"), digits=3))}
        {_metric_card("Calmar", _number(summary.get("calmar"), digits=3))}
        {_metric_card("调仓次数", _number(summary.get("rebalance_count"), digits=0))}
      </div>
      <p>区间：{_date(summary.get("start_date"))} 至 {_date(summary.get("end_date"))}；交易日：{_h(summary.get("sessions", "-"))}；最新信号：{_h(summary.get("latest_signal") or "-")}（{_date(summary.get("latest_signal_date"))}）。</p>
    </section>
    <section class="section">
      <h2>净值曲线</h2>
      <div class="legend">
        <span><i class="swatch" style="background: var(--accent);"></i>策略净值</span>
        <span><i class="swatch" style="background: var(--gray);"></i>等权参考</span>
      </div>
      <div class="chart-wrap">{_render_cycle_equity_svg(equity_curve)}</div>
    </section>
    <div class="grid-2">
      <section class="section">
        <h2>最新权重</h2>
        {_weights_table(summary.get("latest_weights"))}
      </section>
      <section class="section">
        <h2>对比资产</h2>
        {_comparison_assets_table(comparison_assets)}
      </section>
    </div>
    <div class="grid-2">
      <section class="section">
        <h2>最近信号</h2>
        {_signals_table(signals)}
      </section>
      <section class="section">
        <h2>验证与方法</h2>
        {_validation_table(validation)}
        {method_html}
      </section>
    </div>
  </main>
  __MYINVEST_FOOTER__
</body>
</html>"""
    return _inject_unified_shell(page)


def render_not_found_page(message: str) -> str:
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>未找到 - MyInvestStrategyIndex</title>
  <style>
    body {{
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: #f6f7f9;
      color: #1c2430;
    }}
    main {{
      max-width: 880px;
      margin: 0 auto;
      padding: 40px 20px;
      display: grid;
      gap: 14px;
    }}
    a {{ color: #0f766e; text-decoration: none; }}
  </style>
</head>
<body>
  __MYINVEST_HEADER__
  <main>
    <h1>未找到策略回测结果</h1>
    <p>{_h(message)}</p>
    <p><a href="/strategy-backtests">返回策略回测列表</a></p>
  </main>
  __MYINVEST_FOOTER__
</body>
</html>"""
    return _inject_unified_shell(page)


def _cycle_strategy_group_html(category: str, items: list[dict[str, object]]) -> str:
    cards = "\n".join(_cycle_strategy_card_html(item) for item in items)
    return f"""
    <section class="category">
      <h2>{_h(category)}（{len(items)}）</h2>
      <div class="strategy-list">
        {cards}
      </div>
    </section>"""


def _cycle_strategy_card_html(item: dict[str, object]) -> str:
    strategy_id = str(item.get("strategy_id") or "")
    description = str(item.get("description") or "")
    if len(description) > 86:
        description = description[:86] + "..."
    description = description or "查看该策略的净值曲线、核心指标、最新权重和回测信号。"
    date_range = f"{_date(item.get('start_date'))} 至 {_date(item.get('end_date'))}"
    return f"""
        <a class="backtest-card" href="/strategy-backtests/{_h(strategy_id)}">
          <div class="card-head">
            <div>
              <h3 class="card-title">{_h(item.get("strategy_name") or strategy_id)}</h3>
              <div class="card-id">{_h(strategy_id)}</div>
            </div>
            <span class="pill">{_h(item.get("category") or "-")}</span>
          </div>
          <p class="card-desc">{_h(description)}</p>
          <div class="metrics">
            {_metric_card("年化", _pct(item.get("annualized_return")))}
            {_metric_card("回撤", _pct(item.get("max_drawdown")))}
            {_metric_card("Sharpe", _number(item.get("sharpe"), digits=2))}
            {_metric_card("Calmar", _number(item.get("calmar"), digits=2))}
          </div>
          <div class="card-foot">
            <span>{_h(date_range)}</span>
            <span>调仓 {_number(item.get("rebalance_count"), digits=0)}</span>
          </div>
        </a>"""


def _metric_card(label: str, value: str) -> str:
    return f'<div class="metric"><span>{_h(label)}</span><strong>{_h(value)}</strong></div>'


def _weights_table(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return '<div class="empty">无权重数据。</div>'
    rows = []
    for code, weight in sorted(value.items(), key=lambda item: _as_float(item[1]) or 0.0, reverse=True):
        rows.append(f"<tr><td>{_h(code)}</td><td class=\"num\">{_pct(weight)}</td></tr>")
    return f"<table><thead><tr><th>标的</th><th class=\"num\">权重</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _comparison_assets_table(items: object) -> str:
    if not isinstance(items, list) or not items:
        return '<div class="empty">无对比资产数据。</div>'
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name") or item.get("code") or item.get("asset") or "-"
        rows.append(
            "<tr>"
            f"<td>{_h(name)}</td>"
            f"<td class=\"num\">{_pct(item.get('annualized_return'))}</td>"
            f"<td class=\"num\">{_pct(item.get('max_drawdown'))}</td>"
            f"<td class=\"num\">{_number(item.get('sharpe'), digits=2)}</td>"
            f"<td class=\"num\">{_number(item.get('calmar'), digits=2)}</td>"
            "</tr>"
        )
    if not rows:
        return '<div class="empty">无对比资产数据。</div>'
    return (
        "<table><thead><tr><th>资产</th><th class=\"num\">年化</th><th class=\"num\">最大回撤</th>"
        "<th class=\"num\">Sharpe</th><th class=\"num\">Calmar</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _signals_table(items: object) -> str:
    if not isinstance(items, list) or not items:
        return '<div class="empty">无信号数据。</div>'
    rows = []
    for item in items[-10:][::-1]:
        if not isinstance(item, dict):
            continue
        date = item.get("date") or item.get("trade_date") or item.get("signal_date") or "-"
        signal = item.get("signal") or item.get("action") or item.get("selected_asset") or item.get("regime") or "-"
        weights = item.get("target_weights") or item.get("weights") or {}
        rows.append(
            "<tr>"
            f"<td>{_date(date)}</td>"
            f"<td>{_h(signal)}</td>"
            f"<td>{_h(_weights_inline(weights))}</td>"
            "</tr>"
        )
    if not rows:
        return '<div class="empty">无信号数据。</div>'
    return "<table><thead><tr><th>日期</th><th>信号</th><th>目标权重</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def _validation_table(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return '<div class="empty">无验证数据。</div>'
    rows = []
    for key, raw in value.items():
        display = "是" if raw is True else "否" if raw is False else str(raw)
        rows.append(f"<tr><td>{_h(key)}</td><td>{_h(display)}</td></tr>")
    return f"<table><thead><tr><th>项目</th><th>结果</th></tr></thead><tbody>{''.join(rows)}</tbody></table>"


def _render_cycle_equity_svg(records: object) -> str:
    if not isinstance(records, list) or len(records) < 2:
        return '<div class="empty">无净值曲线数据。</div>'
    clean_records = [item for item in records if isinstance(item, dict)]
    if len(clean_records) < 2:
        return '<div class="empty">无净值曲线数据。</div>'
    max_points = 900
    step = max(1, math.ceil(len(clean_records) / max_points))
    sampled = clean_records[::step]
    if sampled[-1] is not clean_records[-1]:
        sampled.append(clean_records[-1])
    series = [
        ("strategy_equity", "策略净值", "#0f766e"),
        ("equal_weight_equity", "等权参考", "#64748b"),
    ]
    values: list[float] = []
    for record in sampled:
        for key, _, _ in series:
            value = _as_float(record.get(key))
            if value is not None:
                values.append(value)
    if not values:
        return '<div class="empty">无净值曲线数据。</div>'
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        min_value -= 0.05
        max_value += 0.05
    width = 980
    height = 340
    left = 58
    right = 18
    top = 24
    bottom = 42
    plot_w = width - left - right
    plot_h = height - top - bottom

    def x_at(index: int) -> float:
        return left + plot_w * (index / max(len(sampled) - 1, 1))

    def y_at(value: float) -> float:
        return top + plot_h * (1 - (value - min_value) / (max_value - min_value))

    paths = []
    for key, label, color in series:
        points = []
        for index, record in enumerate(sampled):
            value = _as_float(record.get(key))
            if value is None:
                continue
            cmd = "M" if not points else "L"
            points.append(f"{cmd}{x_at(index):.2f},{y_at(value):.2f}")
        if points:
            paths.append(
                f'<path d="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.4" '
                f'stroke-linejoin="round" stroke-linecap="round"><title>{_h(label)}</title></path>'
            )
    grid = []
    for i in range(5):
        y = top + plot_h * i / 4
        value = max_value - (max_value - min_value) * i / 4
        grid.append(
            f'<line x1="{left}" x2="{width - right}" y1="{y:.2f}" y2="{y:.2f}" stroke="#e5e7eb" />'
            f'<text x="{left - 8}" y="{y + 4:.2f}" text-anchor="end" fill="#687385" font-size="11">{_h(f"{value:.2f}")}</text>'
        )
    start_date = _date(sampled[0].get("date") or sampled[0].get("trade_date"))
    end_date = _date(sampled[-1].get("date") or sampled[-1].get("trade_date"))
    return f"""
        <svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="策略净值曲线">
          <rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" />
          {"".join(grid)}
          <line x1="{left}" x2="{width - right}" y1="{height - bottom}" y2="{height - bottom}" stroke="#cbd5e1" />
          <line x1="{left}" x2="{left}" y1="{top}" y2="{height - bottom}" stroke="#cbd5e1" />
          {"".join(paths)}
          <text x="{left}" y="{height - 14}" fill="#687385" font-size="12">{_h(start_date)}</text>
          <text x="{width - right}" y="{height - 14}" text-anchor="end" fill="#687385" font-size="12">{_h(end_date)}</text>
        </svg>"""


def _weights_inline(value: object) -> str:
    if not isinstance(value, dict) or not value:
        return "-"
    parts = []
    for code, weight in sorted(value.items(), key=lambda item: _as_float(item[1]) or 0.0, reverse=True):
        parts.append(f"{code} {_pct(weight)}")
    return "；".join(parts)


def _pct(value: object) -> str:
    number = _as_float(value)
    if number is None:
        return "-"
    return f"{number:.2%}"


def _number(value: object, *, digits: int = 2) -> str:
    number = _as_float(value)
    if number is None:
        return "-"
    if digits <= 0:
        return f"{number:.0f}"
    return f"{number:.{digits}f}"


def _date(value: object) -> str:
    text = str(value or "").strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:8]}"
    return text or "-"


def _h(value: object) -> str:
    return escape(str(value), quote=True)


def _as_float(value: object) -> float | None:
    try:
        if value is None:
            return None
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def _strategy_calmar_panel_html() -> str:
    return """
    <section class="conclusion-panel">
      <h2 class="panel-title">Calmar 优化结论</h2>
      <div class="content">
        <ul class="conclusion-list">
          <li><span class="conclusion-key">分层权重模型已更新为 Calmar 全样本最优权重：</span>国信价值0%、创成长R11.13%、红利低波0%、自由现金流R25.22%、黄金ETF23.64%、十年国债ETF40.00%。</li>
          <li><span class="conclusion-key">最优分层权重模型年化表现：</span>2018-09-03 至 2026-07-02 全样本区间，年化收益 12.73%，年化波动 8.86%，最大回撤 7.44%，Sharpe 1.453，Calmar 1.713。</li>
          <li><span class="conclusion-key">全样本表现：</span>优化组合 Calmar 1.713，高于等权组合 1.132；最大回撤 7.44%，低于等权组合 12.12%。</li>
          <li><span class="conclusion-key">70/30 样本外验证：</span>训练期优化权重在样本外 Calmar 0.874，低于等权组合 1.910。</li>
          <li><span class="conclusion-key">审计结论：</span>样本内有效、样本外不稳健，不应直接当作稳健配置，只适合作为参考边界。</li>
        </ul>
      </div>
    </section>"""


def _chinext_intro_panel_html() -> str:
    return """
    <section class="conclusion-panel">
      <h2 class="panel-title">创业板全收益指数对比</h2>
      <div class="content">
        <ul class="conclusion-list">
          <li><span class="conclusion-key">对比对象：</span>399006 创业板指、399673 创业板50、399296 创成长三个指数的全收益版本。</li>
          <li><span class="conclusion-key">实际数据源：</span>399606.SZ 创业板R、CN2673.CNI 创业板50R、CN2296.CNI 创成长R。</li>
          <li><span class="conclusion-key">展示方式：</span>默认三个指数全部勾选，指标和曲线按当前选择区间动态计算。</li>
        </ul>
      </div>
    </section>"""


def _four_asset_calmar_panel_html() -> str:
    return """
    <section class="conclusion-panel">
      <h2 class="panel-title">四资产 Calmar 优化结论</h2>
      <div class="content">
        <ul class="conclusion-list">
          <li><span class="conclusion-key">分层权重模型已更新为 Calmar 全样本最优权重：</span>创业板R15.80%、自由现金流R18.45%、黄金ETF25.74%、十年国债ETF40.00%。</li>
          <li><span class="conclusion-key">最优分层权重模型年化表现：</span>2017-08-24 至 2026-07-02 全样本区间，年化收益 10.43%，年化波动 8.54%，最大回撤 8.05%，Sharpe 1.251，Calmar 1.296。</li>
          <li><span class="conclusion-key">等权组合对比：</span>同区间等权组合年化收益 11.93%，年化波动 11.69%，最大回撤 13.20%，Sharpe 1.061，Calmar 0.904。</li>
          <li><span class="conclusion-key">结论：</span>Calmar 最优模型牺牲部分年化收益，换取更低回撤和更高收益回撤比；十年国债ETF触及40%上限，组合偏防守，全样本优化不代表样本外承诺。</li>
        </ul>
      </div>
    </section>"""


def _three_asset_calmar_panel_html() -> str:
    return """
    <section class="conclusion-panel">
      <h2 class="panel-title">三资产 Calmar 优化结论</h2>
      <div class="content">
        <ul class="conclusion-list">
          <li><span class="conclusion-key">分层权重模型已更新为 Calmar 全样本最优权重：</span>创业板R21.68%、自由现金流R38.32%、黄金ETF40.00%。</li>
          <li><span class="conclusion-key">最优分层权重模型年化表现：</span>2017-08-24 至 2026-07-02 区间，年化收益 14.75%，年化波动 14.38%，最大回撤 15.84%，Sharpe 1.067，Calmar 0.931。</li>
          <li><span class="conclusion-key">等权组合对比：</span>同区间等权组合年化收益 14.39%，年化波动 15.72%，最大回撤 18.69%，Sharpe 0.968，Calmar 0.770。</li>
          <li><span class="conclusion-key">结论：</span>从2017-08-24开始后，Calmar 最优模型仍把黄金ETF打到40%上限，并提高自由现金流R权重；相对等权，年化略高、回撤更低，收益回撤比明显改善。</li>
        </ul>
      </div>
    </section>"""


def render_etf_compare_page(top_panel_html: str = "") -> str:
    page = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ETF 复权对比 - MyInvestStrategyIndex</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1c2430;
      --muted: #687385;
      --line: #d9dee7;
      --accent: #0f766e;
      --soft: #edf7f5;
      --bad: #b42318;
      --good: #157347;
      --warn: #a15c07;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      background: var(--bg);
      color: var(--text);
      letter-spacing: 0;
    }
    .page-header {
      border-bottom: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.97);
    }
    .bar {
      max-width: 1440px;
      margin: 0 auto;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      font-weight: 700;
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .meta {
      display: flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 9px;
      background: #fff;
      white-space: nowrap;
    }
    main {
      max-width: 1600px;
      margin: 0 auto;
      padding: 18px 20px 28px;
      display: grid;
      gap: 16px;
      align-items: start;
    }
    .control-panel, section {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      overflow: hidden;
    }
    .panel-title {
      margin: 0;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      font-size: 15px;
      font-weight: 700;
      background: #fbfcfd;
    }
    .conclusion-panel {
      border-color: #bfd6e3;
      background: #f8fbfc;
    }
    .conclusion-panel .panel-title {
      background: #eef7f7;
      color: #0f4f5f;
    }
    .conclusion-list {
      display: grid;
      gap: 8px;
      margin: 0;
      padding-left: 18px;
      line-height: 1.55;
      font-size: 13px;
    }
    .conclusion-key {
      color: var(--accent);
      font-weight: 700;
    }
    .content { padding: 14px; }
    .stack { display: grid; gap: 16px; }
    .controls-layout {
      display: grid;
      grid-template-columns: minmax(420px, 1.4fr) minmax(320px, 0.95fr) minmax(210px, 0.65fr) minmax(240px, 0.75fr);
      gap: 16px;
      align-items: start;
    }
    .control-group { display: grid; gap: 10px; }
    .control-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--muted);
    }
    .instrument-list {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 8px 14px;
    }
    .instrument {
      display: grid;
      grid-template-columns: auto 14px 1fr;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      line-height: 1.35;
    }
    .swatch {
      width: 12px;
      height: 12px;
      border-radius: 2px;
      display: inline-block;
    }
    .date-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    .control-note {
      grid-column: 1 / -1;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }
    label span {
      display: block;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 4px;
    }
    input[type="date"] {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 7px 8px;
      font: inherit;
      background: #fff;
    }
    .quick-buttons, .actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    button {
      border: 1px solid var(--accent);
      border-radius: 6px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      font-weight: 650;
      padding: 7px 10px;
      cursor: pointer;
      min-height: 34px;
    }
    button.secondary {
      background: #fff;
      color: var(--accent);
    }
    button:disabled {
      cursor: wait;
      opacity: 0.65;
    }
    .icon-button {
      width: 34px;
      padding: 7px 0;
      text-align: center;
    }
    .note {
      color: var(--muted);
      font-size: 12px;
      line-height: 1.55;
    }
    .status {
      min-height: 20px;
      color: var(--muted);
      font-size: 13px;
    }
    .status.error { color: var(--bad); }
    .status.ok { color: var(--good); }
    .chart-wrap {
      padding: 12px 14px 14px;
    }
    .chart-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: baseline;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }
    .chart-title {
      font-size: 15px;
      font-weight: 700;
    }
    .chart-meta {
      color: var(--muted);
      font-size: 12px;
    }
    svg {
      width: 100%;
      height: auto;
      display: block;
      overflow: visible;
    }
    .main-chart svg { min-height: 370px; }
    .drawdown-chart svg { min-height: 165px; }
    .metric-bars svg {
      height: 120px;
      min-height: 0;
    }
    .axis text {
      fill: var(--muted);
      font-size: 12px;
    }
    .axis line, .grid-line {
      stroke: #e8ebf0;
      stroke-width: 1;
    }
    .zero-line {
      stroke: #9aa3af;
      stroke-width: 1;
    }
    .series-line {
      fill: none;
      stroke-width: 2.4;
      stroke-linejoin: round;
      stroke-linecap: round;
    }
    .background-line {
      fill: none;
      stroke: #94a3b8;
      stroke-width: 1.8;
      stroke-linejoin: round;
      stroke-linecap: round;
      stroke-dasharray: 6 5;
      opacity: 0.68;
    }
    .background-label {
      fill: #64748b;
      font-size: 12px;
    }
    #value-chart {
      cursor: grab;
      touch-action: none;
    }
    #value-chart.dragging {
      cursor: grabbing;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 8px 9px;
      text-align: right;
      white-space: nowrap;
    }
    th:first-child, td:first-child {
      text-align: left;
      white-space: normal;
    }
    th {
      color: var(--muted);
      font-weight: 650;
      background: #fbfcfd;
    }
    th[data-sort] {
      cursor: pointer;
      user-select: none;
    }
    th[data-sort]::after {
      content: " ↕";
      color: #9aa3af;
      font-weight: 500;
    }
    th.sorted-asc::after { content: " ↑"; color: var(--accent); }
    th.sorted-desc::after { content: " ↓"; color: var(--accent); }
    .positive { color: var(--good); font-weight: 650; }
    .negative { color: var(--bad); font-weight: 650; }
    .empty {
      color: var(--muted);
      padding: 12px;
      border: 1px dashed var(--line);
      border-radius: 8px;
      background: #fbfcfd;
    }
    @media (max-width: 980px) {
      .bar { align-items: flex-start; flex-direction: column; }
      .meta { justify-content: flex-start; }
      .controls-layout { grid-template-columns: 1fr; }
      .date-row { grid-template-columns: 1fr; }
      th, td { white-space: normal; }
    }
  </style>
</head>
<body>
  __MYINVEST_HEADER__
  <div class="page-header">
    <div class="bar">
      <h1>ETF 复权价值曲线对比</h1>
      <div class="meta">
        <a class="pill" href="/">首页</a>
        <a class="pill" href="/value-compare">策略指数对比</a>
        <a class="pill" href="/chinext-compare">创业板全收益</a>
        <a class="pill" href="/four-asset-compare">四资产组合</a>
        <a class="pill" href="/three-asset-compare">三资产组合</a>
        <span class="pill">主图可左右拖动</span>
        <span class="pill">日线复权口径</span>
      </div>
    </div>
  </div>
  <main>
    __TOP_PANEL__
    <section class="control-panel">
      <h2 class="panel-title">对比设置</h2>
      <div class="content controls-layout">
        <div class="control-group">
          <div class="control-title">标的</div>
          <div id="instrument-list" class="instrument-list"></div>
        </div>
        <div class="control-group">
          <div class="control-title">时间范围</div>
          <div class="quick-buttons">
            <button id="mode-longest" type="button" class="secondary" data-mode="longest">2012起</button>
            <button id="mode-common" type="button" data-mode="common">共同区间</button>
          </div>
          <div class="quick-buttons">
            <button type="button" class="secondary" data-range="all">全部</button>
            <button type="button" class="secondary" data-years="1">近1年</button>
            <button type="button" class="secondary" data-years="3">近3年</button>
            <button type="button" class="secondary" data-years="5">近5年</button>
            <button type="button" class="secondary" data-years="6">近6年</button>
            <button type="button" class="secondary" data-years="7">近7年</button>
            <button type="button" class="secondary" data-years="8">近8年</button>
            <button type="button" class="secondary" data-years="9">近9年</button>
            <button type="button" class="secondary" data-years="10">近10年</button>
            <button type="button" class="secondary" data-since="2021-01-01">2021以来</button>
          </div>
          <div class="date-row">
            <label><span>开始</span><input id="start-date" type="date"></label>
            <label><span>结束</span><input id="end-date" type="date"></label>
          </div>
        </div>
        <div class="control-group">
          <div class="control-title">Y轴</div>
          <div class="quick-buttons">
            <button id="axis-return" type="button" data-y-axis="return">累计收益率%</button>
            <button id="axis-multiple" type="button" class="secondary" data-y-axis="multiple">净值倍数</button>
            <button id="axis-log" type="button" class="secondary" data-y-axis="log">对数</button>
          </div>
        </div>
        <div class="control-group">
          <div class="control-title">操作</div>
          <div class="actions">
            <button id="pan-left" type="button" class="secondary icon-button" title="左移" aria-label="左移">←</button>
            <button id="zoom-in" type="button" class="secondary icon-button" title="放大" aria-label="放大">+</button>
            <button id="zoom-out" type="button" class="secondary icon-button" title="缩小" aria-label="缩小">-</button>
            <button id="pan-right" type="button" class="secondary icon-button" title="右移" aria-label="右移">→</button>
            <button id="reset-range" type="button" class="secondary">恢复全区间</button>
            <button id="refresh-data" type="button">更新数据</button>
          </div>
          <div id="status" class="status">准备加载数据...</div>
        </div>
        <div class="note control-note">
          2012起模式按最早可用 ETF 开始展示；后上市 ETF 从上市日对应的虚拟等权ETF位置接上。虚拟等权ETF按 512890、510500、510300、159915 四只真实 ETF 中当日已有数据的成分动态等权；480092 为自由现金流R收益指数点位代理。
        </div>
      </div>
    </section>
    <div class="stack">
      <section class="main-chart">
        <div class="chart-wrap">
          <div class="chart-head">
            <div id="value-chart-title" class="chart-title" data-base-title="复权价值曲线">复权价值曲线</div>
            <div id="range-hint" class="chart-meta">-</div>
          </div>
          <svg id="value-chart" viewBox="0 0 1000 390" role="img" aria-label="复权价值曲线"></svg>
        </div>
      </section>
      <section class="drawdown-chart">
        <div class="chart-wrap">
          <div class="chart-head">
            <div class="chart-title">回撤曲线</div>
            <div class="chart-meta">越接近 0 越好</div>
          </div>
          <svg id="drawdown-chart" viewBox="0 0 1000 165" role="img" aria-label="回撤曲线"></svg>
        </div>
      </section>
      <section class="metric-bars">
        <div class="chart-wrap">
          <div class="chart-head">
            <div class="chart-title">年化收益 vs 最大回撤</div>
            <div class="chart-meta">当前区间动态计算</div>
          </div>
          <svg id="bar-chart" viewBox="0 0 1000 120" role="img" aria-label="年化收益与最大回撤柱状图"></svg>
        </div>
      </section>
      <section>
        <h2 class="panel-title">指标对比</h2>
        <div class="content">
          <table>
            <thead>
              <tr>
                <th data-sort="name">标的</th>
                <th data-sort="totalReturn">总收益</th>
                <th data-sort="maxReturn">区间最高收益</th>
                <th data-sort="annualizedReturn">年化收益</th>
                <th data-sort="maxDrawdown">最大回撤</th>
                <th data-sort="annualizedVolatility">年化波动</th>
                <th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>
              </tr>
            </thead>
            <tbody id="metrics-body"></tbody>
          </table>
        </div>
      </section>
      <section id="errors-section" hidden>
        <h2 class="panel-title">数据提示</h2>
        <div id="errors" class="content note"></div>
      </section>
    </div>
  </main>
  __MYINVEST_FOOTER__
<script>
const MS_DAY = 24 * 60 * 60 * 1000;
const VALUE_BOX = { width: 1000, height: 390, plot: { left: 58, right: 20, top: 22, bottom: 38 } };
const DRAW_BOX = { width: 1000, height: 165, plot: { left: 58, right: 20, top: 14, bottom: 30 } };
const BAR_BOX = { width: 1000, height: 120, plot: { left: 46, right: 18, top: 18, bottom: 30 } };
const API_PATH = document.body.dataset.apiPath || "/api/etf-compare/history.json";
const SYNTHETIC_CODE = document.body.dataset.syntheticCode || "VIRTUAL_EQUAL_WEIGHT";
const RISK_PARITY_CODE = document.body.dataset.riskParityCode || "";
const ANCHOR_TO_SYNTHETIC = document.body.dataset.anchorSynthetic !== "false";
const LONGEST_MODE_LABEL = document.body.dataset.longestModeLabel || "2012起";
const LONGEST_BASE_TEXT = document.body.dataset.longestBaseText || "后上市标的接到虚拟等权ETF位置";
const INCLUDE_RECOVERY_METRICS = document.body.dataset.extraMetrics === "true";
const SHOW_BACKGROUND = document.body.dataset.showBackground === "true";
const DEFAULT_START_DATE = document.body.dataset.defaultStartDate || "";
const DEFAULT_UNSELECTED_CODES = new Set(
  (document.body.dataset.defaultUnselectedCodes || "")
    .split(",")
    .map((code) => code.trim())
    .filter(Boolean)
);
const VALUE_AXIS_MODES = {
  return: { title: "累计收益率%", baseline: 0 },
  multiple: { title: "净值倍数", baseline: 1 },
  log: { title: "对数累计收益率%", baseline: 1 },
};

const state = {
  payload: null,
  selected: new Set(),
  drag: null,
  dynamicSyntheticRows: [],
  dynamicRiskParityRows: [],
  rangeMode: "common",
  valueAxisMode: "return",
  sortKey: "annualizedReturnDrawdownRatio",
  sortDirection: "desc",
};

const dom = {
  instruments: document.getElementById("instrument-list"),
  start: document.getElementById("start-date"),
  end: document.getElementById("end-date"),
  status: document.getElementById("status"),
  hint: document.getElementById("range-hint"),
  valueTitle: document.getElementById("value-chart-title"),
  valueChart: document.getElementById("value-chart"),
  drawdownChart: document.getElementById("drawdown-chart"),
  barChart: document.getElementById("bar-chart"),
  metricsBody: document.getElementById("metrics-body"),
  errorsSection: document.getElementById("errors-section"),
  errors: document.getElementById("errors"),
  refresh: document.getElementById("refresh-data"),
  reset: document.getElementById("reset-range"),
  panLeft: document.getElementById("pan-left"),
  panRight: document.getElementById("pan-right"),
  zoomIn: document.getElementById("zoom-in"),
  zoomOut: document.getElementById("zoom-out"),
  axisReturn: document.getElementById("axis-return"),
  axisMultiple: document.getElementById("axis-multiple"),
  axisLog: document.getElementById("axis-log"),
  modeCommon: document.getElementById("mode-common"),
  modeLongest: document.getElementById("mode-longest"),
};
const VALUE_TITLE_BASE = dom.valueTitle?.dataset.baseTitle || "价值曲线";

function setStatus(text, kind = "") {
  dom.status.textContent = text;
  dom.status.className = `status ${kind}`.trim();
}

function parseDate(value) {
  return new Date(`${value}T00:00:00+08:00`).getTime();
}

function fmtDate(ms) {
  const d = new Date(ms);
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function pct(value) {
  if (!Number.isFinite(value)) return "-";
  return `${(value * 100).toFixed(2)}%`;
}

function ratioText(value) {
  if (!Number.isFinite(value)) return "-";
  return value.toFixed(2);
}

function valueAxisConfig() {
  return VALUE_AXIS_MODES[state.valueAxisMode] || VALUE_AXIS_MODES.return;
}

function valueAxisLabel() {
  return valueAxisConfig().title;
}

function commonBaseText() {
  if (state.valueAxisMode === "multiple") return "共同起点=1x";
  if (state.valueAxisMode === "log") return "共同起点=0%（对数）";
  return "共同起点=0%";
}

function valueAxisY(rawValue) {
  const multiple = rawValue / 100;
  if (state.valueAxisMode === "multiple" || state.valueAxisMode === "log") return multiple;
  return multiple - 1;
}

function formatValueAxis(value) {
  if (state.valueAxisMode === "multiple") {
    if (Math.abs(value) >= 10) return `${value.toFixed(0)}x`;
    return `${value.toFixed(1)}x`;
  }
  const pctValue = state.valueAxisMode === "log" ? (value - 1) * 100 : value * 100;
  if (Math.abs(pctValue) >= 100) return `${pctValue.toFixed(0)}%`;
  return `${pctValue.toFixed(1)}%`;
}

function recoveryText(days) {
  if (!Number.isFinite(days)) return "-";
  if (days < 30) return `${Math.round(days)}天`;
  return `${(days / 365.25).toFixed(1)}年`;
}

function metricColumnCount() {
  return INCLUDE_RECOVERY_METRICS ? 9 : 7;
}

function moneyText(value) {
  if (!Number.isFinite(value)) return "-";
  return value.toFixed(1);
}

function svgEl(name, attrs = {}) {
  const node = document.createElementNS("http://www.w3.org/2000/svg", name);
  for (const [key, value] of Object.entries(attrs)) {
    node.setAttribute(key, String(value));
  }
  return node;
}

function clearSvg(svg) {
  while (svg.firstChild) svg.removeChild(svg.firstChild);
}

async function loadHistory(refresh = false) {
  dom.refresh.disabled = true;
  setStatus(refresh ? "正在更新历史数据..." : "正在加载历史数据...");
  try {
    const response = await fetch(`${API_PATH}${refresh ? "?refresh=1" : ""}`);
    const payload = await response.json();
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || "历史数据加载失败");
    }
    for (const rows of Object.values(payload.series)) {
      rows.forEach((row) => {
        row.dateMs = parseDate(row.date);
        row.close = Number(row.close);
        row.value = Number(row.value);
      });
    }
    if (Array.isArray(payload.background_series)) {
      payload.background_series.forEach((row) => {
        row.dateMs = parseDate(row.date);
        row.close = Number(row.close);
        row.value = Number(row.value);
      });
    }
    state.payload = payload;
    state.selected = new Set(
      payload.instruments
        .filter((item) => payload.series[item.code]?.length && !DEFAULT_UNSELECTED_CODES.has(item.code))
        .map((item) => item.code)
    );
    renderInstrumentControls();
    setRangeToCurrentMode();
    renderAll();
    setStatus(refresh ? "数据已更新" : "数据已加载", "ok");
  } catch (error) {
    setStatus(`失败：${error.message}`, "error");
  } finally {
    dom.refresh.disabled = false;
  }
}

function renderInstrumentControls() {
  dom.instruments.innerHTML = "";
  state.payload.instruments.forEach((item) => {
    const hasData = Boolean(state.payload.series[item.code]?.length);
    const label = document.createElement("label");
    label.className = "instrument";
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = item.code;
    input.checked = state.selected.has(item.code);
    input.disabled = !hasData;
    input.addEventListener("change", () => {
      if (input.checked) state.selected.add(item.code);
      else state.selected.delete(item.code);
      clampInputsToCurrentMode();
      renderAll();
    });
    const swatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.style.background = item.color;
    const text = document.createElement("span");
    text.textContent = hasData ? item.name : `${item.name}（无数据）`;
    label.append(input, swatch, text);
    dom.instruments.appendChild(label);
  });
}

function selectedCodes() {
  return Array.from(state.selected).filter((code) => state.payload.series[code]?.length);
}

function isSyntheticCode(code) {
  const instrument = instrumentByCode(code);
  return String(instrument.kind || "").startsWith("synthetic_");
}

function isDynamicSyntheticCode(code) {
  return code === SYNTHETIC_CODE || (RISK_PARITY_CODE && code === RISK_PARITY_CODE);
}

function selectedComponentCodes() {
  return selectedCodes().filter((code) => !isSyntheticCode(code));
}

function boundsCodes(codes = selectedCodes()) {
  const output = [];
  codes.forEach((code) => {
    if (isDynamicSyntheticCode(code)) output.push(...selectedComponentCodes());
    else output.push(code);
  });
  return Array.from(new Set(output)).filter((code) => state.payload.series[code]?.length);
}

function getCommonBounds(codes = selectedCodes()) {
  codes = boundsCodes(codes);
  if (!codes.length) return null;
  const starts = [];
  const ends = [];
  codes.forEach((code) => {
    const rows = state.payload.series[code] || [];
    if (rows.length) {
      starts.push(rows[0].dateMs);
      ends.push(rows[rows.length - 1].dateMs);
    }
  });
  if (!starts.length) return null;
  return { start: Math.max(...starts), end: Math.min(...ends) };
}

function getLongestBounds(codes = selectedCodes()) {
  codes = boundsCodes(codes);
  if (!codes.length) return null;
  const starts = [];
  const ends = [];
  codes.forEach((code) => {
    const rows = state.payload.series[code] || [];
    if (rows.length) {
      starts.push(rows[0].dateMs);
      ends.push(rows[rows.length - 1].dateMs);
    }
  });
  if (!starts.length) return null;
  return { start: Math.min(...starts), end: Math.max(...ends) };
}

function currentBounds() {
  return state.rangeMode === "longest" ? getLongestBounds() : getCommonBounds();
}

function defaultStartForBounds(bounds) {
  if (!DEFAULT_START_DATE) return bounds.start;
  const defaultStart = parseDate(DEFAULT_START_DATE);
  if (!Number.isFinite(defaultStart)) return bounds.start;
  return Math.min(Math.max(defaultStart, bounds.start), bounds.end);
}

function setRangeToCurrentMode() {
  const bounds = currentBounds();
  if (!bounds) return;
  dom.start.value = fmtDate(defaultStartForBounds(bounds));
  dom.end.value = fmtDate(bounds.end);
}

function clampInputsToCurrentMode() {
  const bounds = currentBounds();
  if (!bounds) return;
  let start = dom.start.value ? parseDate(dom.start.value) : defaultStartForBounds(bounds);
  let end = dom.end.value ? parseDate(dom.end.value) : bounds.end;
  start = Math.max(start, bounds.start);
  end = Math.min(end, bounds.end);
  if (start > end) {
    start = bounds.start;
    end = bounds.end;
  }
  dom.start.value = fmtDate(start);
  dom.end.value = fmtDate(end);
}

function activeRange() {
  const bounds = currentBounds();
  if (!bounds) return null;
  let start = dom.start.value ? parseDate(dom.start.value) : defaultStartForBounds(bounds);
  let end = dom.end.value ? parseDate(dom.end.value) : bounds.end;
  start = Math.max(start, bounds.start);
  end = Math.min(end, bounds.end);
  if (start > end) {
    const tmp = start;
    start = end;
    end = tmp;
  }
  return { start, end, commonStart: bounds.start, commonEnd: bounds.end };
}

function setActiveRange(start, end, shouldRender = true) {
  const bounds = currentBounds();
  if (!bounds) return false;
  let nextStart = Number(start);
  let nextEnd = Number(end);
  if (!Number.isFinite(nextStart) || !Number.isFinite(nextEnd)) return false;
  if (nextStart > nextEnd) {
    const tmp = nextStart;
    nextStart = nextEnd;
    nextEnd = tmp;
  }
  const boundsSpan = Math.max(bounds.end - bounds.start, MS_DAY);
  let span = Math.max(nextEnd - nextStart, MS_DAY);
  if (span >= boundsSpan) {
    nextStart = bounds.start;
    nextEnd = bounds.end;
  } else {
    if (nextStart < bounds.start) {
      nextEnd += bounds.start - nextStart;
      nextStart = bounds.start;
    }
    if (nextEnd > bounds.end) {
      nextStart -= nextEnd - bounds.end;
      nextEnd = bounds.end;
    }
    nextStart = Math.max(bounds.start, nextStart);
    nextEnd = Math.min(bounds.end, nextEnd);
  }
  dom.start.value = fmtDate(nextStart);
  dom.end.value = fmtDate(nextEnd);
  if (shouldRender) renderAll();
  return true;
}

function rowsInRange(code, range) {
  if (code === SYNTHETIC_CODE) {
    return state.dynamicSyntheticRows.filter((row) => row.dateMs >= range.start && row.dateMs <= range.end);
  }
  if (RISK_PARITY_CODE && code === RISK_PARITY_CODE) {
    return state.dynamicRiskParityRows.filter((row) => row.dateMs >= range.start && row.dateMs <= range.end);
  }
  return (state.payload.series[code] || []).filter((row) => row.dateMs >= range.start && row.dateMs <= range.end);
}

function calculateMetrics(rows) {
  if (rows.length < 2) return null;
  const first = rows[0];
  const last = rows[rows.length - 1];
  const base = first.value;
  const totalReturn = last.value / base - 1;
  const days = Math.max((last.dateMs - first.dateMs) / MS_DAY, 1);
  const annualizedReturn = Math.pow(last.value / base, 365.25 / days) - 1;
  let peak = -Infinity;
  let peakDateMs = first.dateMs;
  let underwaterStartMs = null;
  let maxDrawdown = 0;
  let maxReturn = -Infinity;
  let longestRecoveryDays = 0;
  const dailyReturns = [];
  rows.forEach((row, index) => {
    if (row.value >= peak) {
      if (underwaterStartMs !== null) {
        longestRecoveryDays = Math.max(longestRecoveryDays, (row.dateMs - underwaterStartMs) / MS_DAY);
        underwaterStartMs = null;
      }
      peak = row.value;
      peakDateMs = row.dateMs;
    } else if (underwaterStartMs === null) {
      underwaterStartMs = peakDateMs;
    }
    maxDrawdown = Math.min(maxDrawdown, row.value / peak - 1);
    maxReturn = Math.max(maxReturn, row.value / base - 1);
    if (index > 0) {
      const prev = rows[index - 1].value;
      if (prev > 0) dailyReturns.push(row.value / prev - 1);
    }
  });
  if (underwaterStartMs !== null) {
    longestRecoveryDays = Math.max(longestRecoveryDays, (last.dateMs - underwaterStartMs) / MS_DAY);
  }
  const rollingWindowMs = 3 * 365.25 * MS_DAY;
  let rollingThreeYearWorstReturn = NaN;
  let endIndex = 0;
  rows.forEach((startRow) => {
    const targetDate = startRow.dateMs + rollingWindowMs;
    while (endIndex < rows.length && rows[endIndex].dateMs < targetDate) endIndex += 1;
    if (endIndex < rows.length && startRow.value > 0) {
      const rollingReturn = rows[endIndex].value / startRow.value - 1;
      rollingThreeYearWorstReturn = Number.isFinite(rollingThreeYearWorstReturn)
        ? Math.min(rollingThreeYearWorstReturn, rollingReturn)
        : rollingReturn;
    }
  });
  const avg = dailyReturns.reduce((sum, item) => sum + item, 0) / Math.max(dailyReturns.length, 1);
  const variance = dailyReturns.reduce((sum, item) => sum + Math.pow(item - avg, 2), 0) / Math.max(dailyReturns.length - 1, 1);
  const annualizedVolatility = Math.sqrt(variance) * Math.sqrt(252);
  return {
    totalReturn,
    maxReturn,
    annualizedReturn,
    maxDrawdown,
    annualizedVolatility,
    annualizedReturnDrawdownRatio: annualizedReturn / Math.abs(maxDrawdown || NaN),
    longestRecoveryDays,
    rollingThreeYearWorstReturn,
  };
}

function equalWeightAnchor(dateMs, range) {
  const equalRows = rowsInRange(SYNTHETIC_CODE, range);
  if (!equalRows.length) return 100;
  const base = equalRows[0].value;
  let anchorRow = equalRows[0];
  for (const row of equalRows) {
    if (row.dateMs <= dateMs) anchorRow = row;
    else break;
  }
  return anchorRow.value / base * 100;
}

function buildDynamicSyntheticRows(range) {
  const componentRows = selectedComponentCodes()
    .map((code) => rowsInRange(code, range))
    .filter((rows) => rows.length >= 2);
  if (!componentRows.length) return [];

  const allDates = new Set();
  const returnMaps = componentRows.map((rows) => {
    const returns = new Map();
    rows.forEach((row) => allDates.add(row.dateMs));
    rows.forEach((row, index) => {
      if (index === 0) return;
      const prev = rows[index - 1].value;
      if (prev > 0) returns.set(row.dateMs, row.value / prev - 1);
    });
    return returns;
  });
  const dates = Array.from(allDates).sort((left, right) => left - right);
  let value = 1;
  return dates.map((dateMs, index) => {
    if (index > 0) {
      const availableReturns = returnMaps
        .filter((returns) => returns.has(dateMs))
        .map((returns) => returns.get(dateMs))
        .filter(Number.isFinite);
      if (availableReturns.length) {
        value *= 1 + availableReturns.reduce((sum, item) => sum + item, 0) / availableReturns.length;
      }
    }
    return { dateMs, close: value, value };
  });
}

function buildRiskParityRows(range) {
  if (!RISK_PARITY_CODE) return [];
  const componentRows = selectedComponentCodes()
    .map((code) => rowsInRange(code, range))
    .filter((rows) => rows.length >= 2);
  if (componentRows.length < 2) return [];

  const allDates = new Set();
  const returnMaps = componentRows.map((rows) => {
    const returns = new Map();
    rows.forEach((row) => allDates.add(row.dateMs));
    rows.forEach((row, index) => {
      if (index === 0) return;
      const prev = rows[index - 1].value;
      if (prev > 0) returns.set(row.dateMs, row.value / prev - 1);
    });
    return returns;
  });
  const dates = Array.from(allDates).sort((left, right) => left - right);
  const trailingReturns = returnMaps.map(() => []);
  let value = 1;
  return dates.map((dateMs, index) => {
    const available = returnMaps
      .map((returns, assetIndex) => ({
        assetIndex,
        dailyReturn: returns.get(dateMs),
        volatility: trailingVolatility(trailingReturns[assetIndex]),
      }))
      .filter((item) => Number.isFinite(item.dailyReturn));
    if (index > 0 && available.length) {
      const weights = inverseVolatilityWeights(available.map((item) => item.volatility));
      const portfolioReturn = available.reduce((sum, item, itemIndex) => sum + item.dailyReturn * weights[itemIndex], 0);
      value *= 1 + portfolioReturn;
    }
    returnMaps.forEach((returns, assetIndex) => {
      const dailyReturn = returns.get(dateMs);
      if (Number.isFinite(dailyReturn)) trailingReturns[assetIndex].push(dailyReturn);
    });
    return { dateMs, close: value, value };
  });
}

function trailingVolatility(values, window = 60) {
  const recent = values.slice(-window).filter(Number.isFinite);
  if (recent.length < 20) return NaN;
  const avg = recent.reduce((sum, item) => sum + item, 0) / recent.length;
  const variance = recent.reduce((sum, item) => sum + Math.pow(item - avg, 2), 0) / Math.max(recent.length - 1, 1);
  return Math.sqrt(variance);
}

function inverseVolatilityWeights(volatilities) {
  const valid = volatilities.filter((item) => Number.isFinite(item) && item > 1e-9).sort((left, right) => left - right);
  const fallback = valid.length ? valid[Math.floor(valid.length / 2)] : NaN;
  const inverse = volatilities.map((volatility) => {
    const usable = Number.isFinite(volatility) && volatility > 1e-9 ? volatility : fallback;
    return Number.isFinite(usable) && usable > 1e-9 ? 1 / usable : 1;
  });
  const total = inverse.reduce((sum, item) => sum + item, 0);
  if (!Number.isFinite(total) || total <= 0) return volatilities.map(() => 1 / volatilities.length);
  return inverse.map((item) => item / total);
}

function normalizedSeries(code, range) {
  const rows = rowsInRange(code, range);
  if (rows.length < 2) return null;
  const base = rows[0].value;
  const anchor = ANCHOR_TO_SYNTHETIC && state.rangeMode === "longest" && !isSyntheticCode(code)
    ? equalWeightAnchor(rows[0].dateMs, range)
    : 100;
  let peak = -Infinity;
  const values = rows.map((row) => {
    const value = row.value / base * anchor;
    peak = Math.max(peak, row.value);
    return {
      dateMs: row.dateMs,
      value,
      drawdown: row.value / peak - 1,
    };
  });
  return { code, values, metrics: calculateMetrics(rows), rows };
}

function backgroundNormalizedSeries(range) {
  if (!SHOW_BACKGROUND || !Array.isArray(state.payload.background_series)) return null;
  const rows = state.payload.background_series.filter((row) => row.dateMs >= range.start && row.dateMs <= range.end);
  if (rows.length < 2) return null;
  const base = rows[0].value;
  if (!Number.isFinite(base) || base <= 0) return null;
  let peak = -Infinity;
  const code = state.payload.background?.code || "BACKGROUND";
  const values = rows.map((row) => {
    const value = row.value / base * 100;
    peak = Math.max(peak, row.value);
    return {
      dateMs: row.dateMs,
      value,
      drawdown: row.value / peak - 1,
    };
  });
  return { code, values, rows, background: true };
}

function renderAll() {
  if (!state.payload) return;
  const range = activeRange();
  const codes = selectedCodes();
  if (!range || !codes.length) {
    dom.metricsBody.innerHTML = `<tr><td colspan="${metricColumnCount()}">请至少选择一个有数据的标的。</td></tr>`;
    clearSvg(dom.valueChart);
    clearSvg(dom.drawdownChart);
    clearSvg(dom.barChart);
    return;
  }
  dom.start.value = fmtDate(range.start);
  dom.end.value = fmtDate(range.end);
  state.dynamicSyntheticRows = buildDynamicSyntheticRows(range);
  state.dynamicRiskParityRows = buildRiskParityRows(range);
  const series = codes.map((code) => normalizedSeries(code, range)).filter(Boolean);
  const background = backgroundNormalizedSeries(range);
  const modeText = state.rangeMode === "longest" ? LONGEST_MODE_LABEL : "共同区间";
  const baseText = state.rangeMode === "longest" ? LONGEST_BASE_TEXT : commonBaseText();
  dom.valueTitle.textContent = `${VALUE_TITLE_BASE}（${valueAxisLabel()}）`;
  dom.hint.textContent = `${modeText}：${fmtDate(range.start)} 至 ${fmtDate(range.end)}；${baseText}；已显示 ${series.length} 个标的`;
  renderLineChart(dom.valueChart, VALUE_BOX, series, "value", background);
  renderLineChart(dom.drawdownChart, DRAW_BOX, series, "drawdown");
  renderBarChart(series);
  renderMetricsTable(series);
  renderErrors();
}

function renderLineChart(svg, box, series, mode, background = null) {
  clearSvg(svg);
  const plot = box.plot;
  const width = box.width - plot.left - plot.right;
  const height = box.height - plot.top - plot.bottom;
  const renderSeries = background && mode === "value" ? [background, ...series] : series;
  const allPoints = renderSeries.flatMap((item) => item.values);
  if (!allPoints.length) return;
  const xMin = Math.min(...allPoints.map((item) => item.dateMs));
  const xMax = Math.max(...allPoints.map((item) => item.dateMs));
  const pointY = (point) => mode === "drawdown" ? point.drawdown : valueAxisY(point.value);
  let yMin;
  let yMax;
  if (mode === "drawdown") {
    yMin = Math.min(...allPoints.map((item) => item.drawdown), -0.01);
    yMax = 0;
  } else if (state.valueAxisMode === "log") {
    yMin = Math.min(...allPoints.map((item) => valueAxisY(item.value)), 1);
    yMax = Math.max(...allPoints.map((item) => valueAxisY(item.value)), 1);
    yMin = Math.max(yMin, 0.0001);
    yMax = Math.max(yMax, yMin * 1.01);
    const logMin = Math.log(yMin);
    const logMax = Math.log(yMax);
    const padding = (logMax - logMin || 1) * 0.08;
    yMin = Math.exp(logMin - padding);
    yMax = Math.exp(logMax + padding);
  } else {
    const baseline = valueAxisConfig().baseline;
    yMin = Math.min(...allPoints.map((item) => valueAxisY(item.value)), baseline);
    yMax = Math.max(...allPoints.map((item) => valueAxisY(item.value)), baseline);
    const padding = (yMax - yMin || 1) * 0.08;
    yMin = state.valueAxisMode === "multiple" ? Math.max(yMin - padding, 0) : Math.max(yMin - padding, -1);
    yMax += padding;
  }
  const xScale = (value) => plot.left + ((value - xMin) / Math.max(xMax - xMin, 1)) * width;
  const yScale = state.valueAxisMode === "log" && mode === "value"
    ? (value) => {
        const safeMin = Math.max(yMin, 0.0001);
        const safeValue = Math.max(value, 0.0001);
        return plot.top + (1 - (Math.log(safeValue) - Math.log(safeMin)) / Math.max(Math.log(yMax) - Math.log(safeMin), 1e-9)) * height;
      }
    : (value) => plot.top + (1 - (value - yMin) / Math.max(yMax - yMin, 1)) * height;
  drawGrid(svg, box, xMin, xMax, yMin, yMax, mode, yScale);
  if (mode === "value") {
    const baseline = valueAxisConfig().baseline;
    if (yMin < baseline && yMax > baseline) {
      svg.appendChild(svgEl("line", { x1: plot.left, x2: plot.left + width, y1: yScale(baseline), y2: yScale(baseline), class: "zero-line" }));
    }
  }
  if (mode === "drawdown") {
    svg.appendChild(svgEl("line", { x1: plot.left, x2: plot.left + width, y1: yScale(0), y2: yScale(0), class: "zero-line" }));
  }
  if (background && mode === "value") {
    const points = background.values.map((point) => [
      xScale(point.dateMs),
      yScale(pointY(point)),
    ]);
    const path = points.map((point, index) => `${index ? "L" : "M"}${point[0].toFixed(1)},${point[1].toFixed(1)}`).join(" ");
    svg.appendChild(svgEl("path", { d: path, class: "background-line", stroke: state.payload.background?.color || "#94A3B8" }));
    const label = svgEl("text", {
      x: plot.left + width - 4,
      y: plot.top + 16,
      "text-anchor": "end",
      class: "background-label",
    });
    label.textContent = `背景：${state.payload.background?.name || "上证指数"}`;
    svg.appendChild(label);
  }
  series.forEach((item) => {
    const instrument = instrumentByCode(item.code);
    const points = item.values.map((point) => [
      xScale(point.dateMs),
      yScale(pointY(point)),
    ]);
    const path = points.map((point, index) => `${index ? "L" : "M"}${point[0].toFixed(1)},${point[1].toFixed(1)}`).join(" ");
    svg.appendChild(svgEl("path", { d: path, class: "series-line", stroke: instrument.color }));
  });
}

function drawGrid(svg, box, xMin, xMax, yMin, yMax, mode, yScale) {
  const plot = box.plot;
  const width = box.width - plot.left - plot.right;
  const height = box.height - plot.top - plot.bottom;
  const axis = svgEl("g", { class: "axis" });
  for (let i = 0; i <= 4; i++) {
    const value = mode === "value" && state.valueAxisMode === "log"
      ? Math.exp(Math.log(yMax) - (Math.log(yMax) - Math.log(Math.max(yMin, 0.0001))) * i / 4)
      : yMax - (yMax - yMin) * i / 4;
    const y = yScale(value);
    axis.appendChild(svgEl("line", { x1: plot.left, x2: plot.left + width, y1: y, y2: y, class: "grid-line" }));
    const text = svgEl("text", { x: plot.left - 8, y: y + 4, "text-anchor": "end" });
    text.textContent = mode === "drawdown" ? `${(value * 100).toFixed(0)}%` : formatValueAxis(value);
    axis.appendChild(text);
  }
  for (let i = 0; i <= 4; i++) {
    const x = plot.left + width * i / 4;
    const dateMs = xMin + (xMax - xMin) * i / 4;
    axis.appendChild(svgEl("line", { x1: x, x2: x, y1: plot.top, y2: plot.top + height, class: "grid-line" }));
    const text = svgEl("text", { x, y: plot.top + height + 24, "text-anchor": "middle" });
    text.textContent = fmtDate(dateMs).slice(0, 7);
    axis.appendChild(text);
  }
  svg.appendChild(axis);
}

function renderBarChart(series) {
  const svg = dom.barChart;
  clearSvg(svg);
  const box = BAR_BOX;
  const plot = box.plot;
  const width = box.width - plot.left - plot.right;
  const height = box.height - plot.top - plot.bottom;
  const maxValue = Math.max(
    ...series.map((item) => Math.max(item.metrics.annualizedReturn, Math.abs(item.metrics.maxDrawdown))).filter(Number.isFinite),
    0.1
  );
  const yScale = (value) => plot.top + (1 - value / (maxValue * 1.18)) * height;
  for (let i = 0; i <= 4; i++) {
    const value = maxValue * 1.18 * i / 4;
    const y = yScale(value);
    svg.appendChild(svgEl("line", { x1: plot.left, x2: plot.left + width, y1: y, y2: y, class: "grid-line" }));
    const label = svgEl("text", { x: plot.left - 7, y: y + 4, "text-anchor": "end", class: "axis" });
    label.textContent = `${(value * 100).toFixed(0)}%`;
    svg.appendChild(label);
  }
  const groupWidth = width / Math.max(series.length, 1);
  const barWidth = Math.min(28, groupWidth * 0.28);
  series.forEach((item, index) => {
    const instrument = instrumentByCode(item.code);
    const center = plot.left + groupWidth * index + groupWidth / 2;
    const ann = Math.max(item.metrics.annualizedReturn, 0);
    const dd = Math.abs(item.metrics.maxDrawdown);
    const annY = yScale(ann);
    const ddY = yScale(dd);
    svg.appendChild(svgEl("rect", { x: center - barWidth - 2, y: annY, width: barWidth, height: plot.top + height - annY, fill: "#2E7D32" }));
    svg.appendChild(svgEl("rect", { x: center + 2, y: ddY, width: barWidth, height: plot.top + height - ddY, fill: instrument.color }));
    const annLabel = svgEl("text", { x: center - barWidth / 2 - 2, y: annY - 5, "text-anchor": "middle", class: "axis" });
    annLabel.textContent = `${(ann * 100).toFixed(1)}%`;
    svg.appendChild(annLabel);
    const ddLabel = svgEl("text", { x: center + barWidth / 2 + 2, y: ddY - 5, "text-anchor": "middle", class: "axis" });
    ddLabel.textContent = `${(dd * 100).toFixed(1)}%`;
    svg.appendChild(ddLabel);
    const name = instrument.name.replace(/ ETF|指数/g, "");
    const text = svgEl("text", { x: center, y: plot.top + height + 24, "text-anchor": "middle", class: "axis" });
    text.textContent = name.length > 8 ? name.slice(0, 8) : name;
    svg.appendChild(text);
  });
  const legend = svgEl("g", {});
  legend.appendChild(svgEl("rect", { x: plot.left, y: 0, width: 12, height: 12, fill: "#2E7D32" }));
  const annText = svgEl("text", { x: plot.left + 18, y: 11, class: "axis" });
  annText.textContent = "年化收益";
  legend.appendChild(annText);
  legend.appendChild(svgEl("rect", { x: plot.left + 94, y: 0, width: 12, height: 12, fill: "#64748B" }));
  const ddText = svgEl("text", { x: plot.left + 112, y: 11, class: "axis" });
  ddText.textContent = "最大回撤=曲线色";
  legend.appendChild(ddText);
  svg.appendChild(legend);
}

function renderMetricsTable(series) {
  dom.metricsBody.innerHTML = "";
  if (!series.length) {
    dom.metricsBody.innerHTML = `<tr><td colspan="${metricColumnCount()}">暂无可比数据。</td></tr>`;
    return;
  }
  updateSortHeaders();
  const sorted = [...series].sort(compareMetricRows);
  sorted.forEach((item) => {
    const instrument = instrumentByCode(item.code);
    const row = document.createElement("tr");
    const cells = [
      { value: instrument.name, type: "text" },
      { value: pct(item.metrics.totalReturn), type: "gain" },
      { value: pct(item.metrics.maxReturn), type: "gain" },
      { value: pct(item.metrics.annualizedReturn), type: "gain" },
      { value: pct(item.metrics.maxDrawdown), type: "loss" },
      { value: pct(item.metrics.annualizedVolatility), type: "gain" },
      { value: ratioText(item.metrics.annualizedReturnDrawdownRatio), type: "ratio" },
    ];
    if (INCLUDE_RECOVERY_METRICS) {
      cells.push(
        { value: recoveryText(item.metrics.longestRecoveryDays), type: "duration" },
        { value: pct(item.metrics.rollingThreeYearWorstReturn), type: "loss" },
      );
    }
    cells.forEach((cellData) => {
      const cell = document.createElement("td");
      const value = cellData.value;
      cell.textContent = value;
      if (cellData.type !== "text" && cellData.type !== "duration" && value !== "-") {
        const numeric = Number(value.replace("%", ""));
        if (cellData.type === "loss") cell.className = "negative";
        else if (numeric >= 0) cell.className = "positive";
        else cell.className = "negative";
      }
      row.appendChild(cell);
    });
    dom.metricsBody.appendChild(row);
  });
}

function compareMetricRows(left, right) {
  const leftInstrument = instrumentByCode(left.code);
  const rightInstrument = instrumentByCode(right.code);
  let leftValue;
  let rightValue;
  if (state.sortKey === "name") {
    leftValue = leftInstrument.name;
    rightValue = rightInstrument.name;
  } else {
    leftValue = left.metrics[state.sortKey];
    rightValue = right.metrics[state.sortKey];
  }
  let result;
  if (typeof leftValue === "string" || typeof rightValue === "string") {
    result = String(leftValue).localeCompare(String(rightValue), "zh-CN");
  } else {
    const leftNumber = Number.isFinite(leftValue) ? leftValue : -Infinity;
    const rightNumber = Number.isFinite(rightValue) ? rightValue : -Infinity;
    result = leftNumber - rightNumber;
  }
  return state.sortDirection === "asc" ? result : -result;
}

function updateSortHeaders() {
  document.querySelectorAll("th[data-sort]").forEach((header) => {
    header.classList.toggle("sorted-asc", header.dataset.sort === state.sortKey && state.sortDirection === "asc");
    header.classList.toggle("sorted-desc", header.dataset.sort === state.sortKey && state.sortDirection === "desc");
  });
}

function updateValueAxisControls() {
  dom.axisReturn.classList.toggle("secondary", state.valueAxisMode !== "return");
  dom.axisMultiple.classList.toggle("secondary", state.valueAxisMode !== "multiple");
  dom.axisLog.classList.toggle("secondary", state.valueAxisMode !== "log");
}

function setValueAxisMode(mode) {
  state.valueAxisMode = Object.prototype.hasOwnProperty.call(VALUE_AXIS_MODES, mode) ? mode : "return";
  updateValueAxisControls();
  renderAll();
}

function renderErrors() {
  const errors = state.payload.errors || [];
  dom.errorsSection.hidden = !errors.length;
  dom.errors.innerHTML = errors.map((item) => `${item.name}: ${item.error}`).join("<br>");
}

function instrumentByCode(code) {
  return state.payload.instruments.find((item) => item.code === code) || { name: code, color: "#555" };
}

function applyQuickRange(kind, value) {
  const bounds = currentBounds();
  if (!bounds) return;
  let start = bounds.start;
  let end = bounds.end;
  if (kind === "years") {
    start = Math.max(bounds.start, end - Number(value) * 365.25 * MS_DAY);
  } else if (kind === "since") {
    start = Math.max(bounds.start, parseDate(value));
  }
  setActiveRange(start, end);
}

function panActiveRange(direction, fraction = 0.35) {
  const range = activeRange();
  if (!range) return;
  const span = range.end - range.start;
  const shift = span * fraction * direction;
  setActiveRange(range.start + shift, range.end + shift);
}

function zoomActiveRange(factor) {
  const range = activeRange();
  if (!range) return;
  const center = (range.start + range.end) / 2;
  const span = Math.max((range.end - range.start) * factor, 20 * MS_DAY);
  setActiveRange(center - span / 2, center + span / 2);
}

function setRangeMode(mode) {
  state.rangeMode = mode === "longest" ? "longest" : "common";
  dom.modeCommon.classList.toggle("secondary", state.rangeMode !== "common");
  dom.modeLongest.classList.toggle("secondary", state.rangeMode !== "longest");
  setRangeToCurrentMode();
  renderAll();
}

function svgPointer(svg, event) {
  const point = svg.createSVGPoint();
  point.x = event.clientX;
  point.y = event.clientY;
  return point.matrixTransform(svg.getScreenCTM().inverse());
}

function installChartPan() {
  const svg = dom.valueChart;
  svg.addEventListener("pointerdown", (event) => {
    const range = activeRange();
    if (!range) return;
    const point = svgPointer(svg, event);
    const plot = VALUE_BOX.plot;
    const plotRight = VALUE_BOX.width - plot.right;
    const plotBottom = VALUE_BOX.height - plot.bottom;
    if (point.x < plot.left || point.x > plotRight || point.y < plot.top || point.y > plotBottom) return;
    state.drag = { startX: point.x, currentX: point.x, range };
    svg.classList.add("dragging");
    svg.setPointerCapture(event.pointerId);
  });
  svg.addEventListener("pointermove", (event) => {
    if (!state.drag) return;
    const point = svgPointer(svg, event);
    const plot = VALUE_BOX.plot;
    const plotRight = VALUE_BOX.width - plot.right;
    const x = Math.max(plot.left, Math.min(plotRight, point.x));
    state.drag.currentX = x;
  });
  svg.addEventListener("pointerup", () => {
    if (!state.drag) return;
    const plot = VALUE_BOX.plot;
    const width = VALUE_BOX.width - plot.left - plot.right;
    const deltaX = state.drag.currentX - state.drag.startX;
    const range = state.drag.range;
    svg.classList.remove("dragging");
    state.drag = null;
    if (Math.abs(deltaX) < 8) return;
    const span = range.end - range.start;
    const shift = -(deltaX / Math.max(width, 1)) * span;
    setActiveRange(range.start + shift, range.end + shift);
  });
  svg.addEventListener("pointercancel", () => {
    if (!state.drag) return;
    svg.classList.remove("dragging");
    state.drag = null;
  });
}

document.querySelectorAll("[data-range]").forEach((button) => {
  button.addEventListener("click", () => applyQuickRange("all"));
});
document.querySelectorAll("[data-years]").forEach((button) => {
  button.addEventListener("click", () => applyQuickRange("years", button.dataset.years));
});
document.querySelectorAll("[data-since]").forEach((button) => {
  button.addEventListener("click", () => applyQuickRange("since", button.dataset.since));
});
document.querySelectorAll("[data-mode]").forEach((button) => {
  button.addEventListener("click", () => setRangeMode(button.dataset.mode));
});
document.querySelectorAll("[data-y-axis]").forEach((button) => {
  button.addEventListener("click", () => setValueAxisMode(button.dataset.yAxis));
});
document.querySelectorAll("th[data-sort]").forEach((header) => {
  header.addEventListener("click", () => {
    const key = header.dataset.sort;
    if (state.sortKey === key) {
      state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
    } else {
      state.sortKey = key;
      state.sortDirection = key === "name" ? "asc" : "desc";
    }
    renderAll();
  });
});
dom.start.addEventListener("change", () => { clampInputsToCurrentMode(); renderAll(); });
dom.end.addEventListener("change", () => { clampInputsToCurrentMode(); renderAll(); });
dom.panLeft.addEventListener("click", () => panActiveRange(-1));
dom.panRight.addEventListener("click", () => panActiveRange(1));
dom.zoomIn.addEventListener("click", () => zoomActiveRange(0.5));
dom.zoomOut.addEventListener("click", () => zoomActiveRange(2));
dom.reset.addEventListener("click", () => { setRangeToCurrentMode(); renderAll(); });
dom.refresh.addEventListener("click", () => loadHistory(true));
updateValueAxisControls();
installChartPan();
loadHistory(false);
</script>
</body>
</html>"""
    page = page.replace("__TOP_PANEL__", top_panel_html)
    return _inject_unified_shell(page)



def render_strategy_index_compare_page() -> str:
    page = render_etf_compare_page(top_panel_html=_strategy_calmar_panel_html())
    replacements = {
        "ETF 复权对比 - MyInvestStrategyIndex": "策略指数对比 - MyInvestStrategyIndex",
        "ETF 复权价值曲线对比": "策略指数收益曲线对比",
        "日线复权口径": "全收益指数口径",
        "/api/etf-compare/history.json": "/api/strategy-index-compare/history.json",
        "<body>": (
            '<body data-api-path="/api/strategy-index-compare/history.json" data-extra-metrics="true" '
            'data-synthetic-code="VIRTUAL_EQUAL_WEIGHT_STRATEGY" '
            'data-risk-parity-code="VIRTUAL_RISK_PARITY_STRATEGY" data-anchor-synthetic="false" '
            'data-show-background="true" data-longest-mode-label="最早起" '
            'data-longest-base-text="当前指数自身起点=0%；上证指数作灰色背景参考">'
        ),
        (
            "2012起模式按最早可用 ETF 开始展示；后上市 ETF 从上市日对应的虚拟等权ETF位置接上。"
            "虚拟等权ETF按 512890、510500、510300、159915 四只真实 ETF 中当日已有数据的成分动态等权；"
            "480092 为自由现金流R收益指数点位代理。"
        ): (
            "最早起模式按最早可用指数开始展示。策略指数页对比国信价值全收益、创成长R、"
            "红利低波全收益、自由现金流R、华安黄金ETF和十年国债ETF，并提供当前勾选成分的"
            "策略等权组合和滚动60日风险平价组合，以及Calmar全样本最优分层权重模型；"
            "分层模型权重为国信价值0%、创成长R11.13%、红利低波0%、自由现金流R25.22%、"
            "黄金ETF23.64%、十年国债ETF40.00%；样本外70/30验证输给等权，仅作参考。"
            "上证指数作为灰色背景线，仅用于观察市场背景，不参与指标排序。"
        ),
        "2012起": "最早起",
        "复权价值曲线": "策略指数曲线",
        '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>': (
            '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>\n'
            '                <th data-sort="longestRecoveryDays">最长回本时间</th>\n'
            '                <th data-sort="rollingThreeYearWorstReturn">滚动3年最差收益</th>'
        ),
    }
    for old, new in replacements.items():
        page = page.replace(old, new)
    return page


def render_chinext_compare_page() -> str:
    page = render_etf_compare_page(top_panel_html=_chinext_intro_panel_html())
    replacements = {
        "ETF 复权对比 - MyInvestStrategyIndex": "创业板全收益指数对比 - MyInvestStrategyIndex",
        "ETF 复权价值曲线对比": "创业板全收益指数对比",
        "日线复权口径": "全收益指数口径",
        "/api/etf-compare/history.json": "/api/chinext-compare/history.json",
        "<body>": (
            '<body data-api-path="/api/chinext-compare/history.json" data-extra-metrics="true" '
            'data-anchor-synthetic="false" data-show-background="false" '
            'data-longest-mode-label="最早起" data-longest-base-text="当前指数自身起点=0%">'
        ),
        (
            "2012起模式按最早可用 ETF 开始展示；后上市 ETF 从上市日对应的虚拟等权ETF位置接上。"
            "虚拟等权ETF按 512890、510500、510300、159915 四只真实 ETF 中当日已有数据的成分动态等权；"
            "480092 为自由现金流R收益指数点位代理。"
        ): (
            "最早起模式按最早可用全收益指数开始展示。创业板页对比 399006 创业板指、"
            "399673 创业板50、399296 创成长三个指数的全收益版本；实际数据源分别为 "
            "399606.SZ、CN2673.CNI、CN2296.CNI。"
        ),
        "2012起": "最早起",
        "复权价值曲线": "全收益指数曲线",
        '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>': (
            '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>\n'
            '                <th data-sort="longestRecoveryDays">最长回本时间</th>\n'
            '                <th data-sort="rollingThreeYearWorstReturn">滚动3年最差收益</th>'
        ),
    }
    for old, new in replacements.items():
        page = page.replace(old, new)
    return page


def render_four_asset_compare_page() -> str:
    page = render_etf_compare_page(top_panel_html=_four_asset_calmar_panel_html())
    replacements = {
        "ETF 复权对比 - MyInvestStrategyIndex": "四资产组合对比 - MyInvestStrategyIndex",
        "ETF 复权价值曲线对比": "四资产组合对比",
        "日线复权口径": "全收益/复权口径",
        "/api/etf-compare/history.json": "/api/four-asset-compare/history.json",
        "<body>": (
            '<body data-api-path="/api/four-asset-compare/history.json" data-extra-metrics="true" '
            'data-synthetic-code="VIRTUAL_FOUR_ASSET_EQUAL_WEIGHT" '
            'data-anchor-synthetic="false" data-show-background="false" '
            'data-longest-mode-label="最早起" data-longest-base-text="当前标的自身起点=0%">'
        ),
        (
            "2012起模式按最早可用 ETF 开始展示；后上市 ETF 从上市日对应的虚拟等权ETF位置接上。"
            "虚拟等权ETF按 512890、510500、510300、159915 四只真实 ETF 中当日已有数据的成分动态等权；"
            "480092 为自由现金流R收益指数点位代理。"
        ): (
            "最早起模式按四个真实标的的最早可用数据开始展示。四资产页对比创业板R、"
            "自由现金流R、华安黄金ETF、十年国债ETF，并加入四资产等权组合和 Calmar "
            "全样本最优分层权重模型。"
        ),
        "2012起": "最早起",
        "复权价值曲线": "四资产组合曲线",
        '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>': (
            '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>\n'
            '                <th data-sort="longestRecoveryDays">最长回本时间</th>\n'
            '                <th data-sort="rollingThreeYearWorstReturn">滚动3年最差收益</th>'
        ),
    }
    for old, new in replacements.items():
        page = page.replace(old, new)
    return page


def render_three_asset_compare_page() -> str:
    page = render_etf_compare_page(top_panel_html=_three_asset_calmar_panel_html())
    replacements = {
        "ETF 复权对比 - MyInvestStrategyIndex": "三资产组合对比 - MyInvestStrategyIndex",
        "ETF 复权价值曲线对比": "三资产组合对比",
        "日线复权口径": "全收益/复权口径",
        "/api/etf-compare/history.json": "/api/three-asset-compare/history.json",
        "<body>": (
            '<body data-api-path="/api/three-asset-compare/history.json" data-extra-metrics="true" '
            'data-synthetic-code="VIRTUAL_THREE_ASSET_EQUAL_WEIGHT" '
            'data-anchor-synthetic="false" data-show-background="false" '
            'data-longest-mode-label="最早起" data-longest-base-text="当前标的自身起点=0%" '
            'data-default-start-date="2017-08-24">'
        ),
        (
            "2012起模式按最早可用 ETF 开始展示；后上市 ETF 从上市日对应的虚拟等权ETF位置接上。"
            "虚拟等权ETF按 512890、510500、510300、159915 四只真实 ETF 中当日已有数据的成分动态等权；"
            "480092 为自由现金流R收益指数点位代理。"
        ): (
            "最早起模式按三个真实标的的最早可用数据开始展示。三资产页对比创业板R、"
            "自由现金流R、华安黄金ETF，并加入三资产等权组合和 Calmar 全样本最优分层权重模型。"
        ),
        "2012起": "最早起",
        "复权价值曲线": "三资产组合曲线",
        '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>': (
            '<th data-sort="annualizedReturnDrawdownRatio" class="sorted-desc">年化收益/最大回撤</th>\n'
            '                <th data-sort="longestRecoveryDays">最长回本时间</th>\n'
            '                <th data-sort="rollingThreeYearWorstReturn">滚动3年最差收益</th>'
        ),
    }
    for old, new in replacements.items():
        page = page.replace(old, new)
    return page


def render_value_compare_page() -> str:
    return render_strategy_index_compare_page()



if __name__ == "__main__":
    raise SystemExit(main())
