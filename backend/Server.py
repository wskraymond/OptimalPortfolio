from flask import Flask, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from analytics.Analyzer import RollingPortfolioAnalyzer
from analytics.Allocation import Allocation
from data.contract.MyContract import contractList
from data.store import Store
import pandas as pd
import numpy as np
from ibapi.contract import Contract

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")
store_host = 'host.docker.internal'
store = Store(hosts=[store_host], keyspace='store')


from flask import request

@app.post("/api/update_input")
def update_input():
    data = request.json  # expects {"Ticker": "0001.HK", "Input": "NewValue"}
    ticker = data.get("Ticker")
    new_input = data.get("Input")

    # Update in-memory POSITIONS list


    return jsonify({"status": "success", "updated": {"Ticker": ticker, "Input": new_input}})


@app.get("/api/positions")
def positions():
    df = store.select_portfolio_in_pd()
    if df.empty:
        return jsonify([])

    # Map to mock-style fields
    records = []
    for _, row in df.iterrows():
        records.append({
            "Ticker": row.name,  # ticker is index
            "MarketValue": row.get("market_value", 0),
            "Beta": row.get("beta", None),  # if you store beta in Portfolio or compute separately
            "Qty": row.get("qty", 0),
            "Price": row.get("price", 0.0),
            "Position": row.get("position_type", "None"),
            "Input": row.get("input", "Manual")  # default if not stored
        })
    return jsonify(records)


@app.get("/api/covariance")
def covariance():
    alloc = Allocation(analyzer.stats, analyzer.stats.returns, analyzer.stats.div_return)
    alloc.preload()

    # Portfolio weights
    df = store.select_portfolio_in_pd()
    total_mv = df["market_value"].sum()
    weights = df["market_value"] / total_mv if total_mv > 0 else 0

    # Canonical ticker order = covariance matrix index
    tickers = list(alloc.cov.index)

    # Weighted covariance matrix
    weights = weights.reindex(tickers).fillna(0)
    weighted_cov = alloc.weighted_cov(weights)
    print("weighted_cov=", weighted_cov)


    # HPR series aligned to tickers
    hpr_series = pd.Series(alloc.hpr, index=analyzer.stats.recvTickers)
    hpr_series = hpr_series.reindex(tickers).fillna(0)

    weighted_hpr_series = hpr_series * weights

    return jsonify({
        "tickers": tickers,
        "matrix": weighted_cov.loc[tickers, tickers].values.tolist(),
        "weighted_hpr": weighted_hpr_series.to_dict(),
        "portfolio_hpr": float(weighted_hpr_series.sum())
    })


@app.get("/api/betas")
def betas():
    result = analyzer.run_alpha(benchmark="VOO")

    betas_dict = result["beta"]   # {benchmark: {ticker: slope}}
    alphas_dict = result["alpha"] # {ticker: alpha}
    capm_dict = result["CAPM"]    # {ticker: CAPM expected return}

    # Flatten betas properly
    flat_betas = betas_dict.get("VOO", {})

    # Portfolio weights
    df = store.select_portfolio_in_pd()
    total_mv = df["market_value"].sum()
    weights = df["market_value"] / total_mv if total_mv > 0 else 0

    # Portfolio aggregates
    portfolio_beta = sum(weights.get(t, 0) * b for t, b in flat_betas.items())
    portfolio_alpha = sum(weights.get(t, 0) * a for t, a in alphas_dict.items())

    # Build nested dict per ticker
    tickers = {}
    for t in flat_betas:
        tickers[t] = {
            "beta": flat_betas[t],
            "capm_er": capm_dict.get(t, 0),
            "alpha": alphas_dict.get(t, 0)
        }

    # Add portfolio summary row
    tickers["portfolio"] = {
        "beta": portfolio_beta,
        "alpha": portfolio_alpha
    }

    return jsonify(tickers)



@app.get("/api/tangent")
def tangent():
    """Optimal tangent portfolio weights using Allocation"""
    alloc = Allocation(analyzer.stats, analyzer.stats.returns, analyzer.stats.div_return)
    alloc.preload()
    alloc.optimize()
    return jsonify(alloc.get_allocation())

import math
import numpy as np

@app.get("/api/risk")
def risk():
    alloc = Allocation(analyzer.stats, analyzer.stats.returns, analyzer.stats.div_return)
    alloc.preload()

    # Portfolio weights
    df = store.select_portfolio_in_pd()
    weights = df["market_value"] / df["market_value"].sum()
    portfolio_value = df["market_value"].sum()
    weights = weights.reindex(alloc.cov.columns).fillna(0).values

    # Use Allocation’s built-in function
    ret, vol, sr = alloc.gen_ret_vol_sr_func()(weights)

    # Portfolio beta
    benchmark = "VOO"
    beta_alpha = analyzer.run_alpha(benchmark=benchmark)
    flat_betas = beta_alpha["beta"].get(benchmark, {})
    portfolio_beta = sum(
        (df["market_value"].get(t, 0) / portfolio_value) * b
        for t, b in flat_betas.items()
    )

    # Systematic / non-systematic decomposition
    market_var = alloc.var.loc[benchmark, benchmark]
    sys_var = (portfolio_beta ** 2) * market_var
    non_sys_var = (vol ** 2) - sys_var
    sys_risk = math.sqrt(sys_var) if sys_var > 0 else 0
    non_sys_risk = math.sqrt(non_sys_var) if non_sys_var > 0 else 0

    # Treynor ratio
    Rf = alloc.single_period_margin_rate
    treynor = (ret - Rf) / portfolio_beta if portfolio_beta else None

    # Value at Risk
    z95, z99 = 1.645, 2.326
    var95 = -z95 * vol * portfolio_value
    var99 = -z99 * vol * portfolio_value

    # --- M² Alpha ---
    M2, M2_alpha = alloc.calc_period_m2_alpha(weights, benchmark=benchmark)

    return jsonify({
        "Total Covariance": float(weights.T @ alloc.cov.values @ weights),
        "Portfolio Risk(%)": vol * 100,
        "Non-Systematic Var": non_sys_var,
        "Non-Systematic Risk(%)": non_sys_risk * 100,
        "Systematic Var": sys_var,
        "Systematic Risk(%)": sys_risk * 100,
        "Portfolio Return(%)": ret * 100,
        "Sharpe Ratio": sr,
        "Treynor Ratio": treynor,
        "M2": M2,
        "M2 Alpha": M2_alpha,
        "Value At Risk 95%": var95,
        "Value At Risk 99%": var99
    })

@app.post("/api/update_params")
def update_params():
    data = request.get_json()
    startdate = data.get("startdate", "01/01/2020")
    holdingPeriodYear = float(data.get("holdingPeriodYear", 1))
    rollingYr = float(data.get("rollingYr", 5))
    divTaxRate = float(data.get("divTaxRate", 0.3))

    init_analyzer(startdate, holdingPeriodYear, rollingYr, divTaxRate)
    return jsonify({"status": "analyzer reinitialized"})




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
        divTaxRate=divTaxRate,
        store=store
    )

    method = getattr(analyzer, SUPPORTED_CMDS[cmd])
    result = method()

    # Push result back to the client
    emit("analysis_result", result)

# Create contract from portfolio row
def create_contract_from_portfolio_row(row):
    contract = Contract()
    contract.symbol = row.name  # 'ticker' is set as index in DataFrame
    contract.secType = "STK"
    contract.currency = row['currency']['code']
    return contract

# Global analyzer instance
analyzer = None

def init_analyzer(startdate="01/01/2020", holdingPeriodYear=1, rollingYr=5, divTaxRate=0.3):
    global analyzer
    analyzer = RollingPortfolioAnalyzer(
        startdate=startdate,
        holdingPeriodYear=holdingPeriodYear,
        rollingYr=rollingYr,
        divTaxRate=divTaxRate,
        store=store
    )

def pre_start_init():
    print("Initializing resources...")
    # Append first portfolio contract to global list
    global contractList
    portfolio_list = store.select_portfolio_in_pd()
    if not portfolio_list.empty:
        for _, row in portfolio_list.iterrows():
            contract = create_contract_from_portfolio_row(row)
            contractList.append(contract)


    print("contractList=", contractList)
    # Load config, connect to DB, etc.

    init_analyzer()

if __name__ == "__main__":
    pre_start_init()
    app.run(host="0.0.0.0", port=5000, debug=True)
