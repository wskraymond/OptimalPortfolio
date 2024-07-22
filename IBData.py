from ibapi.client import *
from ibapi.wrapper import *
import pandas as pd
from src.data.store import Store
from datetime import datetime
import time
import threading
import collections
port = 4001

mycontract = Contract()
mycontract.symbol = "AAPL"
mycontract.secType = "STK"
mycontract.exchange = "SMART"
mycontract.currency = "USD"

DailyPriceData = collections.namedtuple('DailyPriceData', ['ticker',
                                                           'date',
                                                           'name',
                                                           'ccy',
                                                           'country',
                                                           'close',
                                                           'high',
                                                           'low'])

#https://ibkrcampus.com/trading-lessons/python-receiving-market-data/
class TestApp(EClient, EWrapper):
    def __init__(self):
        EClient.__init__(self, self)
        self.data = []
    def nextValidId(self, orderId: OrderId):
        self.orderId = orderId

    def nextId(self):
        self.orderId += 1
        return self.orderId

    def error(self, reqId, errorCode, errorString, advancedOrderReject):
        print(f"reqId: {reqId}, errorCode: {errorCode}, errorString: {errorString}, orderReject: {advancedOrderReject}")

    def historicalData(self, reqId: int, bar: BarData):
        print(reqId, bar)
        self.data.append(DailyPriceData(ticker=mycontract.symbol,
                                        date=datetime.strptime(bar.date, '%Y%m%d').date(),
                                        name=mycontract.symbol,
                                        ccy=mycontract.currency,
                                        country=mycontract.exchange,
                                        close=bar.close,
                                        high=bar.high,
                                        low=bar.low
                                        ))
    def historicalDataEnd(self, reqId, start, end):
        print(f"Historical Data Ended for {reqId}. Started at {start}, ending at {end}")
        print(self.data)

        store = Store(hosts=['127.0.0.1'], keyspace='store')
        store.batch_insert_daily_price(self.data)
        return super().historicalDataEnd(reqId, start, end)

app = TestApp()
app.connect("127.0.0.1", port, 0)
threading.Thread(target=app.run).start()
time.sleep(1)
# app.reqHistoricalData(app.nextId(), mycontract, "", "1 Y", "1 day", "TRADES", 1, 1, False, [])
app.reqHistoricalData(
    reqId=app.nextId(),
    contract=mycontract,
    endDateTime="",
    durationStr= "1 Y",
    barSizeSetting = "1 day",
    whatToShow= "TRADES",
    useRTH=0,
    formatDate=1,
    keepUpToDate=False,
    chartOptions=[],
)

time.sleep(1)
app.disconnect()