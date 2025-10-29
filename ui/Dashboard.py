import sys
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64
import socketio
from functools import partial

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
    QHBoxLayout, QPushButton, QMessageBox,QDialog,
    QFormLayout, QLineEdit, QScrollArea, QComboBox, QSizePolicy, QAction
)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import pyqtSignal, QObject

#from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvaspropagateSizeHints
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


host = "http://localhost:5000"
API_BASE = "http://localhost:5000/api"

# Socket.IO client
sio = socketio.Client()


class ImageViewer(QDialog):
    def __init__(self, name, pixmap):
        super().__init__()
        self.setWindowTitle(name)
        self.resize(800, 600)  # Initial size, but user can resize freely

        layout = QVBoxLayout(self)

        self.label = QLabel()
        self.label.setPixmap(pixmap)
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setScaledContents(True)  # ✅ Enables dynamic scaling
        self.label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.label)

        layout.addWidget(scroll)




class AnalyzerTab(QWidget):
    result_received = pyqtSignal(dict)   # signal carrying the result dict
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        layout = QVBoxLayout()

        # Form for arguments
        form = QFormLayout()
        self.startdate_input = QLineEdit("01/05/2015")
        self.holding_input = QLineEdit("0.25")
        self.rolling_input = QLineEdit("5")
        self.divtax_input = QLineEdit("0.3")
        form.addRow("Start Date (dd/mm/yyyy):", self.startdate_input)
        form.addRow("Holding Period Year:", self.holding_input)
        form.addRow("Rolling Years:", self.rolling_input)
        form.addRow("Dividend Tax Rate:", self.divtax_input)
        layout.addLayout(form)

        # Dropdown for commands
        self.cmd_dropdown = QComboBox()
        self.cmd_dropdown.addItems([
            "div", "o", "o_avg", "corr", "corr_3d", "ewm_corr_avg",
            "alpha", "alpha_avg", "beta_avg", "var", "ewm_var", "std", "std_avg"
        ])
        layout.addWidget(self.cmd_dropdown)

        # Run button
        self.run_button = QPushButton("Run Analysis")
        self.run_button.clicked.connect(self.run_analysis)
        layout.addWidget(self.run_button)

        # Scroll area for images
        self.scroll_area = QScrollArea()
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setWidget(self.scroll_content)
        layout.addWidget(self.scroll_area)

        self.setLayout(layout)

        self.result_received.connect(self.display_results)

        if not sio.connected:
            sio.connect(host)

            @sio.on("analysis_result")
            def on_result(data):
                # emit signal instead of touching UI directly
                self.result_received.emit(data)

    def run_analysis(self):
        cmd = self.cmd_dropdown.currentText()
        args = {
            "startdate": self.startdate_input.text(),
            "holdingPeriodYear": self.holding_input.text(),
            "rollingYr": self.rolling_input.text(),
            "divTaxRate": self.divtax_input.text(),
        }
        # Emit event to backend
        sio.emit("run_analysis", {"cmd": cmd, "args": args})


    def display_results(self, data):
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        images = data.get("images", {})
        for name, b64 in images.items():
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(b64))
            if not pixmap.isNull():
                preview = QLabel()
                preview.setPixmap(pixmap.scaledToWidth(300, Qt.SmoothTransformation))
                preview.setCursor(Qt.PointingHandCursor)

                # ✅ Use partial to bind arguments correctly
                preview.mousePressEvent = partial(self.open_viewer, name, pixmap)

                self.scroll_layout.addWidget(QLabel(name))
                self.scroll_layout.addWidget(preview)
    
    def open_viewer(self, name, pixmap, event):
        viewer = ImageViewer(name, pixmap)
        viewer.exec_()  # ✅ Use exec_() instead of show()







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
        self.analyzer_tab = AnalyzerTab(self)

        self.tabs.addTab(self.allocation_tab, "Allocation")
        self.tabs.addTab(self.beta_tab, "Beta")
        self.tabs.addTab(self.corr_tab, "Correlation")
        self.tabs.addTab(self.analyzer_tab, "Analyzer")

        self._build_allocation_tab()
        self._build_beta_tab()
        self._build_corr_tab()


        self.refresh_data_and_render()

    def _build_header(self, title, refresh_callback):
        layout = QHBoxLayout()
        label = QLabel(title)
        label.setStyleSheet("font-weight: bold; font-size: 16px;")
        layout.addWidget(label)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(refresh_callback)
        layout.addWidget(refresh_btn)
        layout.addStretch()

        return layout


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

    def _build_allocation_tab(self):
        layout = QVBoxLayout()
        self.alloc_header = self._build_header("Portfolio allocation", self.refresh_data_and_render)
        layout.addLayout(self.alloc_header)

        # --- Top half: two pie charts side by side ---
        chart_layout = QHBoxLayout()
        self.alloc_fig, self.alloc_ax = plt.subplots(figsize=(4,4))   # smaller
        self.alloc_canvas = FigureCanvas(self.alloc_fig)
        chart_layout.addWidget(self.alloc_canvas)

        self.tangent_fig, self.tangent_ax = plt.subplots(figsize=(4,4))  # smaller
        self.tangent_canvas = FigureCanvas(self.tangent_fig)
        chart_layout.addWidget(self.tangent_canvas)

        # --- Bottom half: two tables side by side ---
        table_layout = QHBoxLayout()
        self.portfolio_table = QTableWidget()
        self.portfolio_table.itemChanged.connect(self._on_portfolio_item_changed)
        table_layout.addWidget(self.portfolio_table)

        self.risk_table = QTableWidget()
        table_layout.addWidget(self.risk_table)

        # Add both halves to main layout
        layout.addLayout(chart_layout, stretch=1)
        layout.addLayout(table_layout, stretch=1)

        self.allocation_tab.setLayout(layout)




    def _on_portfolio_item_changed(self, item):
        # Only handle edits in the "Input" column
        col_name = self.portfolio_table.horizontalHeaderItem(item.column()).text()
        if col_name == "Input":
            ticker = self.portfolio_table.item(item.row(), 0).text()  # Ticker is first column
            new_value = item.text()

            try:
                r = requests.post(f"{API_BASE}/update_input", json={"Ticker": ticker, "Input": new_value}, timeout=5)
                r.raise_for_status()
            except Exception as e:
                QMessageBox.critical(self, "Update Error", f"Failed to update Input for {ticker}:\n{e}")



    def render_allocation(self):
        # --- Allocation pie ---
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

        # --- Tangent pie ---
        self.tangent_ax.clear()
        if not self.tangent:
            self.tangent_ax.text(0.5, 0.5, "No tangent data", ha="center", va="center")
        else:
            s = pd.Series(self.tangent).sort_values(ascending=False)
            s.plot.pie(ax=self.tangent_ax, autopct="%.1f%%", legend=False)
            self.tangent_ax.set_ylabel("")
            self.tangent_ax.set_title("Tangent portfolio weights")
        self.tangent_canvas.draw_idle()

        # --- Portfolio table with tangent weights ---
        if not self.positions_df.empty:
            cols = ["Ticker", "MarketValue", "Qty", "Price", "Position", "Input", "Tangent Weight"]
            self.portfolio_table.clear()
            self.portfolio_table.setRowCount(len(self.positions_df))
            self.portfolio_table.setColumnCount(len(cols))
            self.portfolio_table.setHorizontalHeaderLabels(cols)

            for i, row in self.positions_df.iterrows():
                ticker = row.get("Ticker", "")
                for j, col in enumerate(cols):
                    if col == "Tangent Weight":
                        val = self.tangent.get(ticker, 0.0)
                        item = QTableWidgetItem(f"{val:.6f}")
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    else:
                        val = row.get(col, "")
                        item = QTableWidgetItem(str(val))
                        if col != "Input":
                            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.portfolio_table.setItem(i, j, item)

            self.portfolio_table.resizeColumnsToContents()

        # --- Risk metrics table (reuse render_risk logic) ---
        if not self.risk_metrics:
            self.risk_table.clear()
            self.risk_table.setRowCount(1)
            self.risk_table.setColumnCount(1)
            self.risk_table.setHorizontalHeaderLabels(["Message"])
            self.risk_table.setItem(0, 0, QTableWidgetItem("No risk data"))
        else:
            metrics = self.risk_metrics
            rows = list(metrics.items())
            self.risk_table.clear()
            self.risk_table.setRowCount(len(rows))
            self.risk_table.setColumnCount(2)
            self.risk_table.setHorizontalHeaderLabels(["Metric", "Value"])
            for i, (k, v) in enumerate(rows):
                key_item = QTableWidgetItem(k)
                val_item = QTableWidgetItem(f"{v:.4f}" if isinstance(v, float) else str(v))
                key_item.setFlags(key_item.flags() & ~Qt.ItemIsEditable)
                val_item.setFlags(val_item.flags() & ~Qt.ItemIsEditable)
                self.risk_table.setItem(i, 0, key_item)
                self.risk_table.setItem(i, 1, val_item)
            self.risk_table.resizeColumnsToContents()





    def _build_beta_tab(self):
        layout = QVBoxLayout()
        header = self._build_header("Systematic risk (betas)", self.refresh_data_and_render)
        layout.addLayout(header)

        # Replace chart with table
        self.beta_table = QTableWidget()
        layout.addWidget(self.beta_table)

        self.beta_tab.setLayout(layout)


    def render_beta(self):
        if not self.betas:
            self.beta_table.clear()
            self.beta_table.setRowCount(1)
            self.beta_table.setColumnCount(1)
            self.beta_table.setHorizontalHeaderLabels(["Message"])
            self.beta_table.setItem(0, 0, QTableWidgetItem("No beta data"))
            return

        # Columns
        cols = ["Ticker", "Market ETF", "Weighted Beta", "CAPM E[R]", "Alpha"]
        rows = [t for t in self.betas.keys() if t.lower() != "portfolio"]
        self.beta_table.clear()
        self.beta_table.setRowCount(len(rows) + 1)  # +1 for portfolio summary
        self.beta_table.setColumnCount(len(cols))
        self.beta_table.setHorizontalHeaderLabels(cols)

        # Fill rows
        for i, ticker in enumerate(rows):
            data = self.betas[ticker]
            self.beta_table.setItem(i, 0, QTableWidgetItem(ticker))
            self.beta_table.setItem(i, 1, QTableWidgetItem("SPY"))  # or VOO
            self.beta_table.setItem(i, 2, QTableWidgetItem(f"{data.get('beta', 0):.3f}"))
            self.beta_table.setItem(i, 3, QTableWidgetItem(f"{data.get('capm_er', 0):.2%}"))
            self.beta_table.setItem(i, 4, QTableWidgetItem(f"{data.get('alpha', 0):.2%}"))

        # Portfolio summary row
        port = self.betas.get("portfolio", {})
        last_row = len(rows)
        self.beta_table.setItem(last_row, 0, QTableWidgetItem("Portfolio"))
        self.beta_table.setItem(last_row, 1, QTableWidgetItem("-"))
        self.beta_table.setItem(last_row, 2, QTableWidgetItem(f"{port.get('beta', 0):.3f}"))
        self.beta_table.setItem(last_row, 3, QTableWidgetItem("-"))
        self.beta_table.setItem(last_row, 4, QTableWidgetItem(f"{port.get('alpha', 0):.2%}"))

        self.beta_table.resizeColumnsToContents()


    def _build_corr_tab(self):
        layout = QVBoxLayout()
        header = self._build_header("Correlation heatmap", self.refresh_data_and_render)
        layout.addLayout(header)

        self.corr_fig, self.corr_ax = plt.subplots(figsize=(9,7))
        self.corr_canvas = FigureCanvas(self.corr_fig)
        layout.addWidget(self.corr_canvas)

        # Add weighted HPR table
        self.hpr_table = QTableWidget()
        layout.addWidget(self.hpr_table)

        self.corr_tab.setLayout(layout)


    def render_corr(self):
        # Clear figure completely to avoid duplicate colorbars
        self.corr_fig.clf()
        self.corr_ax = self.corr_fig.add_subplot(111)

        if self.corr_df.empty:
            self.corr_ax.text(0.5, 0.5, "No correlation data", ha="center", va="center")
        else:
            sns.heatmap(self.corr_df, cmap="coolwarm", vmin=-1, vmax=1,
                        ax=self.corr_ax, linewidths=0.3)
            self.corr_ax.set_title("Ticker correlation matrix")

        self.corr_canvas.draw_idle()

        # Render Weighted HPR table (unchanged)
        cor = self._fetch_json("correlation")
        if cor and "weighted_hpr" in cor:
            tickers = cor["tickers"]
            hpr = cor["weighted_hpr"]

            self.hpr_table.clear()
            self.hpr_table.setRowCount(1)
            self.hpr_table.setColumnCount(len(tickers))
            self.hpr_table.setHorizontalHeaderLabels(tickers)

            for j, t in enumerate(tickers):
                val = hpr.get(t, 0.0)
                item = QTableWidgetItem(f"{val:.6f}")
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.hpr_table.setItem(0, j, item)

            self.hpr_table.resizeColumnsToContents()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PortfolioVisualizer()
    window.show()
    sys.exit(app.exec_())
