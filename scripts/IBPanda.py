#https://ibkrcampus.com/ibkr-quant-news/using-pandas-for-market-data-management/

from ibapi.client import *
from ibapi.wrapper import *
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
port = 4001
class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = []
    def nextValidId(self, orderId: OrderId):
        mycontract = Contract()
        mycontract.conId = 265598
        mycontract.exchange = "SMART"

        self.reqHistoricalData(
            reqId=123,
            contract=mycontract,
            endDateTime="",
            durationStr= "2 D",
            barSizeSetting = "1 hour",
            whatToShow= "TRADES",
            useRTH=0,
            formatDate=1,
            keepUpToDate=False,
            chartOptions=[],
        )
    def historicalData(self, reqId: int, bar: BarData):
        print("Historical Bar", bar)
        # Remove timezone information before appending
        date_without_tz = bar.date.split(' ')[0] + ' ' + bar.date.split(' ')[1]
        self.data.append([
            date_without_tz, bar.open, bar.high, bar.low, bar.close,
            bar.volume, bar.wap, bar.barCount
        ])
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        print("\nHistorical Data received \n")
        df = pd.DataFrame(self.data, columns=[
            'Date', 'Open', 'High', 'Low', 'Close', 'Volume', 'WAP', 'BarCount'
        ])
        # Convert 'Date' to datetime and set as index
        df['Date'] = pd.to_datetime(df['Date'], format='%Y%m%d %H:%M:%S')
        df.set_index('Date', inplace=True)
        print("Creating Data Frame...Printing DataFrame:\n")
        print(df)

        # Plot the data
        fig, ax1 = plt.subplots(figsize=(12, 8))
        # Plot OHLC data
        ax1.plot(df.index, df['Open'], label='Open', color='blue')
        ax1.plot(df.index, df['High'], label='High', color='green')
        ax1.plot(df.index, df['Low'], label='Low', color='red')
        ax1.plot(df.index, df['Close'], label='Close', color='black')
        ax1.set_ylabel('Price')
        ax1.legend(loc='upper left')
        # Create another y-axis for the volume data
        ax2 = ax1.twinx()
        ax2.fill_between(df.index, df['Volume'], color='gray', alpha=0.3, label='Volume')
        ax2.set_ylabel('Volume')
        ax2.legend(loc='upper right')
        # Format the x-axis to show the full date and time
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d %H:%M:%S'))
        plt.xticks(rotation=45)
        plt.gcf().autofmt_xdate()  # Auto format date for better visibility
        plt.title('Stock Price and Volume')
        plt.show()

        return super().historicalDataEnd(reqId, start, end)
    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        print(reqId, errorCode, errorString, advancedOrderRejectJson)
app = TestApp()
app.connect("127.0.0.1", port, 1)
app.run()