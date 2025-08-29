
from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timezone
import yfinance as yf

app = Flask(__name__, static_folder="static")

USD_SAR = 3.75  # fixed as requested

# Baseline holdings (can be edited from the UI and saved to browser)
BASELINE = [
    {"name_ar": "الإنماء", "symbol": "1150.SR", "qty": 303, "total_cost": 8364.02, "avg": 27.6, "type": "tadawul"},
    {"name_ar": "سابك", "symbol": "2010.SR", "qty": 79, "total_cost": 5083.43, "avg": 64.4, "type": "tadawul"},
    {"name_ar": "أرامكو", "symbol": "2222.SR", "qty": 267, "total_cost": 7015.91, "avg": 26.3, "type": "tadawul"},
    {"name_ar": "المواساة", "symbol": "4002.SR", "qty": 8, "total_cost": 591.41, "avg": 73.9, "type": "tadawul"},
    {"name_ar": "بنيان ريت", "symbol": "4347.SR", "qty": 371, "total_cost": 3472.33, "avg": 9.36, "type": "tadawul"},
    {"name_ar": "الاتصالات السعودية", "symbol": "7010.SR", "qty": 205, "total_cost": 8225.74, "avg": 40.1, "type": "tadawul"},
    {"name_ar": "الحلول الذكية", "symbol": "7202.SR", "qty": 27, "total_cost": 7467.35, "avg": 276.6, "type": "tadawul"},

    {"name_ar": "صندوق الأهلي السنبلة", "symbol": "", "qty": 96.6994, "total_cost": 13000.0, "avg": 134.4, "type": "nav_manual"},
    {"name_ar": "الصندوق الأمريكي الإسلامي", "symbol": "SPUS", "qty": 39.64, "total_cost": 5959.0, "avg": None, "type": "us_etf"},

    {"name_ar": "مقيلا (فلل)", "symbol": "", "qty": None, "market_value": 6000.0, "type": "fixed"},
    {"name_ar": "الإنماء الادخاري", "symbol": "", "qty": None, "market_value": 11823.0, "type": "cash"}
]

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)

def fetch_price_yf(symbol: str):
    if not symbol:
        return None
    t = yf.Ticker(symbol)
    price = None
    # fast_info
    try:
        fi = getattr(t, "fast_info", None)
        if fi:
            price = getattr(fi, "last_price", None)
    except Exception:
        pass
    # info fallback
    if price is None:
        try:
            info = t.info
            price = info.get("regularMarketPrice")
        except Exception:
            pass
    # history fallback
    if price is None:
        try:
            hist = t.history(period="1d", interval="1m")
            if not hist.empty:
                price = float(hist["Close"].iloc[-1])
        except Exception:
            pass
    try:
        return None if price is None else float(price)
    except Exception:
        return None

@app.route("/api/summary", methods=["POST"])
def summary():
    """
    Accepts optional JSON: {"holdings": [...], "sunbullah_nav": <float or null>}
    Returns computed rows & totals.
    """
    data = request.get_json(force=True, silent=True) or {}
    holdings = data.get("holdings") or BASELINE
    sunbullah_nav = data.get("sunbullah_nav")  # optional manual NAV
    usd_sar = float(data.get("usd_sar") or 3.75)

    rows = []
    total_mkt = 0.0
    total_cost = 0.0
    total_zakat = 0.0

    for h in holdings:
        typ = h.get("type")
        name = h.get("name_ar") or h.get("symbol") or "—"
        qty = h.get("qty")
        avg = h.get("avg")
        total_cost_item = h.get("total_cost") or 0.0
        symbol = h.get("symbol", "")

        price = None
        market_value = None
        pl = None
        zakat = None

        if typ == "tadawul":
            price = fetch_price_yf(symbol)  # SAR
            if price is not None and qty:
                market_value = price * qty
                total_mkt += market_value
            if market_value is not None:
                total_cost += total_cost_item
                pl = market_value - total_cost_item

        elif typ == "nav_manual":
            # Sunbullah: manual NAV if provided, else leave None (use cost as current value baseline)
            if sunbullah_nav is not None and qty:
                price = float(sunbullah_nav)  # per unit (SAR)
                market_value = price * qty
            else:
                # fallback to cost as current approximation
                market_value = float(total_cost_item)
            total_mkt += market_value
            total_cost += total_cost_item
            pl = market_value - total_cost_item
            zakat = market_value * 0.025  # only funds

        elif typ == "us_etf":
            # SPUS in USD -> convert to SAR per unit
            spus_usd = fetch_price_yf(symbol)  # per unit in USD
            if spus_usd is not None:
                price = float(spus_usd) * usd_sar  # unit in SAR
            if price is not None and qty:
                market_value = price * qty
                total_mkt += market_value
                total_cost += total_cost_item  # total_cost already SAR per user preference
                pl = market_value - total_cost_item
                zakat = market_value * 0.025  # zakat applies

        elif typ == "fixed" or typ == "cash":
            market_value = float(h.get("market_value") or 0.0)
            total_mkt += market_value
            # no PL for fixed cash/investments without cost basis

        rows.append({
            "name": name,
            "qty": qty,
            "avg": avg,
            "price": price,  # for SPUS we will render without "ريال"
            "market_value": market_value,
            "pl": pl,
            "zakat": zakat,
            "type": typ,
        })

    if total_cost == 0:
        total_pl = None
        pct = None
    else:
        total_pl = total_mkt - total_cost
        pct = (total_pl / total_cost) * 100.0

    return jsonify({
        "rows": rows,
        "totals": {
            "market_value": total_mkt,
            "total_cost": total_cost,
            "pl": total_pl,
            "pl_pct": pct,
            "zakat": total_zakat  # (we didn't sum zakat above per-row; front-end will sum)
        },
        "meta": {
            "time": datetime.now(timezone.utc).isoformat(),
            "usd_sar": usd_sar
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
