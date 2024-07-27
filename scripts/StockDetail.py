import traceback

import yfinance as yf

try:
    vti = yf.Ticker('BRK-B')  # Replace with your ETF ticker
    print(vti.incomestmt)
    # expense_ratio = vti.info['annualReportExpenseRatio']
except Exception as error:
    print("An error occurred:", error)
    traceback.print_exc()
    # print(f"Expense Ratio for VTI: {expense_ratio:.4f}")
