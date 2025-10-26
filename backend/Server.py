from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from analytics.Analyzer import RollingPortfolioAnalyzer
from analytics.Allocation import Allocation

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# --- Mock data (replace with your real sources) ---
POSITIONS = [
    {"Ticker": "2840.hk", "MarketValue": 6795, "Beta": 0.0884,
     "Qty": 100, "Price": 67.95, "Position": "Long", "Input": "Manual"},
    {"Ticker": "159919.SZ", "MarketValue": 0, "Beta": 0.1574,
     "Qty": 0, "Price": 0.0, "Position": "None", "Input": "Manual"},
    {"Ticker": "0001.HK", "MarketValue": 60100, "Beta": 0.2708,
     "Qty": 2000, "Price": 30.05, "Position": "Long", "Input": "Manual"},
    {"Ticker": "9988.HK", "MarketValue": 21020, "Beta": 0.1075,
     "Qty": 100, "Price": 210.20, "Position": "Long", "Input": "Manual"},
    {"Ticker": "DBC", "MarketValue": 0, "Beta": 0.4531,
     "Qty": 0, "Price": 0.0, "Position": "None", "Input": "Manual"},
    {"Ticker": "2800.HK", "MarketValue": 0, "Beta": 0.2120,
     "Qty": 0, "Price": 0.0, "Position": "None", "Input": "Manual"},
    {"Ticker": "BIDU", "MarketValue": 772, "Beta": 1.1677,
     "Qty": 2, "Price": 386.0, "Position": "Long", "Input": "Manual"},
    {"Ticker": "BRK-B", "MarketValue": 13162, "Beta": 0.9599,
     "Qty": 40, "Price": 329.05, "Position": "Long", "Input": "Manual"},
    {"Ticker": "REET", "MarketValue": 2820, "Beta": 0.5240,
     "Qty": 100, "Price": 28.20, "Position": "Long", "Input": "Manual"},
    {"Ticker": "ARKK", "MarketValue": 549, "Beta": 0.7705,
     "Qty": 10, "Price": 54.90, "Position": "Long", "Input": "Manual"},
    {"Ticker": "LIT", "MarketValue": 3389, "Beta": 1.1033,
     "Qty": 50, "Price": 67.78, "Position": "Long", "Input": "Manual"},
    {"Ticker": "SPY", "MarketValue": 0, "Beta": 1.0,
     "Qty": 0, "Price": 0.0, "Position": "None", "Input": "Manual"},
]


TICKERS = [p["Ticker"] for p in POSITIONS]

# Symmetric 12x12 correlation matrix (example values aligned with your sheet)
CORRELATION = [
    # 2840.hk, 159919.SZ, 0001.HK, 9988.HK, DBC, 2800.HK, BIDU, BRK-B, REET, ARKK, LIT, SPY
    [1, -0.027688, 0.009325, 0.106217, -0.004510, 0.013533, -0.001472, -0.009754, 0.126270, 0.057053, 0.020512, -0.008254],
    [-0.027688, 1, 0.289229, 0.362027, 0.143085, 0.524068, 0.212292, 0.116542, 0.113555, 0.168402, 0.271474, 0.160092],
    [0.009325, 0.289229, 1, 0.258301, 0.173619, 0.674857, 0.184173, 0.128015, 0.217914, 0.188740, 0.261469, 0.196027],
    [0.106217, 0.362027, 0.258301, 1, 0.166267, 0.473204, 0.263351, 0.224549, 0.242531, 0.204875, 0.293678, 0.218243],
    [-0.004510, 0.143085, 0.173619, 0.166267, 1, 0.189198, 0.285135, 0.357890, 0.338729, 0.314345, 0.463547, 0.481208],
    [0.013533, 0.524068, 0.674857, 0.473204, 0.189198, 1, 0.241759, 0.102473, 0.134427, 0.200022, 0.316060, 0.183992],
    [-0.001472, 0.212292, 0.184173, 0.263351, 0.285135, 0.241759, 1, 0.354890, 0.315488, 0.508313, 0.481093, 0.496408],
    [-0.009754, 0.116542, 0.128015, 0.224549, 0.357890, 0.102473, 0.354890, 1, 0.637524, 0.476615, 0.605731, 0.817010],
    [0.126270, 0.113555, 0.217914, 0.242531, 0.338729, 0.134427, 0.315488, 0.637524, 1, 0.494090, 0.574175, 0.745230],
    [0.057053, 0.168402, 0.188740, 0.204875, 0.314345, 0.200022, 0.508313, 0.476615, 0.494090, 1, 0.661376, 0.725753],
    [0.020512, 0.271474, 0.261469, 0.293678, 0.463547, 0.316060, 0.481093, 0.605731, 0.574175, 0.661376, 1, 0.754533],
    [-0.008254, 0.160092, 0.196027, 0.218243, 0.481208, 0.183992, 0.496408, 0.817010, 0.745230, 0.725753, 0.754533, 1],
]

BETAS = {p["Ticker"]: p["Beta"] for p in POSITIONS}

TANGENT_WEIGHTS = {
    # From your tangentPortfolio section (others are ~0)
    "BRK-B": 0.37639471300157801,
    "DBC": 0.35648312666953402,
    "REET": 0.17925537350522699,
    "0001.HK": 0.0878667868240567,
    "SPY": 1.22312709548329e-14,
    "2800.HK": 7.879778101717300e-16
}

RISK_METRICS = {
    "Sharpe Ratio": 0.85,
    "Treynor Ratio": 0.12,
    "Portfolio Return(%)": 8.5,
    "Portfolio Risk(%)": 12.3,
    "Value At Risk": -5.2,
    "Systematic Risk": 7.9,
    "Non-Systematic Risk": 9.8,
    "M^2 Alpha": 0.6,
    "Leverage Ratio": 1.5
}

from flask import request

@app.post("/api/update_input")
def update_input():
    data = request.json  # expects {"Ticker": "0001.HK", "Input": "NewValue"}
    ticker = data.get("Ticker")
    new_input = data.get("Input")

    # Update in-memory POSITIONS list
    for p in POSITIONS:
        if p["Ticker"] == ticker:
            p["Input"] = new_input
            break

    return jsonify({"status": "success", "updated": {"Ticker": ticker, "Input": new_input}})


@app.get("/api/positions")
def positions():
    return jsonify(POSITIONS)

@app.get("/api/correlation")
def correlation():
    return jsonify({"tickers": TICKERS, "matrix": CORRELATION, "weighted_hpr": {
            "2840.hk": 0.0883636,
            "159919.SZ": 0.1574364,
            "0001.HK": 0.2708308,
            "9988.HK": 0.1074900,
            "DBC": 0.4530765,
            "2800.HK": 0.2119516,
            "BIDU": 1.1676715,
            "BRK-B": 0.9598599,
            "REET": 0.5240434,
            "ARKK": 0.7704677,
            "LIT": 1.1032598,
            "SPY": 1.0
        }})

@app.get("/api/betas")
def betas():
    # Parameters (mocked for now)
    Rf = 0.0037   # 1-year T-bill log return ≈ 0.37%
    Rm = 0.08     # Assume 8% expected market return

    total_mv = sum(p["MarketValue"] for p in POSITIONS)
    results = {}
    portfolio_beta = 0
    portfolio_alpha = 0

    for p in POSITIONS:
        ticker = p["Ticker"]
        beta = p["Beta"]
        weight = p["MarketValue"] / total_mv if total_mv > 0 else 0

        # CAPM expected return
        capm_er = Rf + beta * (Rm - Rf)

        # For now, mock actual return as weight * 10% (replace with real data)
        actual_return = 0.10 * weight
        alpha = actual_return - capm_er

        weighted_beta = beta * weight

        results[ticker] = {
            "beta": beta,
            "weighted_beta": weighted_beta,
            "capm_er": capm_er,
            "alpha": alpha
        }

        portfolio_beta += weighted_beta
        portfolio_alpha += alpha * weight

    results["portfolio"] = {
        "beta": portfolio_beta,
        "alpha": portfolio_alpha
    }

    return jsonify(results)


@app.get("/api/tangent")
def tangent():
    return jsonify(TANGENT_WEIGHTS)

import math
import numpy as np

@app.get("/api/risk")
def risk():
    Rf = 0.0037  # 1-year T-bill log return
    portfolio_return = 0.022805504  # from Excel
    total_cov = 0.019739749
    non_sys_var = 0.004066145
    sys_var = 0.013918029
    portfolio_beta = 0.4869

    portfolio_risk = math.sqrt(total_cov)
    non_sys_risk = math.sqrt(non_sys_var)
    sys_risk = math.sqrt(sys_var)

    sharpe = (portfolio_return - Rf) / portfolio_risk
    treynor = (portfolio_return - Rf) / portfolio_beta

    # VaR at 95% and 99%
    z95, z99 = 1.644854, 2.326348
    portfolio_value = sum(p["MarketValue"] for p in POSITIONS)
    var95 = -z95 * portfolio_risk * portfolio_value
    var99 = -z99 * portfolio_risk * portfolio_value

    return jsonify({
        "Total Covariance": total_cov,
        "Portfolio Risk(%)": portfolio_risk * 100,
        "Non-Systematic Var": non_sys_var,
        "Non-Systematic Risk(%)": non_sys_risk * 100,
        "Systematic Var": sys_var,
        "Systematic Risk(%)": sys_risk * 100,
        "Portfolio Return(%)": portfolio_return * 100,
        "Sharpe Ratio": sharpe,
        "Treynor Ratio": treynor,
        "Value At Risk 95%": var95,
        "Value At Risk 99%": var99
    })

SUPPORTED_CMDS = {
    "div": "run_div",
    "o": "run_optimal",
    "o_avg": "run_optimal_avg",
    "corr": "run_corr",
    "corr_3d": "run_corr_3d",
    "ewm_corr_avg": "run_ewm_corr_avg",
    "alpha": "run_alpha",
    "alpha_avg": "run_alpha_avg",
    "beta_avg": "run_beta_avg",
    "var": "run_var",
    "ewm_var": "run_ewm_var",
    "std": "run_std",
    "std_avg": "run_std_avg",
}

@socketio.on("run_analysis")
def handle_run_analysis(data):
    """
    data is expected to be a dict like:
    {
        "cmd": "div",
        "args": {
            "startdate": "01/05/2015",
            "holdingPeriodYear": 0.25,
            "rollingYr": 5,
            "divTaxRate": 0.3
        }
    }
    """
    cmd = data.get("cmd")
    if cmd not in SUPPORTED_CMDS:
        emit("analysis_result", {"error": f"Unsupported command {cmd}"})
        return

    args = data.get("args", {})
    startdate = args.get("startdate", "01/05/2015")
    holdingPeriodYear = float(args.get("holdingPeriodYear", 0.25))
    rollingYr = float(args.get("rollingYr", 5))
    divTaxRate = float(args.get("divTaxRate", 0.3))

    analyzer = RollingPortfolioAnalyzer(
        startdate=startdate,
        holdingPeriodYear=holdingPeriodYear,
        rollingYr=rollingYr,
        divTaxRate=divTaxRate
    )

    method = getattr(analyzer, SUPPORTED_CMDS[cmd])
    result = method()

    # Push result back to the client
    emit("analysis_result", result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
