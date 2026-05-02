from data.store import Store
from datetime import date

store_host = 'host.docker.internal'
store = Store(hosts=[store_host], keyspace='store')

# Get all unique tickers
all_tickers = set(row.ticker for row in store.select_all_stocks())

target_date = '2026-04-17'
missing_tickers = []

for ticker in all_tickers:
    # Check if this ticker has a record for the target date
    query = "SELECT * FROM DailyPrice WHERE ticker = %s AND date = %s"
    rows = store.session.execute(query, [ticker, target_date])
    if not rows:
        missing_tickers.append(ticker)

print(f"Tickers missing {target_date}: {missing_tickers}")
print(f"Count: {len(missing_tickers)}")