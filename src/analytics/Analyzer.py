import time
import pandas as pd
import numpy as np
import pandas_datareader as pdr
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm
import datetime as dt
import seaborn as sns
from pandas.core.window import Window
from scipy.optimize import minimize
from argparse import ArgumentParser
import math
from pandas_datareader.data import DataReader as dr
import traceback

from data.contract.MyContract import contractList
from data.store import Store
from analytics.Stats import Stats
from analytics.Allocation import Allocation
from datetime import datetime
import mplcursors
import yfinance as yf
from yahooquery import Ticker
from ibapi.contract import Contract
from scipy import stats as ss
import base64
import io

store_host = 'host.docker.internal'

# Helper to capture a matplotlib figure as base64
def fig_to_base64(fig, dpi=300):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=dpi)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")

class RollingPortfolioAnalyzer:
    def __init__(self, startdate: str, holdingPeriodYear: float = 0.25,
                 rollingYr: float = 5, divTaxRate: float = 0.3, store: Store = None):
        """
        Initialize analyzer: builds Stats, loads data, and precomputes returns/dividends/expenses.
        """
        self.stats = Stats(startdate, holdingPeriodYear, rollingYr, divTaxRate, store)

        # Preload all data
        self.stats.loadYC()
        self.stats.loadDailyPrice()
        self.stats.load_div_expense()
        self.stats.after_tax()
        self.stats.pre_return()
        self.stats.pre_div_return()
        self.stats.pre_log_expense()
    
    def run_div(self):
        """Perform dividend-related analysis and return plots as base64 images + summary data."""
        stats = self.stats

        # Compute summary stats
        summary = {
            "log_mean": stats.returns.mean().to_dict(),
            "log_std": stats.returns.std().to_dict(),
            "div_mean": stats.div_return.mean().to_dict(),
            "div_std": stats.div_return.std().to_dict(),
            "expense": ((np.exp(stats.log_expense) - 1) * 100).to_dict(),
        }

        images = {}

        # --- Plot 1: log returns ---
        fig1, ax1 = plt.subplots()
        stats.returns.plot(ax=ax1)
        ax1.set_title("log return")
        images["log_return"] = fig_to_base64(fig1)
        plt.close(fig1)

        # --- Plot 2: annual dividend payments ---
        fig2, ax2 = plt.subplots()
        div = stats.div.groupby(stats.div.index.year).sum()
        div.plot(ax=ax2)
        ax2.set_title("tax adjusted div payment over year")
        images["div_payment"] = fig_to_base64(fig2)
        plt.close(fig2)

        # --- Plot 3: annual dividend yield ---
        fig3, ax3 = plt.subplots()
        div_yield = (np.exp(stats.div_return.groupby(stats.div_return.index.year).sum()) - 1) * 100
        div_yield.plot(ax=ax3)
        ax3.set_title("tax adjusted div yield per year")
        images["div_yield"] = fig_to_base64(fig3)
        plt.close(fig3)

        # --- Plot 4: dividend yield over time since first funding ---
        fig4, ax4 = plt.subplots()
        div_yield_over_time = (div / stats.Closeprice.loc[stats.Closeprice.first_valid_index()]) * 100
        for ticker in div_yield_over_time.columns:
            div_line = div_yield_over_time[ticker]
            close_price = stats.Closeprice.loc[stats.Closeprice.first_valid_index(), ticker]
            date = stats.Closeprice[ticker].first_valid_index().date()
            label = f"{ticker}@{close_price:.2f} on {date}"
            div_line.plot(ax=ax4, label=label)
        ax4.set_title("Tax-Adjusted Dividend Yield Over Years Since First Funding")
        ax4.legend()
        ax4.grid(True)
        images["div_yield_over_time"] = fig_to_base64(fig4)
        plt.close(fig4)

        return {"summary": summary, "images": images}
    
    def run_optimal(self):
        """Rolling optimal allocations (cmd == 'o')."""
        rolling_return = self.stats.rolling_return_list()
        rolling_div_return = self.stats.rolling_div_return_list()

        def rolling_optimize(ret, div):
            alloc = Allocation(self.stats, ret, div)
            alloc.preload(); alloc.optimize()
            return alloc

        rolling_alloc = [rolling_optimize(r.dropna(), d.dropna())
                         for r, d in zip(rolling_return, rolling_div_return)
                         if not r.empty and not d.empty]

        ratio_m = pd.DataFrame([a.get_result() for a in rolling_alloc],
                               index=[a.endDate for a in rolling_alloc])
        alloc_m = pd.DataFrame([a.get_allocation() for a in rolling_alloc],
                               index=[a.endDate for a in rolling_alloc])

        # Plot ratio
        fig1, ax1 = plt.subplots()
        ratio_m.plot(ax=ax1)
        ax1.set_title(f"Ratio - optimal portfolio with {int(self.stats.holdingPeriodYear)}Y HPR rolling over {int(self.stats.rollingYr)}Y window")
        img_ratio = fig_to_base64(fig1); plt.close(fig1)

        # Plot allocation
        fig2, ax2 = plt.subplots()
        alloc_m.plot(ax=ax2)
        ax2.set_title(f"Alloc - optimal portfolio with {int(self.stats.holdingPeriodYear)}Y HPR rolling over {int(self.stats.rollingYr)}Y window")
        img_alloc = fig_to_base64(fig2); plt.close(fig2)

        return {"images": {"ratio": img_ratio, "allocation": img_alloc}}

    def run_optimal_avg(self):
        """Smoothed optimal allocations (cmd == 'o_avg')."""
        rolling_return = self.stats.rolling_return_list()
        rolling_div_return = self.stats.rolling_div_return_list()

        def rolling_optimize(ret, div):
            alloc = Allocation(self.stats, ret, div)
            alloc.preload(); alloc.optimize()
            return alloc

        rolling_alloc = [rolling_optimize(r.dropna(), d.dropna())
                         for r, d in zip(rolling_return, rolling_div_return)
                         if not r.empty and not d.empty]

        ratio_m = pd.DataFrame([a.get_result() for a in rolling_alloc],
                               index=[a.endDate for a in rolling_alloc])
        alloc_m = pd.DataFrame([a.get_allocation() for a in rolling_alloc],
                               index=[a.endDate for a in rolling_alloc])

        halflife = str(int(self.stats.windowSize) // 2) + " days"
        alloc_mean = alloc_m.ewm(halflife=halflife, times=alloc_m.index).mean()
        ratio_mean = ratio_m.ewm(halflife=halflife, times=ratio_m.index).mean()

        fig1, ax1 = plt.subplots()
        ratio_mean.plot(ax=ax1)
        ax1.set_title(f"Ratio - optimal portfolio with {int(self.stats.holdingPeriodYear)}Y HPR rolling over {int(self.stats.rollingYr)}Y EMA")
        img_ratio = fig_to_base64(fig1); plt.close(fig1)

        fig2, ax2 = plt.subplots()
        alloc_mean.plot(ax=ax2)
        ax2.set_title(f"Alloc - optimal portfolio with {int(self.stats.holdingPeriodYear)}Y HPR rolling over {int(self.stats.rollingYr)}Y EMA")
        ax2.grid(True)
        img_alloc = fig_to_base64(fig2); plt.close(fig2)

        return {"images": {"ratio": img_ratio, "allocation": img_alloc}}

    def run_corr(self):
        """Rolling correlation time series (cmd == 'corr')."""
        corr_matrix = self.stats.rolling_corr()

        fig, ax = plt.subplots(figsize=(10, 6))
        for a in corr_matrix.columns:
            for b in corr_matrix.columns:
                if a != b:
                    y = corr_matrix.loc[(slice(None), a), b].dropna()
                    x = y.index.get_level_values(0).unique().to_numpy()
                    ax.plot(x, y.to_numpy(), label=f"{a}-{b}")

        mplcursors.cursor(hover=True).connect("add",
            lambda sel: sel.annotation.set_text(sel.artist.get_label()))

        ax.set_xlabel("Date"); ax.set_ylabel("Correlation")
        ax.set_title("Rolling Correlation Between Stocks")
        ax.legend(); ax.grid(True)
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"corr": img}}

    def run_corr_3d(self):
        """3D rolling correlation (cmd == 'corr_3d')."""
        corr_matrix = self.stats.rolling_corr()
        fig = plt.figure()
        ax = fig.add_subplot(111, projection="3d")
        my_dict = {value: index for index, value in enumerate(corr_matrix.columns)}
        for a in corr_matrix.columns:
            for b in corr_matrix.columns:
                if a != b:
                    s = corr_matrix.loc[(slice(None), a), b].dropna()
                    y = s.to_numpy()
                    i = s.index.get_level_values(0).unique().astype(int).to_numpy()
                    z = np.full_like(s, my_dict[a])
                    ax.plot(z, i, y, label=f"{my_dict[a]}-{a}-{b}")
        ax.set_xlabel("stock"); ax.set_ylabel("date"); ax.set_zlabel("corr")
        ax.set_title("3D Rolling Correlation Between Stocks")
        ax.legend()
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"corr_3d": img}}

    def run_ewm_corr_avg(self):
        """Exponentially weighted moving average correlation (cmd == 'ewm_corr_avg')."""
        ret = self.stats.returns
        corr = ret.ewm(span=int(self.stats.windowSize)).corr()
        corr_matrix = corr.groupby(level=1).mean()

        fig, ax = plt.subplots(figsize=(13, 8))
        sns.heatmap(corr_matrix, annot=True, cmap="RdYlGn_r", ax=ax)
        ax.set_title("Mean of Exponential Weighted Moving Correlation")
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"ewm_corr_avg": img}}


    def run_alpha(self, benchmark="VOO"):
        """CAPM alpha for each ticker vs benchmark."""
        betas = {}
        for t in self.stats.recvTickers:
            slope, _, _, _, _ = ss.linregress(
                np.nan_to_num(self.stats.returns[benchmark].values),
                np.nan_to_num(self.stats.returns[t].values)
            )
            betas[t] = {benchmark: slope}
        betas_df = pd.DataFrame(betas).T

        alloc = Allocation(self.stats, self.stats.returns, self.stats.div_return)
        alloc.preload()
        alpha_period, E_period = alloc.calc_period_alpha_capm(betas=betas_df, benchmark=benchmark)

        alpha_df = alpha_period.rename("alpha").to_frame().reset_index()
        alpha_df.columns = ["ticker", "alpha"]

        fig, ax = plt.subplots(figsize=(12, 6))
        sns.barplot(data=alpha_df, x="ticker", y="alpha", palette="vlag", ax=ax)
        ax.axhline(0, color="black", linewidth=1)
        ax.set_title(f"CAPM Alpha over {self.stats.holdingPeriodYear}-year Holding Period")
        ax.set_xlabel("Ticker"); ax.set_ylabel("Period Alpha")
        ax.tick_params(axis="x", rotation=45)
        plt.tight_layout()
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"alpha": img}}

    def run_alpha_avg(self, benchmark="VOO"):
        """Rolling CAPM alpha smoothed with EMA."""
        rolling_return = self.stats.rolling_return_list()
        rolling_alpha = []
        for window_ret in rolling_return:
            ret = window_ret.dropna()
            if ret.empty: 
                continue
            div_ret_window = self.stats.div_return.loc[ret.index]
            alloc = Allocation(self.stats, ret, div_ret_window)
            alloc.preload()
            betas_w = {}
            for tkr in self.stats.recvTickers:
                x = np.nan_to_num(ret[benchmark].values)
                y = np.nan_to_num(ret[tkr].values)
                slope, _, _, _, _ = ss.linregress(x, y)
                betas_w[tkr] = {benchmark: slope}
            betas_df_w = pd.DataFrame(betas_w).T
            alpha_w, expected = alloc.calc_period_alpha_capm(betas=betas_df_w, benchmark=benchmark)
            rolling_alpha.append((ret.index[-1], alpha_w))

        alpha_matrix = pd.DataFrame([a for _, a in rolling_alpha],
                                    index=[d for d, _ in rolling_alpha])
        halflife = str(int(self.stats.windowSize) // 2) + " days"
        alpha_avg = alpha_matrix.ewm(halflife=halflife, times=alpha_matrix.index).mean()

        fig, ax = plt.subplots(figsize=(10, 6))
        alpha_avg.plot(ax=ax)
        ax.set_title(f"Rolling CAPM Alpha (halflife={halflife})")
        ax.set_xlabel("Date"); ax.set_ylabel("CAPM Alpha (period)")
        ax.legend(title="Ticker", bbox_to_anchor=(1.02, 1), loc="upper left")
        plt.tight_layout()
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"alpha_avg": img}}

    def run_beta_avg(self, benchmark="VOO"):
        """Rolling CAPM beta smoothed with EMA."""
        rolling_return = self.stats.rolling_return_list()
        betas_list = []
        for ret in rolling_return:
            ret = ret.dropna()
            if ret.empty: continue
            betas = {}
            for t in self.stats.recvTickers:
                slope, _, _, _, _ = ss.linregress(
                    np.nan_to_num(ret[benchmark].values),
                    np.nan_to_num(ret[t].values)
                )
                betas[t] = slope
            betas_list.append((ret.index[-1], betas))
        betas_m = pd.DataFrame([b for _, b in betas_list],
                               index=[d for d, _ in betas_list])
        halflife = str(int(self.stats.windowSize) // 2) + " days"
        rolling_avg = betas_m.ewm(halflife=halflife, times=betas_m.index).mean()

        fig, ax = plt.subplots()
        rolling_avg.plot(ax=ax)
        ax.set_title("Rolling CAPM Beta")
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"beta_avg": img}}

    def run_var(self):
        """Rolling variance annualized."""
        var = self.stats.returns.dropna().rolling(window=int(self.stats.windowSize)).var() * self.stats.no_of_days
        fig, ax = plt.subplots()
        var.plot(ax=ax); ax.set_title("Rolling Variance")
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"var": img}}

    def run_ewm_var(self):
        """Exponentially weighted variance annualized."""
        var = self.stats.returns.ewm(span=int(self.stats.windowSize)).var() * self.stats.no_of_days
        fig, ax = plt.subplots()
        var.plot(ax=ax); ax.set_title("EWM Variance")
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"ewm_var": img}}

    def run_std(self):
        """Rolling custom std measure."""
        def roll_std(ret):
            mean_1 = np.exp(ret.mean() * self.stats.no_of_days)
            log_var = ret.var(skipna=True) * self.stats.no_of_days
            diff = np.exp(-1 * np.sqrt(log_var))
            std = (diff * mean_1 - mean_1) * -100
            return ret.index[-1], std

        rolling_return = self.stats.rolling_return_list()
        rolling_std = [roll_std(r.dropna()) for r in rolling_return if not r.empty]
        std_m = pd.DataFrame([s for _, s in rolling_std],
                             index=[d for d, _ in rolling_std])
        fig, ax = plt.subplots()
        std_m.plot(ax=ax); ax.set_title("Rolling Std")
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"std": img}}

    def run_std_avg(self):
        """Smoothed rolling std measure."""
        std_m = pd.DataFrame()
        def roll_std(ret):
            mean_1 = np.exp(ret.mean() * self.stats.no_of_days)
            log_var = ret.var(skipna=True) * self.stats.no_of_days
            diff = np.exp(-1 * np.sqrt(log_var))
            std = (diff * mean_1 - mean_1) * -100
            return ret.index[-1], std

        rolling_return = self.stats.rolling_return_list()
        rolling_std = [roll_std(r.dropna()) for r in rolling_return if not r.empty]
        std_m = pd.DataFrame([s for _, s in rolling_std],
                             index=[d for d, _ in rolling_std])
        halflife = str(int(self.stats.windowSize) // 2) + " days"
        std_avg = std_m.ewm(halflife=halflife, times=std_m.index).mean()

        fig, ax = plt.subplots()
        std_avg.plot(ax=ax)
        ax.set_title(f"Rolling Risk in a {self.stats.holdingPeriodYear}-Y holding Period")
        ax.grid(True)
        img = fig_to_base64(fig); plt.close(fig)

        return {"images": {"std_avg": img}}
