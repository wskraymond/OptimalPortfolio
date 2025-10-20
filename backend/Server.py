from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
    return jsonify(BETAS)

@app.get("/api/tangent")
def tangent():
    return jsonify(TANGENT_WEIGHTS)

@app.get("/api/risk")
def risk():
    return jsonify(RISK_METRICS)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
