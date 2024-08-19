import traceback

import yfinance as yf


try:
    cl = yf.Ticker('CL')
    print(cl.incomestmt)
    print(cl.get_dividends())
    print(cl.info['dividendRate'])
    print(cl.info['dividendYield'])
    print(cl.info['exDividendDate'])
    print(cl.info['payoutRatio'])
    print(cl.info['lastDividendDate'])
    print(cl.info['lastDividendValue'])
    print(cl.info['returnOnEquity'])
    print(cl.info['returnOnAssets'])

    from yahooquery import Ticker

    def get_expense_ratio(ticker, etf):
        if ticker in etf.fund_profile and 'feesExpensesInvestment' in etf.fund_profile[ticker] and 'annualReportExpenseRatio' in etf.fund_profile[ticker]['feesExpensesInvestment']:
            # Both columns exist
            expense_ratio = etf.fund_profile[ticker]['feesExpensesInvestment']['annualReportExpenseRatio']
        else:
            # Either or both columns do not exist
            expense_ratio = 0.0
        return expense_ratio

    etf = Ticker('SPY')
    # expense_ratio = etf.fund_profile['APPL']['feesExpensesInvestment']['annualReportExpenseRatio']
    print(get_expense_ratio('SPY',etf))

except Exception as error:
    print("An error occurred:", error)
    traceback.print_exc()
    # print(f"Expense Ratio for VTI: {expense_ratio:.4f}")
