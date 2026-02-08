"""
backtest_engine.py

Requirements:
  - duckdb
  - polars
  - python-dateutil

This script:
  - Initializes DuckDB schema (prices, dividends, transactions, holdings, portfolio_monthly)
  - Runs a monthly backtest loop:
      * applies dividends (realized PnL -> cash)
      * applies periodic contributions
      * DCA buys limited by dca_rate
      * band-based rebalancing (sell excess)
      * records transactions, holdings snapshots, and monthly portfolio metrics
  - Uses Polars to compute monthly returns, covariance, and correlation from prices
"""

from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import duckdb
import polars as pl
import math

# ---------------------------
# Database schema & helpers
# ---------------------------

def init_db(con):
    con.execute("""
    CREATE TABLE IF NOT EXISTS prices (
      date DATE,
      ticker VARCHAR,
      close DOUBLE,
      PRIMARY KEY (date, ticker)
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS dividends (
      date DATE,
      ticker VARCHAR,
      div_per_share DOUBLE
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
      ts TIMESTAMP,
      date DATE,
      ticker VARCHAR,
      side VARCHAR,       -- 'BUY'|'SELL'|'DIV'|'FEE'|'CASH_IN'|'CASH_OUT'
      qty DOUBLE,
      price DOUBLE,
      cash_delta DOUBLE,  -- negative for BUY, positive for SELL/DIV
      notes VARCHAR
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS holdings (
      date DATE,
      ticker VARCHAR,
      qty DOUBLE,
      avg_cost DOUBLE,
      market_value DOUBLE,
      unrealized_pnl DOUBLE
    );
    """)
    con.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_monthly (
      month DATE,
      cash DOUBLE,
      contribution DOUBLE,
      withdrawal DOUBLE,
      realized_pnl DOUBLE,
      unrealized_pnl DOUBLE,
      total_value DOUBLE,
      vol DOUBLE,
      sharpe DOUBLE,
      cov_json VARCHAR,
      corr_json VARCHAR
    );
    """)

# ---------------------------
# Dividend application
# ---------------------------

def apply_dividends_for_date(con, d, holdings, cash, realized_pnl_accum):
    rows = con.execute("SELECT ticker, div_per_share FROM dividends WHERE date = ?", [d]).fetchall()
    for ticker, div_ps in rows:
        qty = holdings.get(ticker, {"qty": 0.0})["qty"]
        if qty <= 0:
            continue
        cash_inflow = qty * div_ps
        cash += cash_inflow
        realized_pnl_accum += cash_inflow
        con.execute(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [datetime.now(), d, ticker, "DIV", qty, None, cash_inflow, "Dividend"]
        )
    return cash, realized_pnl_accum

# ---------------------------
# Price helper
# ---------------------------

def get_price(con, d, ticker):
    row = con.execute("SELECT close FROM prices WHERE date = ? AND ticker = ?", [d, ticker]).fetchone()
    return row[0] if row else None

# ---------------------------
# Backtest core loop
# ---------------------------

def run_backtest(
    con,
    tickers,
    target_weights,       # dict {ticker: weight}
    start_date,
    end_date,
    frequency="monthly",  # "monthly" or "quarterly"
    contribution=0.0,     # periodic cash in
    dca_rate=0.3,         # fraction of available cash to deploy per period (0..1)
    band=0.02             # rebalance band (+/-)
):
    # Initialize state
    holdings = {t: {"qty": 0.0, "avg_cost": 0.0} for t in tickers}
    cash = 0.0
    realized_pnl_accum = 0.0

    step = relativedelta(months=1) if frequency == "monthly" else relativedelta(months=3)
    d = start_date

    while d <= end_date:
        # 0) Apply dividends for this date
        cash, realized_pnl_accum = apply_dividends_for_date(con, d, holdings, cash, realized_pnl_accum)

        # 1) Contribution (cash in)
        if contribution > 0:
            cash += contribution
            con.execute(
                "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [datetime.now(), d, None, "CASH_IN", 0.0, None, contribution, "Contribution"]
            )

        # 2) Gather prices and compute market value
        prices = {t: get_price(con, d, t) for t in tickers}
        mv = sum(holdings[t]["qty"] * (prices[t] or 0.0) for t in tickers)
        total_value = mv + cash

        # 3) Compute targets and current values
        targets = {t: target_weights.get(t, 0.0) * total_value for t in tickers}
        current_vals = {t: holdings[t]["qty"] * (prices[t] or 0.0) for t in tickers}

        # 4) DCA buys with controlled spending (dca_rate fraction of cash)
        under = {t: max(0.0, targets[t] - current_vals[t]) for t in tickers}
        need_cash = sum(under.values())
        spend_budget = dca_rate * cash
        spend = min(spend_budget, need_cash, cash)

        if spend > 0 and need_cash > 0:
            for t in tickers:
                p = prices.get(t)
                if p is None or under[t] <= 0:
                    continue
                allocation = spend * (under[t] / need_cash)
                if allocation <= 0:
                    continue
                qty = allocation / p
                # Update avg cost
                q_old = holdings[t]["qty"]; c_old = holdings[t]["avg_cost"]
                q_new = q_old + qty
                c_new = ((q_old * c_old) + (qty * p)) / q_new if q_new > 0 else 0.0
                holdings[t]["qty"] = q_new; holdings[t]["avg_cost"] = c_new
                cash -= allocation
                con.execute(
                    "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    [datetime.now(), d, t, "BUY", qty, p, -allocation, "DCA"]
                )

        # 5) Rebalance: sell if weight > target + band
        total_value = sum(holdings[t]["qty"] * (prices[t] or 0.0) for t in tickers) + cash
        if total_value > 0:
            for t in tickers:
                p = prices.get(t)
                if p is None:
                    continue
                current_w = (holdings[t]["qty"] * p) / total_value
                if current_w > target_weights.get(t, 0.0) + band:
                    target_mv = target_weights.get(t, 0.0) * total_value
                    excess_mv = (holdings[t]["qty"] * p) - target_mv
                    if excess_mv > 0:
                        qty_sell = min(excess_mv / p, holdings[t]["qty"])
                        if qty_sell > 0:
                            realized = (p - holdings[t]["avg_cost"]) * qty_sell
                            realized_pnl_accum += realized
                            holdings[t]["qty"] -= qty_sell
                            cash_inflow = qty_sell * p
                            cash += cash_inflow
                            con.execute(
                                "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                [datetime.now(), d, t, "SELL", qty_sell, p, cash_inflow, "Rebalance"]
                            )

        # 6) Snapshot holdings and compute unrealized PnL
        unrealized_total = 0.0
        for t in tickers:
            p = prices.get(t)
            if p is None:
                continue
            mv_t = holdings[t]["qty"] * p
            unrl = (p - holdings[t]["avg_cost"]) * holdings[t]["qty"]
            unrealized_total += unrl
            con.execute(
                "INSERT INTO holdings VALUES (?, ?, ?, ?, ?, ?)",
                [d, t, holdings[t]["qty"], holdings[t]["avg_cost"], mv_t, unrl]
            )

        total_port_value = cash + sum(holdings[t]["qty"] * (prices[t] or 0.0) for t in tickers)
        con.execute(
            "INSERT INTO portfolio_monthly VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                d, cash, contribution, 0.0, realized_pnl_accum, unrealized_total,
                total_port_value, None, None, None, None
            ]
        )

        d = d + step

# ---------------------------
# Polars analytics
# ---------------------------

def compute_monthly_metrics(con):
    # Read prices into Polars
    prices = pl.read_database("SELECT date, ticker, close FROM prices", connection=con)
    if prices.height == 0:
        return None

    # Pivot to wide format
    prices_wide = prices.pivot(index="date", columns="ticker", values="close").sort("date")

    # Compute daily log returns
    asset_cols = [c for c in prices_wide.columns if c != "date"]
    lr_exprs = [(pl.col(c).log() - pl.col(c).shift(1).log()).alias(c) for c in asset_cols]
    log_ret = prices_wide.select(*lr_exprs, pl.col("date")).drop_nulls()

    # Aggregate to monthly log returns (sum of daily log returns approximates monthly log return)
    log_ret_m = (
        log_ret
        .with_columns(month=pl.col("date").dt.truncate("1mo"))
        .groupby("month")
        .agg(*[pl.col(c).sum().alias(c) for c in asset_cols])
        .sort("month")
    )

    if log_ret_m.height == 0:
        return None

    # Covariance and correlation
    cov_df = log_ret_m.select(asset_cols).cov()
    corr_df = log_ret_m.select(asset_cols).corr()

    # Example: compute portfolio monthly returns for latest month using weights from portfolio_monthly holdings
    # For demonstration, compute portfolio returns for each month using static weights derived from last holdings snapshot
    # (In production, derive weights per month from holdings table)
    # Here we compute portfolio returns for each month using equal weights as placeholder
    weights = [1.0 / len(asset_cols)] * len(asset_cols)
    # compute portfolio returns series
    port_returns = log_ret_m.select(asset_cols).to_numpy() @ pl.Series(weights).to_numpy()
    # convert to Polars Series
    port_returns_pl = pl.Series("port_ret", port_returns)

    vol = float(port_returns_pl.std()) if port_returns_pl.len() > 1 else None
    mean = float(port_returns_pl.mean()) if port_returns_pl.len() > 0 else None
    sharpe = (mean / vol) if (vol and vol != 0) else None

    # Return serialized cov/corr and metrics
    return {
        "cov_df": cov_df,
        "corr_df": corr_df,
        "vol": vol,
        "sharpe": sharpe
    }

# ---------------------------
# Demo / Example usage
# ---------------------------

def seed_example_data(con):
    # Simple synthetic price series for three tickers monthly (end-of-month)
    # For a real run, load daily prices into the prices table.
    import random
    tickers = ["BRK.B", "TLT", "IAU"]
    start = date(2020, 1, 31)
    months = 36
    for i in range(months):
        d = (start + relativedelta(months=i))
        for t in tickers:
            # synthetic price: base + small random walk
            base = {"BRK.B": 300.0, "TLT": 150.0, "IAU": 18.0}[t]
            # simple deterministic drift + noise
            price = base * (1 + 0.01 * i/12.0) * (1 + (random.random() - 0.5) * 0.02)
            con.execute("INSERT INTO prices VALUES (?, ?, ?)", [d, t, float(price)])
    # Seed a few dividend events
    con.execute("INSERT INTO dividends VALUES (?, ?, ?)", [date(2020, 3, 31), "TLT", 0.5])
    con.execute("INSERT INTO dividends VALUES (?, ?, ?)", [date(2021, 3, 31), "TLT", 0.45])
    con.execute("INSERT INTO dividends VALUES (?, ?, ?)", [date(2022, 3, 31), "IAU", 0.1])

def main():
    # Connect to DuckDB file-backed DB
    con = duckdb.connect("backtest.duckdb")
    init_db(con)

    # Seed example data (only for demo; skip if you have real prices/dividends)
    seed_example_data(con)

    # Backtest parameters
    tickers = ["BRK.B", "TLT", "IAU"]
    target_weights = {"BRK.B": 0.5, "TLT": 0.3, "IAU": 0.2}
    start_date = date(2020, 1, 31)
    end_date = date(2022, 12, 31)
    contribution = 1000.0        # monthly contribution
    dca_rate = 0.5               # deploy up to 50% of cash each period
    band = 0.03                  # rebalance band +/- 3%

    # Run backtest
    run_backtest(
        con=con,
        tickers=tickers,
        target_weights=target_weights,
        start_date=start_date,
        end_date=end_date,
        frequency="monthly",
        contribution=contribution,
        dca_rate=dca_rate,
        band=band
    )

    # Compute analytics with Polars
    metrics = compute_monthly_metrics(con)
    if metrics:
        print("Monthly vol:", metrics["vol"])
        print("Monthly sharpe:", metrics["sharpe"])
        print("Covariance matrix (Polars DataFrame):")
        print(metrics["cov_df"])
        print("Correlation matrix (Polars DataFrame):")
        print(metrics["corr_df"])

    # Example: show last 5 transactions and last portfolio snapshot
    print("\nLast 5 transactions:")
    print(con.execute("SELECT * FROM transactions ORDER BY ts DESC LIMIT 5").fetchdf())

    print("\nLast portfolio_monthly rows:")
    print(con.execute("SELECT * FROM portfolio_monthly ORDER BY month DESC LIMIT 6").fetchdf())

if __name__ == "__main__":
    main()