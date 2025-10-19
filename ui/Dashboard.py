import sys
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

""" from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QPushButton, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas """

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHBoxLayout, QPushButton, QMessageBox
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)



API_BASE = "http://localhost:5000/api"

class PortfolioVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MyPortfolio Visualizer (Backend Inputs)")
        self.setGeometry(200, 200, 1150, 800)

        self.positions_df = pd.DataFrame()
        self.corr_df = pd.DataFrame()
        self.betas = {}
        self.tangent = {}
        self.risk_metrics = {}

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.allocation_tab = QWidget()
        self.beta_tab = QWidget()
        self.corr_tab = QWidget()
        self.tangent_tab = QWidget()
        self.risk_tab = QWidget()

        self.tabs.addTab(self.allocation_tab, "Allocation")
        self.tabs.addTab(self.beta_tab, "Beta")
        self.tabs.addTab(self.corr_tab, "Correlation")
        self.tabs.addTab(self.tangent_tab, "Tangent portfolio")
        self.tabs.addTab(self.risk_tab, "Risk metrics")

        self._build_allocation_tab()
        self._build_beta_tab()
        self._build_corr_tab()
        self._build_tangent_tab()
        self._build_risk_tab()

        self.refresh_data_and_render()

    def _fetch_json(self, endpoint):
        try:
            r = requests.get(f"{API_BASE}/{endpoint}", timeout=10)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            QMessageBox.critical(self, "API Error", f"Failed to fetch {endpoint}:\n{e}")
            return None

    def refresh_data_and_render(self):
        pos = self._fetch_json("positions")
        cor = self._fetch_json("correlation")
        bet = self._fetch_json("betas")
        tan = self._fetch_json("tangent")
        risk = self._fetch_json("risk")

        if pos:
            self.positions_df = pd.DataFrame(pos)
        if cor and "tickers" in cor and "matrix" in cor:
            self.corr_df = pd.DataFrame(cor["matrix"], index=cor["tickers"], columns=cor["tickers"])
        if bet:
            self.betas = bet
        if tan:
            self.tangent = tan
        if risk:
            self.risk_metrics = risk

        self.render_allocation()
        self.render_beta()
        self.render_corr()
        self.render_tangent()
        self.render_risk()

    def _build_allocation_tab(self):
        layout = QVBoxLayout()
        self.alloc_header = self._build_header("Portfolio allocation", self.refresh_data_and_render)
        layout.addLayout(self.alloc_header)
        self.alloc_fig, self.alloc_ax = plt.subplots(figsize=(6,6))
        self.alloc_canvas = FigureCanvas(self.alloc_fig)
        layout.addWidget(self.alloc_canvas)
        self.allocation_tab.setLayout(layout)

    def render_allocation(self):
        self.alloc_ax.clear()
        if self.positions_df.empty:
            self.alloc_ax.text(0.5, 0.5, "No positions data", ha="center", va="center")
        else:
            weights = self.positions_df.set_index("Ticker")["MarketValue"]
            if weights.sum() == 0:
                self.alloc_ax.text(0.5, 0.5, "All market values are zero", ha="center", va="center")
            else:
                weights.plot.pie(ax=self.alloc_ax, autopct="%.1f%%", legend=False)
                self.alloc_ax.set_ylabel("")
                self.alloc_ax.set_title("Allocation by market value")
        self.alloc_canvas.draw_idle()

    def _build_beta_tab(self):
        layout = QVBoxLayout()
        header = self._build_header("Systematic risk (betas)", self.refresh_data_and_render)
        layout.addLayout(header)
        self.beta_fig, self.beta_ax = plt.subplots(figsize=(8,5))
        self.beta_canvas = FigureCanvas(self.beta_fig)
        layout.addWidget(self.beta_canvas)
        self.beta_tab.setLayout(layout)

    def render_beta(self):
        self.beta_ax.clear()
        if not self.betas:
            self.beta_ax.text(0.5, 0.5, "No beta data", ha="center", va="center")
        else:
            s = pd.Series(self.betas).sort_values()
            s.plot(kind="bar", ax=self.beta_ax, color="steelblue")
            self.beta_ax.set_title("Portfolio betas by ticker")
            self.beta_ax.axhline(1.0, color="red", linestyle="--", linewidth=1, label="Market beta (SPY=1)")
            self.beta_ax.legend()
        self.beta_canvas.draw_idle()

    def _build_corr_tab(self):
        layout = QVBoxLayout()
        header = self._build_header("Correlation heatmap", self.refresh_data_and_render)
        layout.addLayout(header)
        self.corr_fig, self.corr_ax = plt.subplots(figsize=(9,7))
        self.corr_canvas = FigureCanvas(self.corr_fig)
        layout.addWidget(self.corr_canvas)
        self.corr_tab.setLayout(layout)

    def render_corr(self):
        self.corr_ax.clear()
        if self.corr_df.empty:
            self.corr_ax.text(0.5, 0.5, "No correlation data", ha="center", va="center")
        else:
            sns.heatmap(self.corr_df, cmap="coolwarm", vmin=-1, vmax=1, ax=self.corr_ax, linewidths=0.3)
            self.corr_ax.set_title("Ticker correlation matrix")
        self.corr_canvas.draw_idle()

    def _build_tangent_tab(self):
        layout = QVBoxLayout()
        header = self._build_header("Tangent portfolio weights", self.refresh_data_and_render)
        layout.addLayout(header)
        self.tangent_fig, self.tangent_ax = plt.subplots(figsize=(8,5))
        self.tangent_canvas = FigureCanvas(self.tangent_fig)
        layout.addWidget(self.tangent_canvas)

        self.tangent_table = QTableWidget()
        layout.addWidget(self.tangent_table)

        self.tangent_tab.setLayout(layout)

    def render_tangent(self):
        self.tangent_ax.clear()
        if not self.tangent:
            self.tangent_ax.text(0.5, 0.5, "No tangent portfolio data", ha="center", va="center")
            self.tangent_canvas.draw_idle()
            return

        s = pd.Series(self.tangent).sort_values(ascending=False)
        s.plot(kind="bar", ax=self.tangent_ax, color="darkorange")
        self.tangent_ax.set_title("Tangent portfolio weights")
        self.tangent_canvas.draw_idle()

        self.tangent_table.clear()
        self.tangent_table.setRowCount(len(s))
        self.tangent_table.setColumnCount(2)
        self.tangent_table.setHorizontalHeaderLabels(["Ticker", "Weight"])
        for i, (k, v) in enumerate(s.items()):
            self.tangent_table.setItem(i, 0, QTableWidgetItem(str(k)))
            self.tangent_table.setItem(i, 1, QTableWidgetItem(f"{v:.6f}"))
        self.tangent_table.resizeColumnsToContents()

    def _build_risk_tab(self):
        layout = QVBoxLayout()
        header = self._build_header("Portfolio risk metrics", self.refresh_data_and_render)
        layout.addLayout(header)

        self.risk_table = QTableWidget()
        layout.addWidget(self.risk_table)

        self.risk_fig, self.risk_ax = plt.subplots(figsize=(7,4))
        self.risk_canvas = FigureCanvas(self.risk_fig)
        layout.addWidget(self.risk_canvas)

        self.risk_tab.setLayout(layout)

    def render_risk(self):
        items = list(self.risk_metrics.items())
        self.risk_table.clear()
        self.risk_table.setRowCount(len(items))
        self.risk_table.setColumnCount(2)
